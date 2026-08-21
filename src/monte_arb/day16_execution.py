"""Day16 execution and capacity engine over frozen L2 books.

Public seam: pure functions (walk_book, order_qty_for_notional, leg_execution,
pair_execution, capacity_usd) plus build_execution_snapshot() and the CLI scan
run_execution_scan(). No execution client and no orders.

Units and honesty rules
-----------------------
- Prices and quantities are Decimal; JSON output uses floats for display.
- Lighter taker/maker fee fields are treated as percent (0.05 -> 5 bps);
  account-level fee schedules are unknown. Hyperliquid HIP-3 meta exposes no
  fee fields, so fee_bps stays None (never silently zero).
- Unknown fee keeps total_cost_bps None; net_spread_bps excludes fees entirely.
- A missing book or a below-minimum order keeps orderable=False with a reason.
"""

from __future__ import annotations

import argparse
import json
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

SCHEMA = "day16-execution-snapshot-v1"
VERSION = "day16-execution-v1"


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
        return {"price": float(self.price), "size": float(self.size)}


@dataclass(frozen=True)
class L2Book:
    bids: Tuple[L2Level, ...]
    asks: Tuple[L2Level, ...]
    source_time_ms: Optional[int] = None

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

    @property
    def top_bid_size(self) -> Decimal:
        return self.bids[0].size if self.bids else Decimal(0)

    @property
    def top_ask_size(self) -> Decimal:
        return self.asks[0].size if self.asks else Decimal(0)


def l2book_from_raw(identity: MarketIdentity, raw: Mapping[str, Any]) -> L2Book:
    """Parse one official book response into a sorted L2Book (venue aware)."""
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
    bids = tuple(sorted(bids, key=lambda level: level.price, reverse=True))
    asks = tuple(sorted(asks, key=lambda level: level.price))
    return L2Book(bids, asks, source_time_ms=source_time_ms)


def _levels_from_pairs(pairs: Any) -> Tuple[L2Level, ...]:
    levels = []
    for price_value, size_value in pairs:
        price = _decimal(price_value)
        size = _decimal(size_value)
        if price is not None and size is not None:
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "venue": self.venue,
            "taker_fee_bps": float(self.taker_fee_bps) if self.taker_fee_bps is not None else None,
            "maker_fee_bps": float(self.maker_fee_bps) if self.maker_fee_bps is not None else None,
            "size_decimals": self.size_decimals,
            "min_base_amount": float(self.min_base_amount),
            "min_quote_amount": float(self.min_quote_amount),
            "multiplier": float(self.multiplier),
            "price_decimals": self.price_decimals,
        }


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
        taker_fee = _decimal(row.get("taker_fee"))
        maker_fee = _decimal(row.get("maker_fee"))
        size_decimals = row.get("supported_size_decimals", row.get("size_decimals"))
        price_decimals = row.get("supported_price_decimals", row.get("price_decimals"))
        try:
            size_decimals = int(size_decimals)
            price_decimals = int(price_decimals)
        except (TypeError, ValueError):
            raise SourceShapeError(f"lighter orderBookDetails {symbol}: bad decimals")
        min_base = _decimal(row.get("min_base_amount")) or Decimal(0)
        min_quote = _decimal(row.get("min_quote_amount")) or Decimal(0)
        multiplier = _decimal(row.get("multiplier")) or Decimal(1)
        # Lighter fee fields are treated as percent: 0.05 -> 5 bps.
        specs[market_id] = MarketSpec(
            identity=MarketIdentity(
                "lighter", "perp", "default", symbol, str(market_id)
            ),
            venue="lighter",
            taker_fee_bps=taker_fee * Decimal(100) if taker_fee is not None else None,
            maker_fee_bps=maker_fee * Decimal(100) if maker_fee is not None else None,
            size_decimals=size_decimals,
            min_base_amount=min_base,
            min_quote_amount=min_quote,
            multiplier=multiplier,
            price_decimals=price_decimals,
        )
    return specs


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
    return normalize_lighter_details(response)


@dataclass(frozen=True)
class WalkResult:
    filled_qty: Decimal
    unfilled_qty: Decimal
    vwap: Optional[Decimal]
    worst_price: Optional[Decimal]
    levels_used: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "filled_qty": float(self.filled_qty),
            "unfilled_qty": float(self.unfilled_qty),
            "vwap": float(self.vwap) if self.vwap is not None else None,
            "worst_price": float(self.worst_price) if self.worst_price is not None else None,
            "levels_used": self.levels_used,
        }


def walk_book(
    levels: Sequence[L2Level],
    target_qty: Decimal,
    *,
    is_bid_side: bool,
) -> WalkResult:
    """Walk one side of a book; bids must already be descending, asks ascending."""
    remaining = target_qty
    total_notional = Decimal(0)
    filled = Decimal(0)
    worst: Optional[Decimal] = None
    used = 0
    for level in levels:
        if remaining <= 0:
            break
        take = min(remaining, level.size)
        if take > 0:
            total_notional += take * level.price
            filled += take
            remaining -= take
            worst = level.price
            used += 1
    if filled > 0:
        vwap = total_notional / filled
    else:
        vwap = None
    return WalkResult(
        filled_qty=filled,
        unfilled_qty=remaining,
        vwap=vwap,
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
    """Floor-to-grid order quantity, or 0 when not placeable."""
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
    """Floor-to-grid order quantity, or (0, reason) when not placeable.

    reason values: OK / MIN_BASE / MIN_QUOTE / BAD_PRICE
    """
    if price is None or price <= 0:
        return Decimal(0), "BAD_PRICE"
    step = Decimal(1).scaleb(-size_decimals)
    raw = notional_usd / (price * multiplier)
    qty = raw.quantize(step, rounding=ROUND_DOWN)
    if qty < min_base_amount:
        return Decimal(0), "MIN_BASE"
    quote_value = qty * price * multiplier
    if quote_value < min_quote_amount:
        return Decimal(0), "MIN_QUOTE"
    return qty, "OK"


@dataclass(frozen=True)
class LegResult:
    venue: str
    side: str
    orderable: bool
    orderable_reason: str
    target_qty: Decimal
    filled_qty: Decimal
    unfilled_qty: Decimal
    unfilled_notional_usd: Decimal
    vwap: Optional[Decimal]
    top_price: Optional[Decimal]
    slippage_bps: float
    fee_bps: Optional[float]
    total_bps: Optional[float]
    levels_used: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue": self.venue,
            "side": self.side,
            "orderable": self.orderable,
            "orderable_reason": self.orderable_reason,
            "target_qty": float(self.target_qty),
            "filled_qty": float(self.filled_qty),
            "unfilled_qty": float(self.unfilled_qty),
            "unfilled_notional_usd": float(self.unfilled_notional_usd),
            "vwap": float(self.vwap) if self.vwap is not None else None,
            "top_price": float(self.top_price) if self.top_price is not None else None,
            "slippage_bps": self.slippage_bps,
            "fee_bps": self.fee_bps,
            "total_bps": self.total_bps,
            "levels_used": self.levels_used,
        }


def leg_execution(
    spec: MarketSpec,
    l2book: L2Book,
    *,
    side: str,
    target_notional_usd: Decimal,
) -> LegResult:
    """One aggressive leg: buy at asks or sell at bids, target-size VWAP."""
    is_buy = side == "buy"
    levels = l2book.asks if is_buy else l2book.bids
    top_price = levels[0].price if levels else None
    if top_price is None:
        return LegResult(
            venue=spec.venue,
            side=side,
            orderable=False,
            orderable_reason="NO_TOP_OF_BOOK",
            target_qty=Decimal(0),
            filled_qty=Decimal(0),
            unfilled_qty=Decimal(0),
            unfilled_notional_usd=Decimal(0),
            vwap=None,
            top_price=None,
            slippage_bps=0.0,
            fee_bps=float(spec.taker_fee_bps) if spec.taker_fee_bps is not None else None,
            total_bps=None,
            levels_used=0,
        )
    qty, reason = _order_qty_with_reason(
        notional_usd=target_notional_usd,
        price=top_price,
        size_decimals=spec.size_decimals,
        min_base_amount=spec.min_base_amount,
        min_quote_amount=spec.min_quote_amount,
        multiplier=spec.multiplier,
    )
    if qty == 0:
        return LegResult(
            venue=spec.venue,
            side=side,
            orderable=False,
            orderable_reason=reason,
            target_qty=Decimal(0),
            filled_qty=Decimal(0),
            unfilled_qty=Decimal(0),
            unfilled_notional_usd=Decimal(0),
            vwap=None,
            top_price=top_price,
            slippage_bps=0.0,
            fee_bps=float(spec.taker_fee_bps) if spec.taker_fee_bps is not None else None,
            total_bps=None,
            levels_used=0,
        )
    walked = walk_book(levels, qty, is_bid_side=not is_buy)
    vwap = walked.vwap if walked.vwap is not None else top_price
    if is_buy:
        slippage = _bps(vwap - top_price, top_price)
    else:
        slippage = _bps(top_price - vwap, top_price)
    fee_bps = float(spec.taker_fee_bps) if spec.taker_fee_bps is not None else None
    total_bps = None if fee_bps is None else slippage + fee_bps
    return LegResult(
        venue=spec.venue,
        side=side,
        orderable=True,
        orderable_reason="OK",
        target_qty=qty,
        filled_qty=walked.filled_qty,
        unfilled_qty=walked.unfilled_qty,
        unfilled_notional_usd=walked.unfilled_qty * vwap,
        vwap=vwap,
        top_price=top_price,
        slippage_bps=round(slippage, 4),
        fee_bps=fee_bps,
        total_bps=round(total_bps, 4) if total_bps is not None else None,
        levels_used=walked.levels_used,
    )


@dataclass(frozen=True)
class PairResult:
    direction: str
    buy: LegResult
    sell: LegResult
    capture_bps: float
    slippage_cost_bps: float
    fee_cost_bps: Optional[float]
    net_spread_bps: float
    total_cost_bps: Optional[float]
    fill_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "buy": self.buy.to_dict(),
            "sell": self.sell.to_dict(),
            "capture_bps": self.capture_bps,
            "slippage_cost_bps": self.slippage_cost_bps,
            "fee_cost_bps": self.fee_cost_bps,
            "net_spread_bps": self.net_spread_bps,
            "total_cost_bps": self.total_cost_bps,
            "fill_pct": self.fill_pct,
        }


def _reference_price(
    left_book: L2Book, right_book: L2Book, left_spec: MarketSpec, right_spec: MarketSpec
) -> Optional[Decimal]:
    mids = []
    for book in (left_book, right_book):
        if book.best_bid is not None and book.best_ask is not None:
            mids.append((book.best_bid + book.best_ask) / Decimal(2))
    if not mids:
        return None
    return sum(mids, Decimal(0)) / Decimal(len(mids))


def pair_execution(
    left_spec: MarketSpec,
    left_book: L2Book,
    right_spec: MarketSpec,
    right_book: L2Book,
    *,
    direction: str,
    target_notional_usd: Decimal,
) -> PairResult:
    """Both legs of one direction at one target size."""
    if direction == "buy_left_sell_right":
        buy_leg = leg_execution(left_spec, left_book, side="buy", target_notional_usd=target_notional_usd)
        sell_leg = leg_execution(right_spec, right_book, side="sell", target_notional_usd=target_notional_usd)
        sell_price = sell_leg.vwap
        buy_price = buy_leg.vwap
    elif direction == "buy_right_sell_left":
        buy_leg = leg_execution(right_spec, right_book, side="buy", target_notional_usd=target_notional_usd)
        sell_leg = leg_execution(left_spec, left_book, side="sell", target_notional_usd=target_notional_usd)
        sell_price = sell_leg.vwap
        buy_price = buy_leg.vwap
    else:
        raise ValueError(f"unknown direction {direction!r}")
    reference = _reference_price(left_book, right_book, left_spec, right_spec)
    capture = 0.0
    if sell_price is not None and buy_price is not None and reference is not None:
        capture = _bps(sell_price - buy_price, reference)
    slippage_cost = round(buy_leg.slippage_bps + sell_leg.slippage_bps, 4)
    if buy_leg.fee_bps is not None and sell_leg.fee_bps is not None:
        fee_cost = round(buy_leg.fee_bps + sell_leg.fee_bps, 4)
        total_cost = round(slippage_cost + fee_cost, 4)
    else:
        fee_cost = None
        total_cost = None
    if buy_leg.target_qty > 0:
        buy_fill = float(buy_leg.filled_qty / buy_leg.target_qty)
    else:
        buy_fill = 0.0
    if sell_leg.target_qty > 0:
        sell_fill = float(sell_leg.filled_qty / sell_leg.target_qty)
    else:
        sell_fill = 0.0
    fill_pct = round(min(buy_fill, sell_fill), 6)
    return PairResult(
        direction=direction,
        buy=buy_leg,
        sell=sell_leg,
        capture_bps=round(capture, 4),
        slippage_cost_bps=slippage_cost,
        fee_cost_bps=fee_cost,
        net_spread_bps=round(capture - slippage_cost, 4),
        total_cost_bps=total_cost,
        fill_pct=fill_pct,
    )


def capacity_usd(
    left_spec: MarketSpec,
    left_book: L2Book,
    right_spec: MarketSpec,
    right_book: L2Book,
    *,
    direction: str,
    sizes: Sequence[Decimal],
) -> Decimal:
    """Largest size where both legs fully fill; 0 when none does.

    Sizes below the minimum orderable notional are skipped, not treated as a
    capacity limit: the curve only ends at the first orderable size that
    cannot fully fill (larger sizes can only consume more depth).
    """
    best = Decimal(0)
    started = False
    for size in sizes:
        result = pair_execution(
            left_spec,
            left_book,
            right_spec,
            right_book,
            direction=direction,
            target_notional_usd=size,
        )
        if not (result.buy.orderable and result.sell.orderable):
            if started:
                break
            continue
        started = True
        if result.buy.unfilled_qty == 0 and result.sell.unfilled_qty == 0:
            best = size
        else:
            break
    return best


@dataclass(frozen=True)
class ExecutionPair:
    pair_name: str
    left_spec: MarketSpec
    right_spec: MarketSpec
    left_book: L2Book
    right_book: L2Book
    per_size: Tuple[Mapping[str, Any], ...]
    capacity_usd: Mapping[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_name": self.pair_name,
            "left": self.left_spec.to_dict(),
            "right": self.right_spec.to_dict(),
            "left_book": self.left_book.to_dict(),
            "right_book": self.right_book.to_dict(),
            "per_size": list(self.per_size),
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "observed_at": self.observed_at,
            "scanned_at": self.scanned_at,
            "read_only": self.read_only,
            "execution_client_present": self.execution_client_present,
            "sizes_usd": [float(size) for size in self.sizes_usd],
            "pairs": [pair.to_dict() for pair in self.pairs],
            "request_errors": [
                {"selector": selector, "reason_code": reason_code}
                for selector, reason_code in self.request_errors
            ],
            "boundaries": list(self.boundaries),
        }


def _discover_pairs(
    lighter: Sequence[CatalogMarket],
    hyperliquid: Sequence[CatalogMarket],
) -> Tuple[Tuple[CatalogMarket, CatalogMarket, str], ...]:
    lighter_by_symbol: dict[str, CatalogMarket] = {}
    for market in lighter:
        lighter_by_symbol[market.identity.symbol] = market
    pairs = []
    seen = set()
    for hl_market in sorted(
        hyperliquid, key=lambda market: market.identity.symbol
    ):
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


DEFAULT_SIZES = (Decimal("10"), Decimal("25"), Decimal("50"), Decimal("100"), Decimal("250"), Decimal("500"), Decimal("1000"))

BOUNDARIES = (
    "Frozen L2 snapshots prove target-size executable prices at one moment only; "
    "they do not prove persistent depth or counterparty willingness after our order enters.",
    "Lighter taker/maker fees are read from the official market spec and treated as "
    "percent (0.05 -> 5 bps); account-level fee schedule is unknown. Hyperliquid HIP-3 "
    "meta exposes no fee fields, so those legs keep fee_bps=null (never zero).",
    "Net spread excludes unknown fees; total_cost_bps stays null until both legs have "
    "known fees. mark/oracle/mid never replace executable prices.",
    "Lighter public API is rate limited (60 req/min unauth); book fetches are paced and "
    "a failed market is recorded as REQUEST_FAILED instead of being guessed.",
    "Capacity is the largest tested size where both legs fully fill in this snapshot; "
    "it is not a promise of repeatable fills. Research ranking is not a trade signal.",
)


def build_execution_snapshot(
    left_specs: Sequence[MarketSpec],
    right_specs: Sequence[MarketSpec],
    books: Mapping[MarketIdentity, L2Book],
    *,
    sizes_usd: Sequence[Decimal] = DEFAULT_SIZES,
    observed_at: Optional[str] = None,
    scanned_at: Optional[str] = None,
    request_errors: Sequence[Tuple[str, str]] = (),
) -> ExecutionSnapshot:
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
        for size in sizes_usd:
            row: dict[str, Any] = {"size_usd": float(size)}
            for direction in ("buy_left_sell_right", "buy_right_sell_left"):
                result = pair_execution(
                    left_spec,
                    left_book,
                    right_spec,
                    right_book,
                    direction=direction,
                    target_notional_usd=size,
                )
                row[direction] = result.to_dict()
            per_size.append(row)
        capacity = {
            direction: float(
                capacity_usd(
                    left_spec,
                    left_book,
                    right_spec,
                    right_book,
                    direction=direction,
                    sizes=sizes_usd,
                )
            )
            for direction in ("buy_left_sell_right", "buy_right_sell_left")
        }
        pairs.append(
            ExecutionPair(
                pair_name=pair_name,
                left_spec=left_spec,
                right_spec=right_spec,
                left_book=left_book,
                right_book=right_book,
                per_size=tuple(per_size),
                capacity_usd=capacity,
            )
        )
    return ExecutionSnapshot(
        schema=SCHEMA,
        observed_at=observed_at or _utc_now(),
        scanned_at=scanned_at or _utc_now(),
        read_only=True,
        execution_client_present=False,
        sizes_usd=tuple(sizes_usd),
        pairs=tuple(pairs),
        request_errors=tuple(request_errors),
        boundaries=BOUNDARIES,
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


def run_execution_scan(args: argparse.Namespace) -> int:
    client = PublicJsonClient(timeout=args.timeout)
    lighter_catalog = fetch_lighter_catalog(client)
    hyperliquid_catalog = fetch_hyperliquid_catalog(client, "xyz")
    pairs = _discover_pairs(lighter_catalog, hyperliquid_catalog)
    lighter_participants = sorted({pair[0].identity.local_id for pair in pairs})
    details = fetch_lighter_details(client, [int(market_id) for market_id in lighter_participants])
    lighter_specs = list(details.values())
    right_specs = [
        MarketSpec(
            identity=market.identity,
            venue="hyperliquid",
            taker_fee_bps=None,
            maker_fee_bps=None,
            size_decimals=int(
                market.context.get("szDecimals", 2)
                if isinstance(market.context.get("szDecimals"), int)
                else 2
            ),
            min_base_amount=Decimal(0),
            min_quote_amount=Decimal(10),
            multiplier=Decimal(1),
            price_decimals=0,
        )
        for market in hyperliquid_catalog
        if market.catalog_status == "active" and market.identity.symbol.startswith("xyz:")
    ]
    # Keep only mapped right specs that have a Lighter counterpart.
    mapped_symbols = {pair[1].identity.symbol for pair in pairs}
    right_specs = [spec for spec in right_specs if spec.identity.symbol in mapped_symbols]

    books: dict[MarketIdentity, L2Book] = {}
    request_errors: list[Tuple[str, str]] = []
    selected_pairs = pairs[: args.max_pairs] if args.max_pairs else pairs
    selected_identities = {
        identity
        for pair in selected_pairs
        for identity in (pair[0].identity, pair[1].identity)
    }
    for pair in selected_pairs:
        left_market, right_market, _ = pair
        for market in (left_market, right_market):
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
    snapshot = build_execution_snapshot(
        lighter_specs,
        right_specs,
        books,
        sizes_usd=args.sizes,
        observed_at=observed_at,
        request_errors=tuple(request_errors),
    )
    payload = snapshot.to_dict()
    payload["scanned_pairs"] = [
        {"pair_name": pair_name, "left": left.identity.selector, "right": right.identity.selector}
        for left, right, pair_name in selected_pairs
    ]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "pair_count": len(selected_pairs),
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
        prog="python3 -m monte_arb.day16_execution",
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
                capacity_usd=dict(row["capacity_usd"]),
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
