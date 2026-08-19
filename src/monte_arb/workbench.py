"""Day14 workbench v0: read-only snapshot candidate scan.

Public seam: build_candidate_snapshot() from raw catalogs/books/funding,
plus the HTTP workbench handler. No execution client and no orders.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Optional, Sequence, Tuple

from .adapters import (
    LIGHTER_BASE_URL,
    PublicJsonClient,
    SourceRequestError,
    fetch_hyperliquid_book,
    fetch_hyperliquid_catalog,
    fetch_lighter_book,
    fetch_lighter_catalog,
)
from .market import CatalogMarket, MarketIdentity, classify_book
from .oracle_consistency import detect_funding_source_mismatch
from .stale_quote import detect_stale_quote_codes

WORKBENCH_VERSION = "day14-workbench-v0"
SCHEMA = "day14-candidate-snapshot-v1"
NO_CANDIDATES = "NO_CANDIDATES_THIS_SCAN"


@dataclass(frozen=True)
class BookQuote:
    """Top-of-book with local request/receive clocks and optional source time."""

    identity: MarketIdentity
    best_bid: str
    best_ask: str
    bid_size: str
    ask_size: str
    source_time_ms: Optional[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "bid_size": self.bid_size,
            "ask_size": self.ask_size,
            "source_time_ms": self.source_time_ms,
        }


@dataclass(frozen=True)
class FundingRate:
    venue: str
    symbol: str
    rate: str
    source_time_ms: Optional[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "venue": self.venue,
            "symbol": self.symbol,
            "rate": self.rate,
            "source_time_ms": self.source_time_ms,
        }


@dataclass(frozen=True)
class SnapshotItem:
    identity: MarketIdentity
    catalog_status: str
    book_status: str
    quote: Optional[BookQuote]
    funding: Optional[FundingRate]
    source_time_ms: Optional[int]
    receive_skew_ms: float = 0.0
    reason_codes: Tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "catalog_status": self.catalog_status,
            "book_status": self.book_status,
            "quote": self.quote.to_dict() if self.quote else None,
            "funding": self.funding.to_dict() if self.funding else None,
            "source_time_ms": self.source_time_ms,
            "receive_skew_ms": self.receive_skew_ms,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class Candidate:
    pair_name: str
    left: SnapshotItem
    right: SnapshotItem
    executable_spread_bps: float
    depth_mismatch: float
    funding_diff_bps: float
    funding_divergent: bool
    liquidity_asymmetry: bool
    reference_dislocation: bool
    data_quality_issues: Tuple[str, ...]
    reasons: Tuple[str, ...]
    trade_rank: float
    research_rank: float
    direction: str
    evidence: Tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_name": self.pair_name,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "executable_spread_bps": self.executable_spread_bps,
            "depth_mismatch": self.depth_mismatch,
            "funding_diff_bps": self.funding_diff_bps,
            "funding_divergent": self.funding_divergent,
            "liquidity_asymmetry": self.liquidity_asymmetry,
            "reference_dislocation": self.reference_dislocation,
            "data_quality_issues": list(self.data_quality_issues),
            "reasons": list(self.reasons),
            "trade_rank": self.trade_rank,
            "research_rank": self.research_rank,
            "direction": self.direction,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class CandidateSnapshot:
    schema: str
    observed_at: str
    scanned_at: str
    read_only: bool
    execution_client_present: bool
    markets: Tuple[SnapshotItem, ...]
    candidates: Tuple[Candidate, ...]
    request_errors: Tuple[Tuple[str, str], ...] = ()
    boundaries: Tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "observed_at": self.observed_at,
            "scanned_at": self.scanned_at,
            "read_only": self.read_only,
            "execution_client_present": self.execution_client_present,
            "markets": [item.to_dict() for item in self.markets],
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "request_errors": [
                {"selector": selector, "reason_code": reason_code}
                for selector, reason_code in self.request_errors
            ],
            "boundaries": list(self.boundaries),
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _decimal(value: Any) -> Optional[Decimal]:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _top_quote(
    identity: MarketIdentity,
    raw_book: Mapping[str, Any],
) -> BookQuote:
    if identity.venue == "hyperliquid":
        if raw_book.get("coin") != identity.symbol:
            raise ValueError(f"{identity.selector}: coin mismatch")
        levels = raw_book.get("levels")
        if not isinstance(levels, list) or len(levels) != 2:
            raise ValueError(f"{identity.selector}: levels must have two sides")
        bids, asks = levels
        bid = bids[0] if bids else None
        ask = asks[0] if asks else None
        if bid is None or ask is None:
            raise ValueError(f"{identity.selector}: one-sided book")
        return BookQuote(
            identity=identity,
            best_bid=str(bid.get("px")),
            best_ask=str(ask.get("px")),
            bid_size=str(bid.get("sz")),
            ask_size=str(ask.get("sz")),
            source_time_ms=raw_book.get("time"),
        )
    if identity.venue == "lighter":
        if raw_book.get("code") != 200:
            raise ValueError(f"{identity.selector}: Lighter code != 200")
        bids = raw_book.get("bids")
        asks = raw_book.get("asks")
        bid = bids[0] if bids else None
        ask = asks[0] if asks else None
        if bid is None or ask is None:
            raise ValueError(f"{identity.selector}: one-sided book")
        return BookQuote(
            identity=identity,
            best_bid=str(bid.get("price")),
            best_ask=str(ask.get("price")),
            bid_size=str(bid.get("remaining_base_amount")),
            ask_size=str(ask.get("remaining_base_amount")),
            source_time_ms=None,
        )
    raise ValueError(f"unsupported venue: {identity.venue}")


def _bps(left: Decimal, right: Decimal) -> float:
    reference = (left + right) / Decimal(2)
    if reference <= 0:
        return 0.0
    return float(((right - left) / reference) * Decimal(10_000))


def _asymmetry(left: Decimal, right: Decimal) -> float:
    total = left + right
    if total <= 0:
        return 1.0
    return float(abs(left - right) / total)


def _candidate_features(
    left: SnapshotItem, right: SnapshotItem
) -> Tuple[float, float, float, bool, bool, bool]:
    left_quote = left.quote
    right_quote = right.quote
    if left_quote is None or right_quote is None:
        return (0.0, 1.0, 0.0, False, False, False)
    left_bid = _decimal(left_quote.best_bid)
    left_ask = _decimal(left_quote.best_ask)
    right_bid = _decimal(right_quote.best_bid)
    right_ask = _decimal(right_quote.best_ask)
    if not all((left_bid, left_ask, right_bid, right_ask)):
        return (0.0, 1.0, 0.0, False, False, False)
    # Two executable directions:
    #  buy Lighter ask / sell Hyperliquid bid  -> bid_right_ask_left  (positive if right bid > left ask)
    #  buy Hyperliquid ask / sell Lighter bid  -> bid_left_ask_right  (positive if left bid > right ask)
    spread_buy_left = _bps(left_ask, right_bid)
    spread_buy_right = _bps(right_ask, left_bid)
    spread = max(spread_buy_left, spread_buy_right)
    left_bid_size = _decimal(left_quote.bid_size) or Decimal(0)
    right_ask_size = _decimal(right_quote.ask_size) or Decimal(0)
    depth_mismatch = _asymmetry(left_bid_size, right_ask_size)
    left_funding = _decimal(left.funding.rate) if left.funding else None
    right_funding = _decimal(right.funding.rate) if right.funding else None
    funding_diff = 0.0
    funding_divergent = False
    if left_funding is not None and right_funding is not None:
        funding_diff = _bps(left_funding, right_funding)
        funding_divergent = abs(funding_diff) >= 10.0
    liquidity_asymmetry = depth_mismatch >= 0.25
    reference_dislocation = False
    return (
        spread,
        depth_mismatch,
        funding_diff,
        funding_divergent,
        liquidity_asymmetry,
        reference_dislocation,
    )


def _discover_pairs(
    lighter: Sequence[CatalogMarket], hyperliquid: Sequence[CatalogMarket]
) -> Tuple[Tuple[CatalogMarket, CatalogMarket, str, str, str], ...]:
    lighter_by_symbol: dict[str, CatalogMarket] = {}
    for market in lighter:
        symbol = market.identity.symbol
        if symbol in lighter_by_symbol:
            raise ValueError(f"duplicate Lighter symbol {symbol!r}")
        lighter_by_symbol[symbol] = market
    pairs = []
    seen = set()
    hl_sorted = sorted(hyperliquid, key=lambda market: market.identity.symbol)
    for hl_market in hl_sorted:
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
        pairs.append((candidate, hl_market, pair_name, base, hl_symbol))
    return tuple(pairs)


def _build_items(
    catalogs: Mapping[str, Sequence[CatalogMarket]],
    books: Mapping[MarketIdentity, Mapping[str, Any]],
) -> Tuple[SnapshotItem, ...]:
    items = []
    for venue, venue_catalogs in catalogs.items():
        for market in venue_catalogs:
            identity = market.identity
            raw_book = books.get(identity)
            quote = None
            book_status = "not_inspected"
            reason_codes: list[str] = []
            if raw_book is not None:
                book_status, reason_codes = classify_book(raw_book, identity)
                if book_status == "two_sided":
                    try:
                        quote = _top_quote(identity, raw_book)
                    except ValueError:
                        book_status = "invalid"
                        reason_codes = ["BOOK_INVALID"]
            items.append(
                SnapshotItem(
                    identity=identity,
                    catalog_status=market.catalog_status,
                    book_status=book_status,
                    quote=quote,
                    funding=None,
                    source_time_ms=quote.source_time_ms if quote else None,
                    receive_skew_ms=0.0,
                    reason_codes=tuple(reason_codes),
                )
            )
    return tuple(items)


def _candidate_from_pair(
    pair: Tuple[CatalogMarket, CatalogMarket, str, str, str],
    left_item: SnapshotItem,
    right_item: SnapshotItem,
    *,
    observed_at: Optional[str] = None,
) -> Candidate:
    _, _, pair_name, _, _ = pair
    (
        spread,
        depth_mismatch,
        funding_diff,
        funding_divergent,
        liquidity_asymmetry,
        reference_dislocation,
    ) = _candidate_features(left_item, right_item)
    left_quote = left_item.quote
    right_quote = right_item.quote
    if left_quote is None or right_quote is None:
        raise ValueError("candidate requires both quotes")
    spread_buy_left = _bps(
        _decimal(left_quote.best_ask) or Decimal(0),
        _decimal(right_quote.best_bid) or Decimal(0),
    )
    spread_buy_right = _bps(
        _decimal(right_quote.best_ask) or Decimal(0),
        _decimal(left_quote.best_bid) or Decimal(0),
    )
    direction = (
        "bid_right_ask_left"
        if spread_buy_left >= spread_buy_right
        else "bid_left_ask_right"
    )
    issues: list[str] = []
    for item in (left_item, right_item):
        if item.quote is None or item.quote.source_time_ms is None:
            issues.append("SOURCE_TIME_NOT_COMPARABLE")
        if item.book_status != "two_sided":
            issues.append("BOOK_INCOMPLETE")
        if item.catalog_status != "active":
            issues.append("MARKET_NOT_ACTIVE")
    issues = sorted(set(issues))
    reasons = ["CROSS_VENUE_EXECUTABLE_SPREAD"]
    if funding_divergent:
        reasons.append("FUNDING_DIVERGENCE")
    if liquidity_asymmetry:
        reasons.append("LIQUIDITY_ASYMMETRY")
    if reference_dislocation:
        reasons.append("REFERENCE_DISLOCATION")
    if "BOOK_INCOMPLETE" in issues:
        reasons.append("DATA_QUALITY_ISSUE")
    stale_codes = detect_stale_quote_codes(
        left_item,
        right_item,
        observed_at=_parse_observed_at(observed_at),
    )
    issues.extend(stale_codes)
    issues = sorted(set(issues))
    trade_rank = max(0.0, 1000.0 - max(spread, 0.0) - depth_mismatch * 500.0)
    research_rank = 100.0
    if funding_divergent:
        research_rank += 40.0
    if reference_dislocation:
        research_rank += 30.0
    if "BOOK_INCOMPLETE" in issues:
        research_rank -= 40.0
    return Candidate(
        pair_name=pair_name,
        left=left_item,
        right=right_item,
        executable_spread_bps=spread,
        depth_mismatch=depth_mismatch,
        funding_diff_bps=funding_diff,
        funding_divergent=funding_divergent,
        liquidity_asymmetry=liquidity_asymmetry,
        reference_dislocation=reference_dislocation,
        data_quality_issues=tuple(issues),
        reasons=tuple(reasons),
        trade_rank=round(trade_rank, 4),
        research_rank=round(research_rank, 4),
        direction=direction,
        evidence=tuple(
            sorted(
                {
                    "lighter-order-books",
                    "hyperliquid-meta-contexts",
                    "lighter-order-book-orders",
                    "hyperliquid-l2-book",
                }
            )
        ),
    )


def _parse_observed_at(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def build_candidate_snapshot(
    lighter_catalog: Sequence[CatalogMarket],
    hyperliquid_catalog: Sequence[CatalogMarket],
    books: Mapping[MarketIdentity, Mapping[str, Any]],
    *,
    observed_at: Optional[str] = None,
    scanned_at: Optional[str] = None,
    request_errors: Sequence[Tuple[str, str]] = (),
) -> CandidateSnapshot:
    catalogs = {
        "lighter": tuple(lighter_catalog),
        "hyperliquid": tuple(hyperliquid_catalog),
    }
    items = _build_items(catalogs, books)
    by_identity = {item.identity: item for item in items}
    pairs = _discover_pairs(lighter_catalog, hyperliquid_catalog)
    candidates = []
    for pair in pairs:
        left_item = by_identity.get(pair[0].identity)
        right_item = by_identity.get(pair[1].identity)
        if left_item is None or right_item is None:
            continue
        if left_item.quote is None or right_item.quote is None:
            # A candidate needs both executable top-of-book quotes; a missing
            # book stops advancement instead of fabricating a spread.
            continue
        candidates.append(
            _candidate_from_pair(pair, left_item, right_item, observed_at=observed_at)
        )
    candidates.sort(key=lambda c: (-c.trade_rank, -c.research_rank, c.pair_name))
    candidates = tuple(candidates)
    boundaries = (
        "Top-of-book snapshots prove current executable observations only; "
        "they do not prove matching contract weights or oracle source state.",
        "No fees, funding cash, slippage, or spread PnL is calculated.",
        "Trading and research ranks are study priority, not trade signals.",
    )
    return CandidateSnapshot(
        schema=SCHEMA,
        observed_at=observed_at or _utc_now(),
        scanned_at=scanned_at or _utc_now(),
        read_only=True,
        execution_client_present=False,
        markets=tuple(items),
        candidates=tuple(candidates),
        request_errors=tuple(request_errors),
        boundaries=boundaries,
    )


def _write_json(path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def run_workbench_scan(args: argparse.Namespace) -> int:
    client = PublicJsonClient(timeout=args.timeout)
    lighter_catalog = fetch_lighter_catalog(client)
    hyperliquid_catalog = fetch_hyperliquid_catalog(client, "xyz")
    request_errors: list[Tuple[str, str]] = []
    books: dict[MarketIdentity, Mapping[str, Any]] = {}
    tokenlist: Mapping[str, Any] = {}
    funding_rates: Sequence[Mapping[str, Any]] = ()
    try:
        tokenlist = client.get("lighter-tokenlist", f"{LIGHTER_BASE_URL}/tokenlist")
        funding_rates = client.get(
            "lighter-funding-rates", f"{LIGHTER_BASE_URL}/funding-rates"
        )
    except SourceRequestError:
        pass
    # Lighter public endpoints are rate-limited (60 req/min unauth); fetching a
    # book for every market would exceed it. Only fetch books for markets that
    # participate in a possible symbol mapping, plus their Lighter counterpart.
    pair_participants: set[MarketIdentity] = set()
    lighter_by_symbol: dict[str, CatalogMarket] = {}
    for market in lighter_catalog:
        lighter_by_symbol[market.identity.symbol] = market
    for hl_market in hyperliquid_catalog:
        if not hl_market.identity.symbol.startswith("xyz:"):
            continue
        base = hl_market.identity.symbol.split(":", 1)[1]
        lighter_match = lighter_by_symbol.get(base)
        if lighter_match is not None:
            pair_participants.add(lighter_match.identity)
            pair_participants.add(hl_market.identity)
    for market in lighter_catalog + hyperliquid_catalog:
        if market.catalog_status != "active":
            continue
        if market.identity not in pair_participants:
            continue
        try:
            if market.identity.venue == "lighter":
                books[market.identity] = fetch_lighter_book(
                    client, market, limit=args.book_limit
                )
            else:
                books[market.identity] = fetch_hyperliquid_book(client, market)
        except SourceRequestError:
            request_errors.append((market.identity.selector, "REQUEST_FAILED"))
    observed_at = client.captures[-1].received_at if client.captures else _utc_now()
    funding_rows: Sequence[Mapping[str, Any]] = ()
    if isinstance(funding_rates, Mapping):
        rows = funding_rates.get("funding_rates")
        if isinstance(rows, list):
            funding_rows = rows
    oracle_issues = detect_funding_source_mismatch(tokenlist, funding_rows)
    snapshot = build_candidate_snapshot(
        lighter_catalog,
        hyperliquid_catalog,
        books,
        observed_at=observed_at,
        request_errors=tuple(request_errors),
    )
    snapshot_dict = snapshot.to_dict()
    snapshot_dict["oracle_consistency_issues"] = [
        {
            "symbol": issue[0],
            "asset_type": issue[1],
            "funding_exchange": issue[2],
            "funding_symbol": issue[3],
            "note": issue[4],
        }
        for issue in oracle_issues
    ]
    _write_json(args.output, snapshot_dict)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "market_count": len(snapshot.markets),
                "candidate_count": len(snapshot.candidates),
                "request_errors": list(snapshot.request_errors),
                "oracle_consistency_issues": [
                    {"symbol": i[0], "funding_exchange": i[2]} for i in oracle_issues
                ],
                "top_candidates": [
                    {
                        "pair_name": candidate.pair_name,
                        "spread_bps": candidate.executable_spread_bps,
                    }
                    for candidate in snapshot.candidates[:3]
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 2 if snapshot.request_errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m monte_arb.workbench",
        description="Read-only Day14 workbench snapshot scan.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="research/runs/day14-workbench-scan.json",
        help="output JSON path",
    )
    parser.add_argument("--book-limit", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    from pathlib import Path

    args.output = Path(args.output)
    return run_workbench_scan(args)


if __name__ == "__main__":
    raise SystemExit(main())
