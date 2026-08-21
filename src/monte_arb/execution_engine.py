"""Execution and capacity engine over frozen L2 order books.

Public seam: pure functions (walk_book, order_qty_for_notional, leg_execution,
pair_execution, capacity_usd) plus build_execution_snapshot() and the CLI scan
run_execution_scan(). No execution client and no orders.

Units and honesty rules
-----------------------
- Prices and quantities are Decimal; JSON output uses floats for display.
- Lighter taker/maker fee fields are treated as percent (0.05 -> 5 bps);
  account-level fee schedules are unknown. Hyperliquid HIP-3 meta exposes no
  fee fields, so fee_bps stays None (never silently zero).
- Unknown fee keeps net_price_pnl_bps None (never silently zero).
- Executable spread is already computed from target-size VWAP; slippage is a
  diagnostic decomposition and is not deducted a second time.
- Both legs share one exactly hedgeable economic exposure after venue grids and
  contract multipliers are applied.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Tuple

from .adapters import (
    LIGHTER_BASE_URL,
    PublicJsonClient,
    SourceRequestError,
    SourceShapeError,
    fetch_hyperliquid_book,
    fetch_hyperliquid_catalog,
    fetch_lighter_book,
    fetch_lighter_catalog,
)
from .market import CatalogMarket, MarketIdentity

SCHEMA = "day16-execution-snapshot-v2"
VERSION = "day16-execution-v2"
DIRECTIONS = ("buy_left_sell_right", "buy_right_sell_left")
DEFAULT_SIZES = (
    Decimal("10"),
    Decimal("25"),
    Decimal("50"),
    Decimal("100"),
    Decimal("250"),
    Decimal("500"),
    Decimal("1000"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _decimal(value: Any) -> Optional[Decimal]:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _bps(diff: Decimal, reference: Decimal) -> float:
    if reference is None or reference <= 0:
        return 0.0
    return float((diff / reference) * Decimal(10_000))


@dataclass(frozen=True)
class L2Level:
    price: Decimal
    size: Decimal

    def to_dict(self) -> dict[str, Any]:
        return {"price": _json_decimal(self.price), "size": _json_decimal(self.size)}


@dataclass(frozen=True)
class L2Book:
    bids: Tuple[L2Level, ...]
    asks: Tuple[L2Level, ...]
    source_time_ms: Optional[int] = None

    def __post_init__(self) -> None:
        if any(level.price <= 0 or level.size <= 0 for level in (*self.bids, *self.asks)):
            raise ValueError("L2 levels require positive price and size")
        if any(a.price < b.price for a, b in zip(self.bids, self.bids[1:])):
            raise ValueError("bid levels must be sorted descending")
        if any(a.price > b.price for a, b in zip(self.asks, self.asks[1:])):
            raise ValueError("ask levels must be sorted ascending")

    def to_dict(self) -> dict[str, Any]:
        return {
            "bids": [level.to_dict() for level in self.bids],
            "asks": [level.to_dict() for level in self.asks],
            "source_time_ms": self.source_time_ms,
        }

    @property
    def best_bid(self) -> Optional[Decimal]:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[Decimal]:
        return self.asks[0].price if self.asks else None


def _json_decimal(value: Decimal) -> float:
    """Serialize a display number while keeping all calculations Decimal."""
    return float(value)


def l2book_from_raw(identity: MarketIdentity, raw: Mapping[str, Any]) -> L2Book:
    """Parse and validate one official book response (venue aware)."""
    if identity.venue == "hyperliquid":
        if raw.get("coin") != identity.symbol:
            raise ValueError(f"{identity.selector}: coin mismatch")
        levels = raw.get("levels")
        if not isinstance(levels, list) or len(levels) != 2:
            raise ValueError(f"{identity.selector}: levels must have two sides")
        bids_raw, asks_raw = levels
        bids = _levels_from_pairs(
            ((level.get("px"), level.get("sz")) for level in (bids_raw or []))
        )
        asks = _levels_from_pairs(
            ((level.get("px"), level.get("sz")) for level in (asks_raw or []))
        )
        source_time_ms = raw.get("time")
    elif identity.venue == "lighter":
        if raw.get("code") != 200:
            raise ValueError(f"{identity.selector}: Lighter code != 200")
        bids = _levels_from_pairs(
            (
                (level.get("price"), level.get("remaining_base_amount"))
                for level in (raw.get("bids") or [])
            )
        )
        asks = _levels_from_pairs(
            (
                (level.get("price"), level.get("remaining_base_amount"))
                for level in (raw.get("asks") or [])
            )
        )
        source_time_ms = None
    else:
        raise ValueError(f"unsupported venue: {identity.venue}")
    return L2Book(
        bids=tuple(sorted(bids, key=lambda level: level.price, reverse=True)),
        asks=tuple(sorted(asks, key=lambda level: level.price)),
        source_time_ms=source_time_ms,
    )


def _levels_from_pairs(pairs: Any) -> Tuple[L2Level, ...]:
    levels = []
    for price_value, size_value in pairs:
        price = _decimal(price_value)
        size = _decimal(size_value)
        if price is None or size is None or price <= 0 or size <= 0:
            raise ValueError("book level requires finite positive price and size")
        levels.append(L2Level(price, size))
    return tuple(levels)


@dataclass(frozen=True)
class MarketSpec:
    identity: MarketIdentity
    venue: str
    taker_fee_bps: Optional[Decimal]
    maker_fee_bps: Optional[Decimal]
    size_decimals: int
    min_base_amount: Decimal
    min_quote_amount: Decimal
    multiplier: Decimal
    price_decimals: int
    max_leverage: Optional[Decimal] = None
    margin_evidence: str = "unknown"

    @property
    def quantity_step(self) -> Decimal:
        return Decimal(1).scaleb(-self.size_decimals)

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "venue": self.venue,
            "taker_fee_bps": _optional_float(self.taker_fee_bps),
            "maker_fee_bps": _optional_float(self.maker_fee_bps),
            "size_decimals": self.size_decimals,
            "min_base_amount": _json_decimal(self.min_base_amount),
            "min_quote_amount": _json_decimal(self.min_quote_amount),
            "multiplier": _json_decimal(self.multiplier),
            "price_decimals": self.price_decimals,
            "max_leverage": _optional_float(self.max_leverage),
            "margin_evidence": self.margin_evidence,
        }


def _optional_float(value: Optional[Decimal]) -> Optional[float]:
    return float(value) if value is not None else None


def normalize_lighter_details(response: Any) -> dict[int, MarketSpec]:
    """Parse orderBookDetails batch response into specs keyed by market_id."""
    if not isinstance(response, Mapping) or response.get("code") != 200:
        raise SourceShapeError("lighter orderBookDetails: expected code=200 object")
    rows = response.get("order_book_details")
    if not isinstance(rows, list):
        raise SourceShapeError("lighter orderBookDetails: order_book_details must be a list")
    specs: dict[int, MarketSpec] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        market_id = row.get("market_id")
        symbol = row.get("symbol")
        if market_id is None or not isinstance(symbol, str):
            continue
        size_decimals = row.get("supported_size_decimals", row.get("size_decimals"))
        price_decimals = row.get("supported_price_decimals", row.get("price_decimals"))
        try:
            size_decimals = int(size_decimals)
            price_decimals = int(price_decimals)
        except (TypeError, ValueError) as exc:
            raise SourceShapeError(f"lighter orderBookDetails {symbol}: bad decimals") from exc
        min_base = _required_decimal(row, "min_base_amount", symbol)
        min_quote = _required_decimal(row, "min_quote_amount", symbol)
        multiplier = _required_decimal(row, "multiplier", symbol)
        if multiplier <= 0:
            raise SourceShapeError(f"lighter orderBookDetails {symbol}: multiplier <= 0")
        taker_fee = _decimal(row.get("taker_fee"))
        maker_fee = _decimal(row.get("maker_fee"))
        default_margin = _decimal(row.get("default_initial_margin_fraction"))
        max_leverage = None
        if default_margin is not None and default_margin > 0:
            # Lighter margin fractions are integer basis points (500 = 5% = 20x).
            max_leverage = Decimal(10_000) / default_margin
        specs[int(market_id)] = MarketSpec(
            identity=MarketIdentity("lighter", "perp", "default", symbol, str(market_id)),
            venue="lighter",
            # Lighter documents the fee field as a percentage (0.05 = 5 bps).
            taker_fee_bps=taker_fee * Decimal(100) if taker_fee is not None else None,
            maker_fee_bps=maker_fee * Decimal(100) if maker_fee is not None else None,
            size_decimals=size_decimals,
            min_base_amount=min_base,
            min_quote_amount=min_quote,
            multiplier=multiplier,
            price_decimals=price_decimals,
            max_leverage=max_leverage,
            margin_evidence=(
                "public_market_default"
                if default_margin is not None
                else "unknown"
            ),
        )
    return specs


def _required_decimal(row: Mapping[str, Any], field_name: str, symbol: str) -> Decimal:
    value = _decimal(row.get(field_name))
    if value is None:
        raise SourceShapeError(
            f"lighter orderBookDetails {symbol}: missing or invalid {field_name}"
        )
    return value


def fetch_lighter_details(
    client: PublicJsonClient, market_ids: Sequence[int]
) -> dict[int, MarketSpec]:
    if not market_ids:
        return {}
    ids = ",".join(str(market_id) for market_id in sorted(market_ids))
    response = client.get(
        "lighter-order-book-details",
        f"{LIGHTER_BASE_URL}/orderBookDetails",
        {"market_ids": ids},
    )
    specs = normalize_lighter_details(response)
    missing = sorted(set(market_ids) - set(specs))
    if missing:
        raise SourceShapeError(
            f"lighter orderBookDetails omitted requested market ids: {missing}"
        )
    return specs


@dataclass(frozen=True)
class WalkResult:
    requested_qty: Decimal
    filled_qty: Decimal
    unfilled_qty: Decimal
    executed_quote: Decimal
    vwap: Optional[Decimal]
    worst_price: Optional[Decimal]
    levels_used: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_qty": _json_decimal(self.requested_qty),
            "filled_qty": _json_decimal(self.filled_qty),
            "unfilled_qty": _json_decimal(self.unfilled_qty),
            "executed_quote": _json_decimal(self.executed_quote),
            "vwap": _optional_float(self.vwap),
            "worst_price": _optional_float(self.worst_price),
            "levels_used": self.levels_used,
        }


def walk_book(
    levels: Sequence[L2Level],
    target_qty: Decimal,
    *,
    is_bid_side: bool,
) -> WalkResult:
    """Walk one sorted book side without inventing liquidity."""
    if target_qty < 0:
        raise ValueError("target_qty must be non-negative")
    remaining = target_qty
    total_quote = Decimal(0)
    filled = Decimal(0)
    worst: Optional[Decimal] = None
    used = 0
    for level in levels:
        if remaining <= 0:
            break
        take = min(remaining, level.size)
        if take <= 0:
            continue
        total_quote += take * level.price
        filled += take
        remaining -= take
        worst = level.price
        used += 1
    return WalkResult(
        requested_qty=target_qty,
        filled_qty=filled,
        unfilled_qty=remaining,
        executed_quote=total_quote,
        vwap=(total_quote / filled) if filled > 0 else None,
        worst_price=worst,
        levels_used=used,
    )


def order_qty_for_notional(
    *,
    notional_usd: Decimal,
    price: Decimal,
    size_decimals: int,
    min_base_amount: Decimal,
    min_quote_amount: Decimal,
    multiplier: Decimal,
) -> Decimal:
    """Floor target notional to one venue's quantity grid."""
    qty, _ = _order_qty_with_reason(
        notional_usd=notional_usd,
        price=price,
        size_decimals=size_decimals,
        min_base_amount=min_base_amount,
        min_quote_amount=min_quote_amount,
        multiplier=multiplier,
    )
    return qty


def _order_qty_with_reason(
    *,
    notional_usd: Decimal,
    price: Decimal,
    size_decimals: int,
    min_base_amount: Decimal,
    min_quote_amount: Decimal,
    multiplier: Decimal,
) -> Tuple[Decimal, str]:
    if notional_usd <= 0:
        return Decimal(0), "BAD_NOTIONAL"
    if price <= 0 or multiplier <= 0:
        return Decimal(0), "BAD_PRICE_OR_MULTIPLIER"
    step = Decimal(1).scaleb(-size_decimals)
    raw = notional_usd / (price * multiplier)
    qty = raw.quantize(step, rounding=ROUND_DOWN)
    if qty < min_base_amount:
        return Decimal(0), "MIN_BASE"
    if qty * price * multiplier < min_quote_amount:
        return Decimal(0), "MIN_QUOTE"
    return qty, "OK"


@dataclass(frozen=True)
class CommonExposure:
    exposure_units: Decimal
    left_qty: Decimal
    right_qty: Decimal
    reason: str


def common_exposure_for_notional(
    left_spec: MarketSpec,
    left_price: Decimal,
    right_spec: MarketSpec,
    right_price: Decimal,
    *,
    target_notional_usd: Decimal,
) -> CommonExposure:
    """Largest exactly hedgeable exposure not exceeding target notional.

    Exposure units are base quantity multiplied by contract multiplier. Both
    venue quantities are quantized down until `left_qty * left_multiplier ==
    right_qty * right_multiplier` exactly. If no common legal quantity exists,
    the pair is blocked instead of leaving a residual exposure.
    """
    if target_notional_usd <= 0 or left_price <= 0 or right_price <= 0:
        return CommonExposure(Decimal(0), Decimal(0), Decimal(0), "BAD_TARGET")
    left_exposure_step = left_spec.quantity_step * left_spec.multiplier
    right_exposure_step = right_spec.quantity_step * right_spec.multiplier
    exposure_step = _decimal_lcm(left_exposure_step, right_exposure_step)
    max_exposure = min(
        target_notional_usd / left_price,
        target_notional_usd / right_price,
    )
    exposure_units = (max_exposure / exposure_step).to_integral_value(
        rounding=ROUND_DOWN
    ) * exposure_step
    if exposure_units <= 0:
        return CommonExposure(Decimal(0), Decimal(0), Decimal(0), "NO_COMMON_GRID")
    left_qty = exposure_units / left_spec.multiplier
    right_qty = exposure_units / right_spec.multiplier
    if left_qty < left_spec.min_base_amount or right_qty < right_spec.min_base_amount:
        return CommonExposure(Decimal(0), Decimal(0), Decimal(0), "MIN_BASE")
    if left_qty * left_price * left_spec.multiplier < left_spec.min_quote_amount:
        return CommonExposure(Decimal(0), Decimal(0), Decimal(0), "MIN_QUOTE_LEFT")
    if right_qty * right_price * right_spec.multiplier < right_spec.min_quote_amount:
        return CommonExposure(Decimal(0), Decimal(0), Decimal(0), "MIN_QUOTE_RIGHT")
    return CommonExposure(exposure_units, left_qty, right_qty, "OK")


def _common_exposure_from_units(
    left_spec: MarketSpec,
    left_price: Decimal,
    right_spec: MarketSpec,
    right_price: Decimal,
    *,
    exposure_units: Decimal,
) -> CommonExposure:
    """Validate an explicit common exposure against both venue grids/minima."""
    if exposure_units <= 0:
        return CommonExposure(Decimal(0), Decimal(0), Decimal(0), "BAD_TARGET")
    left_qty = exposure_units / left_spec.multiplier
    right_qty = exposure_units / right_spec.multiplier
    if left_qty % left_spec.quantity_step != 0 or right_qty % right_spec.quantity_step != 0:
        return CommonExposure(Decimal(0), Decimal(0), Decimal(0), "NO_COMMON_GRID")
    if left_qty < left_spec.min_base_amount or right_qty < right_spec.min_base_amount:
        return CommonExposure(Decimal(0), Decimal(0), Decimal(0), "MIN_BASE")
    if left_qty * left_price * left_spec.multiplier < left_spec.min_quote_amount:
        return CommonExposure(Decimal(0), Decimal(0), Decimal(0), "MIN_QUOTE_LEFT")
    if right_qty * right_price * right_spec.multiplier < right_spec.min_quote_amount:
        return CommonExposure(Decimal(0), Decimal(0), Decimal(0), "MIN_QUOTE_RIGHT")
    return CommonExposure(exposure_units, left_qty, right_qty, "OK")


def _decimal_lcm(left: Decimal, right: Decimal) -> Decimal:
    """Least common multiple for positive finite Decimal grid steps."""
    if left <= 0 or right <= 0:
        raise ValueError("grid steps must be positive")
    scale_exp = max(-left.as_tuple().exponent, -right.as_tuple().exponent)
    scale = Decimal(1).scaleb(-scale_exp)
    left_int = int(left / scale)
    right_int = int(right / scale)
    from math import gcd

    return Decimal(abs(left_int * right_int) // gcd(left_int, right_int)) * scale


@dataclass(frozen=True)
class LegResult:
    venue: str
    side: str
    orderable: bool
    orderable_reason: str
    target_qty: Decimal
    requested_notional_usd: Decimal
    filled_qty: Decimal
    unfilled_qty: Decimal
    executed_notional_usd: Decimal
    unfilled_notional_usd: Decimal
    vwap: Optional[Decimal]
    top_price: Optional[Decimal]
    slippage_bps: float
    fee_bps: Optional[float]
    fee_cost_usd: Optional[Decimal]
    levels_used: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue": self.venue,
            "side": self.side,
            "orderable": self.orderable,
            "orderable_reason": self.orderable_reason,
            "target_qty": _json_decimal(self.target_qty),
            "requested_notional_usd": _json_decimal(self.requested_notional_usd),
            "filled_qty": _json_decimal(self.filled_qty),
            "unfilled_qty": _json_decimal(self.unfilled_qty),
            "executed_notional_usd": _json_decimal(self.executed_notional_usd),
            "unfilled_notional_usd": _json_decimal(self.unfilled_notional_usd),
            "vwap": _optional_float(self.vwap),
            "top_price": _optional_float(self.top_price),
            "slippage_bps": self.slippage_bps,
            "fee_bps": self.fee_bps,
            "fee_cost_usd": _optional_float(self.fee_cost_usd),
            "levels_used": self.levels_used,
        }


def leg_execution(
    spec: MarketSpec,
    l2book: L2Book,
    *,
    side: str,
    target_notional_usd: Optional[Decimal] = None,
    target_qty: Optional[Decimal] = None,
) -> LegResult:
    """One aggressive leg at an explicit legal quantity or target notional."""
    if side not in {"buy", "sell"}:
        raise ValueError("side must be buy or sell")
    if (target_notional_usd is None) == (target_qty is None):
        raise ValueError("provide exactly one of target_notional_usd or target_qty")
    levels = l2book.asks if side == "buy" else l2book.bids
    top_price = levels[0].price if levels else None
    requested_notional = target_notional_usd or Decimal(0)
    if top_price is None:
        return _blocked_leg(spec, side, "NO_TOP_OF_BOOK", requested_notional)
    if target_qty is None:
        target_qty, reason = _order_qty_with_reason(
            notional_usd=target_notional_usd,
            price=top_price,
            size_decimals=spec.size_decimals,
            min_base_amount=spec.min_base_amount,
            min_quote_amount=spec.min_quote_amount,
            multiplier=spec.multiplier,
        )
        if target_qty <= 0:
            return _blocked_leg(spec, side, reason, requested_notional, top_price)
    else:
        if target_qty <= 0 or target_qty % spec.quantity_step != 0:
            return _blocked_leg(spec, side, "INVALID_QUANTITY_GRID", Decimal(0), top_price)
        requested_notional = target_qty * top_price * spec.multiplier
        if target_qty < spec.min_base_amount:
            return _blocked_leg(spec, side, "MIN_BASE", requested_notional, top_price)
        if requested_notional < spec.min_quote_amount:
            return _blocked_leg(spec, side, "MIN_QUOTE", requested_notional, top_price)
    walked = walk_book(levels, target_qty, is_bid_side=(side == "sell"))
    vwap = walked.vwap
    slippage = 0.0
    if vwap is not None:
        diff = (vwap - top_price) if side == "buy" else (top_price - vwap)
        slippage = _bps(diff, top_price)
    executed_notional = walked.executed_quote * spec.multiplier
    unfilled_notional = walked.unfilled_qty * top_price * spec.multiplier
    fee_bps = _optional_float(spec.taker_fee_bps)
    fee_cost = (
        executed_notional * spec.taker_fee_bps / Decimal(10_000)
        if spec.taker_fee_bps is not None
        else None
    )
    return LegResult(
        venue=spec.venue,
        side=side,
        orderable=True,
        orderable_reason="OK",
        target_qty=target_qty,
        requested_notional_usd=requested_notional,
        filled_qty=walked.filled_qty,
        unfilled_qty=walked.unfilled_qty,
        executed_notional_usd=executed_notional,
        unfilled_notional_usd=unfilled_notional,
        vwap=vwap,
        top_price=top_price,
        slippage_bps=round(slippage, 4),
        fee_bps=fee_bps,
        fee_cost_usd=fee_cost,
        levels_used=walked.levels_used,
    )


def _blocked_leg(
    spec: MarketSpec,
    side: str,
    reason: str,
    requested_notional: Decimal,
    top_price: Optional[Decimal] = None,
) -> LegResult:
    return LegResult(
        venue=spec.venue,
        side=side,
        orderable=False,
        orderable_reason=reason,
        target_qty=Decimal(0),
        requested_notional_usd=requested_notional,
        filled_qty=Decimal(0),
        unfilled_qty=Decimal(0),
        executed_notional_usd=Decimal(0),
        unfilled_notional_usd=Decimal(0),
        vwap=None,
        top_price=top_price,
        slippage_bps=0.0,
        fee_bps=_optional_float(spec.taker_fee_bps),
        fee_cost_usd=Decimal(0) if spec.taker_fee_bps is not None else None,
        levels_used=0,
    )


@dataclass(frozen=True)
class PairResult:
    direction: str
    common_exposure_units: Decimal
    common_base_qty: Decimal
    buy: LegResult
    sell: LegResult
    top_of_book_spread_bps: Optional[float]
    executable_spread_bps: Optional[float]
    slippage_cost_bps: float
    reference_notional_usd: Decimal
    price_pnl_usd: Optional[Decimal]
    fee_cost_bps: Optional[float]
    fee_cost_usd: Optional[Decimal]
    price_pnl_bps: Optional[float]
    net_price_pnl_usd: Optional[Decimal]
    net_price_pnl_bps: Optional[float]
    fill_pct: float
    residual_base_qty: Decimal
    reason_codes: Tuple[str, ...]

    # Backward-compatible aliases: old JSON consumers used these names.
    @property
    def capture_bps(self) -> Optional[float]:
        return self.executable_spread_bps

    @property
    def net_spread_bps(self) -> Optional[float]:
        return self.price_pnl_bps

    @property
    def total_cost_bps(self) -> Optional[float]:
        return self.net_price_pnl_bps

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "common_exposure_units": _json_decimal(self.common_exposure_units),
            "common_base_qty": _json_decimal(self.common_base_qty),
            "buy": self.buy.to_dict(),
            "sell": self.sell.to_dict(),
            "top_of_book_spread_bps": self.top_of_book_spread_bps,
            "executable_spread_bps": self.executable_spread_bps,
            "capture_bps": self.executable_spread_bps,
            "slippage_cost_bps": self.slippage_cost_bps,
            "reference_notional_usd": _json_decimal(self.reference_notional_usd),
            "price_pnl_usd": _optional_float(self.price_pnl_usd),
            "fee_cost_bps": self.fee_cost_bps,
            "fee_cost_usd": _optional_float(self.fee_cost_usd),
            "price_pnl_bps": self.price_pnl_bps,
            "net_spread_bps": self.price_pnl_bps,
            "net_price_pnl_usd": _optional_float(self.net_price_pnl_usd),
            "net_price_pnl_bps": self.net_price_pnl_bps,
            "total_cost_bps": self.net_price_pnl_bps,
            "fill_pct": self.fill_pct,
            "residual_base_qty": _json_decimal(self.residual_base_qty),
            "reason_codes": list(self.reason_codes),
        }


def pair_execution(
    left_spec: MarketSpec,
    left_book: L2Book,
    right_spec: MarketSpec,
    right_book: L2Book,
    *,
    direction: str,
    target_notional_usd: Optional[Decimal] = None,
    exposure_units: Optional[Decimal] = None,
) -> PairResult:
    """Execute two legs at one exactly common economic exposure."""
    if (target_notional_usd is None) == (exposure_units is None):
        raise ValueError("provide exactly one of target_notional_usd or exposure_units")
    if direction == "buy_left_sell_right":
        buy_spec, buy_book, buy_side = left_spec, left_book, "left"
        sell_spec, sell_book, sell_side = right_spec, right_book, "right"
    elif direction == "buy_right_sell_left":
        buy_spec, buy_book, buy_side = right_spec, right_book, "right"
        sell_spec, sell_book, sell_side = left_spec, left_book, "left"
    else:
        raise ValueError(f"unknown direction {direction!r}")
    buy_top = buy_book.best_ask
    sell_top = sell_book.best_bid
    if buy_top is None or sell_top is None:
        return _blocked_pair(
            direction,
            left_spec,
            right_spec,
            "NO_TOP_OF_BOOK",
        )
    if exposure_units is None:
        assert target_notional_usd is not None
        exposure = common_exposure_for_notional(
            buy_spec,
            buy_top,
            sell_spec,
            sell_top,
            target_notional_usd=target_notional_usd,
        )
    else:
        exposure = _common_exposure_from_units(
            buy_spec,
            buy_top,
            sell_spec,
            sell_top,
            exposure_units=exposure_units,
        )
    if exposure.reason != "OK":
        return _blocked_pair(
            direction,
            left_spec,
            right_spec,
            exposure.reason,
        )
    buy_qty = exposure.left_qty
    sell_qty = exposure.right_qty
    if buy_side == "right":
        buy_qty, sell_qty = sell_qty, buy_qty
    buy_leg = leg_execution(buy_spec, buy_book, side="buy", target_qty=buy_qty)
    sell_leg = leg_execution(sell_spec, sell_book, side="sell", target_qty=sell_qty)
    filled_buy_exposure = buy_leg.filled_qty * buy_spec.multiplier
    filled_sell_exposure = sell_leg.filled_qty * sell_spec.multiplier
    residual = abs(filled_buy_exposure - filled_sell_exposure)
    reference = (buy_top + sell_top) / Decimal(2)
    top_spread = _bps(sell_top - buy_top, reference)
    full_fill = (
        buy_leg.unfilled_qty == 0
        and sell_leg.unfilled_qty == 0
        and residual == 0
    )
    executable_spread: Optional[float] = None
    reference_notional = exposure.exposure_units * reference
    price_pnl_usd: Optional[Decimal] = None
    if full_fill and buy_leg.vwap is not None and sell_leg.vwap is not None:
        price_pnl_usd = exposure.exposure_units * (sell_leg.vwap - buy_leg.vwap)
        executable_spread = _bps(price_pnl_usd, reference_notional)
    slippage_cost = round(buy_leg.slippage_bps + sell_leg.slippage_bps, 4)
    fee_cost_usd: Optional[Decimal] = None
    fee_cost: Optional[float] = None
    if buy_leg.fee_cost_usd is not None and sell_leg.fee_cost_usd is not None:
        fee_cost_usd = buy_leg.fee_cost_usd + sell_leg.fee_cost_usd
        fee_cost = round(_bps(fee_cost_usd, reference_notional), 4)
    net_price_pnl_usd = (
        price_pnl_usd - fee_cost_usd
        if price_pnl_usd is not None and fee_cost_usd is not None
        else None
    )
    net_price_pnl = (
        round(_bps(net_price_pnl_usd, reference_notional), 4)
        if net_price_pnl_usd is not None
        else None
    )
    buy_fill = (
        buy_leg.filled_qty / buy_leg.target_qty
        if buy_leg.target_qty > 0
        else Decimal(0)
    )
    sell_fill = (
        sell_leg.filled_qty / sell_leg.target_qty
        if sell_leg.target_qty > 0
        else Decimal(0)
    )
    reason_codes = []
    if buy_leg.unfilled_qty > 0 or sell_leg.unfilled_qty > 0:
        reason_codes.append("DEPTH_INSUFFICIENT")
    if residual > 0:
        reason_codes.append("RESIDUAL_EXPOSURE")
    if fee_cost is None:
        reason_codes.append("FEE_UNKNOWN")
    return PairResult(
        direction=direction,
        common_exposure_units=exposure.exposure_units,
        common_base_qty=exposure.exposure_units,
        buy=buy_leg,
        sell=sell_leg,
        top_of_book_spread_bps=round(top_spread, 4),
        executable_spread_bps=(
            round(executable_spread, 4) if executable_spread is not None else None
        ),
        slippage_cost_bps=slippage_cost,
        reference_notional_usd=reference_notional,
        price_pnl_usd=price_pnl_usd,
        fee_cost_bps=fee_cost,
        fee_cost_usd=fee_cost_usd,
        price_pnl_bps=(
            round(executable_spread, 4) if executable_spread is not None else None
        ),
        net_price_pnl_usd=net_price_pnl_usd,
        net_price_pnl_bps=net_price_pnl,
        fill_pct=float(min(buy_fill, sell_fill)),
        residual_base_qty=residual,
        reason_codes=tuple(reason_codes),
    )


def _blocked_pair(
    direction: str,
    left_spec: MarketSpec,
    right_spec: MarketSpec,
    reason: str,
) -> PairResult:
    if direction == "buy_left_sell_right":
        buy_spec, sell_spec = left_spec, right_spec
    else:
        buy_spec, sell_spec = right_spec, left_spec
    return PairResult(
        direction=direction,
        common_exposure_units=Decimal(0),
        common_base_qty=Decimal(0),
        buy=_blocked_leg(buy_spec, "buy", reason, Decimal(0)),
        sell=_blocked_leg(sell_spec, "sell", reason, Decimal(0)),
        top_of_book_spread_bps=None,
        executable_spread_bps=None,
        slippage_cost_bps=0.0,
        reference_notional_usd=Decimal(0),
        price_pnl_usd=None,
        fee_cost_bps=None,
        fee_cost_usd=None,
        price_pnl_bps=None,
        net_price_pnl_usd=None,
        net_price_pnl_bps=None,
        fill_pct=0.0,
        residual_base_qty=Decimal(0),
        reason_codes=(reason,),
    )


@dataclass(frozen=True)
class RoundTripResult:
    entry: PairResult
    exit: PairResult
    reference_notional_usd: Decimal
    round_trip_price_pnl_usd: Optional[Decimal]
    round_trip_price_pnl_bps: Optional[float]
    round_trip_net_pnl_usd: Optional[Decimal]
    round_trip_net_pnl_bps: Optional[float]
    fee_cost_usd: Optional[Decimal]
    fee_cost_bps: Optional[float]
    funding_pnl_bps: Optional[float]
    limitations: Tuple[str, ...]

    def compact_dict(self) -> dict[str, Any]:
        """Snapshot representation without duplicating the already stored entry."""
        return {
            "exit": self.exit.to_dict(),
            "reference_notional_usd": _json_decimal(self.reference_notional_usd),
            "round_trip_price_pnl_usd": _optional_float(self.round_trip_price_pnl_usd),
            "round_trip_price_pnl_bps": self.round_trip_price_pnl_bps,
            "round_trip_net_pnl_usd": _optional_float(self.round_trip_net_pnl_usd),
            "round_trip_net_pnl_bps": self.round_trip_net_pnl_bps,
            "fee_cost_usd": _optional_float(self.fee_cost_usd),
            "fee_cost_bps": self.fee_cost_bps,
            "funding_pnl_bps": self.funding_pnl_bps,
            "limitations": list(self.limitations),
        }

    def to_dict(self) -> dict[str, Any]:
        return {"entry": self.entry.to_dict(), **self.compact_dict()}


def round_trip_execution(
    left_spec: MarketSpec,
    left_book: L2Book,
    right_spec: MarketSpec,
    right_book: L2Book,
    *,
    direction: str,
    target_notional_usd: Decimal,
) -> RoundTripResult:
    """Four aggressive fills using the same frozen entry/exit books.

    Same-book exit is a conservative transaction-cost baseline, not a future
    exit forecast. Funding remains unknown until a holding interval is supplied.
    """
    entry = pair_execution(
        left_spec,
        left_book,
        right_spec,
        right_book,
        direction=direction,
        target_notional_usd=target_notional_usd,
    )
    exit_direction = (
        "buy_right_sell_left"
        if direction == "buy_left_sell_right"
        else "buy_left_sell_right"
    )
    exit_result = pair_execution(
        left_spec,
        left_book,
        right_spec,
        right_book,
        direction=exit_direction,
        exposure_units=entry.common_exposure_units,
    )
    reference_notional = entry.reference_notional_usd
    price_pnl_usd = None
    if entry.price_pnl_usd is not None and exit_result.price_pnl_usd is not None:
        price_pnl_usd = entry.price_pnl_usd + exit_result.price_pnl_usd
    price_pnl = (
        round(_bps(price_pnl_usd, reference_notional), 4)
        if price_pnl_usd is not None and reference_notional > 0
        else None
    )
    fee_cost_usd = None
    if entry.fee_cost_usd is not None and exit_result.fee_cost_usd is not None:
        fee_cost_usd = entry.fee_cost_usd + exit_result.fee_cost_usd
    fee_cost = (
        round(_bps(fee_cost_usd, reference_notional), 4)
        if fee_cost_usd is not None and reference_notional > 0
        else None
    )
    net_pnl_usd = (
        price_pnl_usd - fee_cost_usd
        if price_pnl_usd is not None and fee_cost_usd is not None
        else None
    )
    net = (
        round(_bps(net_pnl_usd, reference_notional), 4)
        if net_pnl_usd is not None and reference_notional > 0
        else None
    )
    return RoundTripResult(
        entry=entry,
        exit=exit_result,
        reference_notional_usd=reference_notional,
        round_trip_price_pnl_usd=price_pnl_usd,
        round_trip_price_pnl_bps=price_pnl,
        round_trip_net_pnl_usd=net_pnl_usd,
        round_trip_net_pnl_bps=net,
        fee_cost_usd=fee_cost_usd,
        fee_cost_bps=fee_cost,
        funding_pnl_bps=None,
        limitations=(
            "SAME_FROZEN_BOOK_EXIT_BASELINE",
            "FUNDING_UNKNOWN_WITHOUT_HOLDING_INTERVAL",
            "MARGIN_USES_PUBLIC_MARKET_DEFAULTS_ONLY",
        ),
    )


@dataclass(frozen=True)
class CapacityResult:
    max_full_fill_usd: Decimal
    lower_bound_only: bool
    first_failed_size_usd: Optional[Decimal]

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_full_fill_usd": _json_decimal(self.max_full_fill_usd),
            "lower_bound_only": self.lower_bound_only,
            "first_failed_size_usd": _optional_float(self.first_failed_size_usd),
        }


def capacity_result(
    left_spec: MarketSpec,
    left_book: L2Book,
    right_spec: MarketSpec,
    right_book: L2Book,
    *,
    direction: str,
    sizes: Sequence[Decimal],
) -> CapacityResult:
    ordered_sizes = tuple(sorted(set(sizes)))
    best = Decimal(0)
    started = False
    first_failed: Optional[Decimal] = None
    for size in ordered_sizes:
        result = pair_execution(
            left_spec,
            left_book,
            right_spec,
            right_book,
            direction=direction,
            target_notional_usd=size,
        )
        orderable = result.buy.orderable and result.sell.orderable
        if not orderable:
            if started:
                first_failed = size
                break
            continue
        started = True
        full = (
            result.buy.unfilled_qty == 0
            and result.sell.unfilled_qty == 0
            and result.residual_base_qty == 0
        )
        if full:
            best = size
        else:
            first_failed = size
            break
    lower_bound_only = bool(ordered_sizes and best == ordered_sizes[-1])
    return CapacityResult(best, lower_bound_only, first_failed)


def capacity_usd(
    left_spec: MarketSpec,
    left_book: L2Book,
    right_spec: MarketSpec,
    right_book: L2Book,
    *,
    direction: str,
    sizes: Sequence[Decimal],
) -> Decimal:
    """Backward-compatible scalar capacity; prefer capacity_result()."""
    return capacity_result(
        left_spec,
        left_book,
        right_spec,
        right_book,
        direction=direction,
        sizes=sizes,
    ).max_full_fill_usd


@dataclass(frozen=True)
class ExecutionPair:
    pair_name: str
    left_spec: MarketSpec
    right_spec: MarketSpec
    left_book: L2Book
    right_book: L2Book
    per_size: Tuple[Mapping[str, Any], ...]
    capacity: Mapping[str, CapacityResult]

    @property
    def capacity_usd(self) -> Mapping[str, float]:
        return {
            direction: float(result.max_full_fill_usd)
            for direction, result in self.capacity.items()
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_name": self.pair_name,
            "left": self.left_spec.to_dict(),
            "right": self.right_spec.to_dict(),
            "left_book": self.left_book.to_dict(),
            "right_book": self.right_book.to_dict(),
            "per_size": list(self.per_size),
            "capacity": {
                direction: result.to_dict()
                for direction, result in self.capacity.items()
            },
            "capacity_usd": dict(self.capacity_usd),
        }


@dataclass(frozen=True)
class ExecutionSnapshot:
    schema: str
    observed_at: str
    scanned_at: str
    read_only: bool
    execution_client_present: bool
    sizes_usd: Tuple[Decimal, ...]
    pairs: Tuple[ExecutionPair, ...]
    request_errors: Tuple[Tuple[str, str], ...] = ()
    boundaries: Tuple[str, ...] = ()
    refresh_mode: str = "static_file"
    capture_span_ms: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "observed_at": self.observed_at,
            "scanned_at": self.scanned_at,
            "read_only": self.read_only,
            "execution_client_present": self.execution_client_present,
            "refresh_mode": self.refresh_mode,
            "capture_span_ms": self.capture_span_ms,
            "sizes_usd": [_json_decimal(size) for size in self.sizes_usd],
            "pairs": [pair.to_dict() for pair in self.pairs],
            "request_errors": [
                {"selector": selector, "reason_code": reason_code}
                for selector, reason_code in self.request_errors
            ],
            "boundaries": list(self.boundaries),
        }


def build_execution_snapshot(
    left_specs: Sequence[MarketSpec],
    right_specs: Sequence[MarketSpec],
    books: Mapping[MarketIdentity, L2Book],
    *,
    sizes_usd: Sequence[Decimal] = (),
    observed_at: Optional[str] = None,
    scanned_at: Optional[str] = None,
    request_errors: Sequence[Tuple[str, str]] = (),
    refresh_mode: str = "static_file",
    capture_span_ms: Optional[float] = None,
) -> ExecutionSnapshot:
    sizes = tuple(sizes_usd) if sizes_usd else DEFAULT_SIZES
    if any(size <= 0 for size in sizes):
        raise ValueError("sizes_usd must contain positive values")
    left_by_identity = {spec.identity: spec for spec in left_specs}
    right_by_identity = {spec.identity: spec for spec in right_specs}
    pairs = []
    for left_identity, right_identity in _pair_identities(left_specs, right_specs):
        left_spec = left_by_identity[left_identity]
        right_spec = right_by_identity[right_identity]
        left_book = books.get(left_identity)
        right_book = books.get(right_identity)
        if left_book is None or right_book is None:
            continue
        pair_name = f"{left_spec.identity.symbol}__{right_spec.identity.symbol}"
        per_size = []
        for size in sizes:
            row: dict[str, Any] = {"size_usd": _json_decimal(size)}
            for direction in DIRECTIONS:
                row[direction] = pair_execution(
                    left_spec,
                    left_book,
                    right_spec,
                    right_book,
                    direction=direction,
                    target_notional_usd=size,
                ).to_dict()
                row[f"{direction}_round_trip"] = round_trip_execution(
                    left_spec,
                    left_book,
                    right_spec,
                    right_book,
                    direction=direction,
                    target_notional_usd=size,
                ).compact_dict()
            per_size.append(row)
        capacity = {
            direction: capacity_result(
                left_spec,
                left_book,
                right_spec,
                right_book,
                direction=direction,
                sizes=sizes,
            )
            for direction in DIRECTIONS
        }
        pairs.append(
            ExecutionPair(
                pair_name=pair_name,
                left_spec=left_spec,
                right_spec=right_spec,
                left_book=left_book,
                right_book=right_book,
                per_size=tuple(per_size),
                capacity=capacity,
            )
        )
    return ExecutionSnapshot(
        schema=SCHEMA,
        observed_at=observed_at or _utc_now(),
        scanned_at=scanned_at or _utc_now(),
        read_only=True,
        execution_client_present=False,
        sizes_usd=sizes,
        pairs=tuple(pairs),
        request_errors=tuple(request_errors),
        boundaries=BOUNDARIES,
        refresh_mode=refresh_mode,
        capture_span_ms=capture_span_ms,
    )

def _discover_pairs(
    lighter: Sequence[CatalogMarket],
    hyperliquid: Sequence[CatalogMarket],
) -> Tuple[Tuple[CatalogMarket, CatalogMarket, str], ...]:
    lighter_by_symbol: dict[str, CatalogMarket] = {}
    for market in lighter:
        if market.catalog_status == "active":
            lighter_by_symbol[market.identity.symbol] = market
    pairs = []
    seen = set()
    for hl_market in sorted(
        hyperliquid, key=lambda market: market.identity.symbol
    ):
        if hl_market.catalog_status != "active":
            continue
        hl_symbol = hl_market.identity.symbol
        if not hl_symbol.startswith("xyz:"):
            continue
        base = hl_symbol.split(":", 1)[1]
        candidate = lighter_by_symbol.get(base)
        if candidate is None:
            continue
        pair_name = f"{candidate.identity.symbol}__{hl_symbol}"
        if pair_name in seen:
            continue
        seen.add(pair_name)
        pairs.append((candidate, hl_market, pair_name))
    return tuple(pairs)


BOUNDARIES = (
    "Frozen L2 snapshots prove target-size executable prices at one moment only; "
    "they do not prove persistent depth or counterparty willingness after our order enters.",
    "Both legs use one exactly common economic exposure after multiplier and quantity-grid "
    "rounding; a pair with no common legal quantity is blocked instead of leaving hidden exposure.",
    "Lighter fees are market-spec percentages (0.05 -> 5 bps); account-level schedules "
    "and Hyperliquid HIP-3 fees remain unknown unless verified, so net_price_pnl_bps stays null.",
    "Executable spread already uses target-size VWAP. Slippage is shown only as the "
    "top-of-book-to-VWAP decomposition and is never deducted a second time.",
    "The same frozen books provide a four-aggressive-fill round-trip cost baseline; "
    "future exit state and funding remain unknown without a holding interval.",
    "Capacity is a tested-size result. If the largest tier still fills, it is reported as "
    "a lower bound (for example >= $1000), not exact capacity.",
    "mark/oracle/mid never replace executable prices. Public market margin fields do "
    "not prove account permissions or available collateral.",
)


def _pair_identities(
    left_specs: Sequence[MarketSpec],
    right_specs: Sequence[MarketSpec],
) -> Tuple[Tuple[MarketIdentity, MarketIdentity], ...]:
    left_by_symbol: dict[str, MarketSpec] = {}
    for spec in left_specs:
        left_by_symbol[spec.identity.symbol] = spec
    pairs = []
    seen = set()
    for right_spec in sorted(right_specs, key=lambda spec: spec.identity.symbol):
        symbol = right_spec.identity.symbol
        if not symbol.startswith("xyz:"):
            continue
        base = symbol.split(":", 1)[1]
        left_spec = left_by_symbol.get(base)
        if left_spec is None:
            continue
        pair_name = f"{left_spec.identity.symbol}__{symbol}"
        if pair_name in seen:
            continue
        seen.add(pair_name)
        pairs.append((left_spec.identity, right_spec.identity))
    return tuple(pairs)


def write_snapshot_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    """Write a complete snapshot and atomically publish it at ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def publish_snapshot_if_complete(
    path: Path, snapshot: ExecutionSnapshot, payload: Mapping[str, Any]
) -> bool:
    """Atomically publish a successful scan; preserve the prior file on errors."""
    if snapshot.request_errors:
        return False
    write_snapshot_atomic(path, payload)
    return True


def run_execution_scan(args: argparse.Namespace) -> int:
    client = PublicJsonClient(timeout=args.timeout)
    lighter_catalog = fetch_lighter_catalog(client)
    hyperliquid_catalog = fetch_hyperliquid_catalog(client, "xyz")
    pairs = _discover_pairs(lighter_catalog, hyperliquid_catalog)
    lighter_participants = sorted({pair[0].identity.local_id for pair in pairs})
    details = fetch_lighter_details(client, [int(market_id) for market_id in lighter_participants])
    lighter_specs = list(details.values())
    spec_errors: list[Tuple[str, str]] = []
    right_specs = []
    for market in hyperliquid_catalog:
        if market.catalog_status != "active" or not market.identity.symbol.startswith("xyz:"):
            continue
        sz_decimals = market.context.get("szDecimals")
        max_leverage = _decimal(market.context.get("maxLeverage"))
        if not isinstance(sz_decimals, int):
            spec_errors.append(
                (market.identity.selector, "SIZE_PRECISION_UNKNOWN")
            )
            # Do not invent a quantity grid; exclude the market explicitly.
            continue
        right_specs.append(
            MarketSpec(
                identity=market.identity,
                venue="hyperliquid",
                taker_fee_bps=None,
                maker_fee_bps=None,
                size_decimals=sz_decimals,
                # Hyperliquid's public meta omits min order quantity; the
                # documented minimum notional is retained and min base stays 0.
                min_base_amount=Decimal(0),
                min_quote_amount=Decimal(10),
                multiplier=Decimal(1),
                price_decimals=0,
                max_leverage=max_leverage,
                margin_evidence=(
                    "public_market_max_leverage"
                    if max_leverage is not None
                    else "unknown"
                ),
            )
        )
    # Keep only mapped right specs that have a Lighter counterpart.
    mapped_symbols = {pair[1].identity.symbol for pair in pairs}
    right_specs = [spec for spec in right_specs if spec.identity.symbol in mapped_symbols]

    books: dict[MarketIdentity, L2Book] = {}
    request_errors: list[Tuple[str, str]] = list(spec_errors)
    selected_pairs = pairs[: args.max_pairs] if args.max_pairs else pairs
    capture_started = datetime.now(timezone.utc)
    fetched_identities: set[MarketIdentity] = set()
    for pair in selected_pairs:
        left_market, right_market, _ = pair
        for market in (left_market, right_market):
            if market.identity in fetched_identities:
                continue
            fetched_identities.add(market.identity)
            try:
                if market.identity.venue == "lighter":
                    if args.pacing > 0 and client.captures:
                        time.sleep(args.pacing)
                    raw = fetch_lighter_book(client, market, limit=args.book_limit)
                else:
                    raw = fetch_hyperliquid_book(client, market)
                books[market.identity] = l2book_from_raw(market.identity, raw)
            except (SourceRequestError, ValueError) as exc:
                request_errors.append((market.identity.selector, f"REQUEST_FAILED:{type(exc).__name__}"))
    observed_at = client.captures[-1].received_at if client.captures else _utc_now()
    capture_span_ms = round(
        (datetime.now(timezone.utc) - capture_started).total_seconds() * 1000,
        3,
    )
    snapshot = build_execution_snapshot(
        lighter_specs,
        right_specs,
        books,
        sizes_usd=args.sizes,
        observed_at=observed_at,
        request_errors=tuple(request_errors),
        refresh_mode="live_scan",
        capture_span_ms=capture_span_ms,
    )
    payload = snapshot.to_dict()
    payload["scanned_pairs"] = [
        {"pair_name": pair_name, "left": left.identity.selector, "right": right.identity.selector}
        for left, right, pair_name in selected_pairs
    ]
    output_path = Path(args.output)
    published = publish_snapshot_if_complete(output_path, snapshot, payload)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "published": published,
                "pair_count": len(snapshot.pairs),
                "discovered_pair_count": len(selected_pairs),
                "book_count": len(books),
                "request_errors": list(request_errors),
                "top_pair": snapshot.pairs[0].pair_name if snapshot.pairs else None,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 2 if snapshot.request_errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m monte_arb.execution_engine",
        description="Read-only Day16 execution and capacity scan.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="research/runs/day16-execution-scan.json",
        help="output JSON path",
    )
    parser.add_argument("--book-limit", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-pairs", type=int, default=None)
    parser.add_argument("--pacing", type=float, default=1.1)
    parser.add_argument("--sizes", type=str, default="10,25,50,100,250,500,1000")
    return parser


def load_snapshot(path: Path) -> ExecutionSnapshot:
    payload = json.loads(path.read_text())
    sizes = tuple(Decimal(str(size)) for size in payload["sizes_usd"])
    pairs = []
    for row in payload["pairs"]:
        left = _spec_from_dict(row["left"])
        right = _spec_from_dict(row["right"])
        pairs.append(
            ExecutionPair(
                pair_name=row["pair_name"],
                left_spec=left,
                right_spec=right,
                left_book=_book_from_dict(row["left_book"]),
                right_book=_book_from_dict(row["right_book"]),
                per_size=tuple(row["per_size"]),
                capacity={
                    direction: CapacityResult(
                        max_full_fill_usd=Decimal(
                            str(detail["max_full_fill_usd"])
                        ),
                        lower_bound_only=bool(detail["lower_bound_only"]),
                        first_failed_size_usd=(
                            Decimal(str(detail["first_failed_size_usd"]))
                            if detail.get("first_failed_size_usd") is not None
                            else None
                        ),
                    )
                    for direction, detail in row["capacity"].items()
                },
            )
        )
    return ExecutionSnapshot(
        schema=payload["schema"],
        observed_at=payload["observed_at"],
        scanned_at=payload["scanned_at"],
        read_only=payload["read_only"],
        execution_client_present=payload["execution_client_present"],
        sizes_usd=sizes,
        pairs=tuple(pairs),
        request_errors=tuple(
            (row["selector"], row["reason_code"]) for row in payload["request_errors"]
        ),
        boundaries=tuple(payload["boundaries"]),
        refresh_mode=payload.get("refresh_mode", "static_file"),
        capture_span_ms=payload.get("capture_span_ms"),
    )


def _spec_from_dict(payload: dict) -> MarketSpec:
    identity = MarketIdentity(**payload["identity"])
    return MarketSpec(
        identity=identity,
        venue=payload["venue"],
        taker_fee_bps=_decimal(payload["taker_fee_bps"]),
        maker_fee_bps=_decimal(payload["maker_fee_bps"]),
        size_decimals=payload["size_decimals"],
        min_base_amount=Decimal(str(payload["min_base_amount"])),
        min_quote_amount=Decimal(str(payload["min_quote_amount"])),
        multiplier=Decimal(str(payload["multiplier"])),
        price_decimals=payload["price_decimals"],
        max_leverage=_decimal(payload.get("max_leverage")),
        margin_evidence=payload.get("margin_evidence", "unknown"),
    )


def _book_from_dict(payload: dict) -> L2Book:
    return L2Book(
        bids=tuple(
            L2Level(Decimal(str(level["price"])), Decimal(str(level["size"])))
            for level in payload["bids"]
        ),
        asks=tuple(
            L2Level(Decimal(str(level["price"])), Decimal(str(level["size"])))
            for level in payload["asks"]
        ),
        source_time_ms=payload.get("source_time_ms"),
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    args.sizes = tuple(Decimal(str(size)) for size in args.sizes.split(","))
    return run_execution_scan(args)


if __name__ == "__main__":
    raise SystemExit(main())
