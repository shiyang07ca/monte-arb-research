from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True, order=True)
class MarketIdentity:
    venue: str
    product_type: str
    venue_namespace: str
    symbol: str
    local_id: str

    @property
    def selector(self) -> str:
        return "/".join(
            (
                self.venue,
                self.product_type,
                self.venue_namespace,
                self.symbol,
                self.local_id,
            )
        )

    @classmethod
    def from_selector(cls, selector: str) -> "MarketIdentity":
        parts = selector.split("/", 4)
        if len(parts) != 5 or any(not part for part in parts):
            raise ValueError(
                "market selector must be venue/product_type/namespace/symbol/local_id"
            )
        return cls(*parts)

    def to_dict(self) -> dict[str, str]:
        return {
            "venue": self.venue,
            "product_type": self.product_type,
            "venue_namespace": self.venue_namespace,
            "symbol": self.symbol,
            "local_id": self.local_id,
        }


@dataclass(frozen=True)
class CatalogMarket:
    identity: MarketIdentity
    catalog_status: str
    context: Mapping[str, Any]
    index_in_meta: Optional[int] = None


@dataclass(frozen=True)
class RequestError:
    selector: str
    reason_code: str

    def to_dict(self) -> dict[str, str]:
        return {"selector": self.selector, "reason_code": self.reason_code}


@dataclass(frozen=True)
class ScannedMarket:
    identity: MarketIdentity
    catalog_status: str
    book_status: str
    scan_status: str
    reason_codes: Tuple[str, ...]
    index_in_meta: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "identity": self.identity.to_dict(),
            "catalog_status": self.catalog_status,
            "book_status": self.book_status,
            "scan_status": self.scan_status,
            "reason_codes": list(self.reason_codes),
        }
        if self.index_in_meta is not None:
            payload["index_in_meta"] = self.index_in_meta
        return payload


@dataclass(frozen=True)
class ScanReport:
    observed_at: str
    markets: Tuple[ScannedMarket, ...]
    request_errors: Tuple[RequestError, ...] = ()

    def decision_payload(self) -> dict[str, Any]:
        """Return deterministic fields, excluding the observation timestamp."""
        return {
            "markets": [market.to_dict() for market in self.markets],
            "request_errors": [error.to_dict() for error in self.request_errors],
        }

    def to_dict(self) -> dict[str, Any]:
        return {"observed_at": self.observed_at, **self.decision_payload()}

    def with_request_errors(self, errors: Iterable[RequestError]) -> "ScanReport":
        merged = tuple(
            sorted(
                (*self.request_errors, *tuple(errors)),
                key=lambda error: (error.selector, error.reason_code),
            )
        )
        return ScanReport(
            self.observed_at,
            self.markets,
            tuple(
                sorted(
                    set(merged),
                    key=lambda error: (error.selector, error.reason_code),
                )
            ),
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _positive_number(value: Any) -> bool:
    try:
        return Decimal(str(value)).is_finite() and Decimal(str(value)) > 0
    except (InvalidOperation, TypeError, ValueError):
        return False


def _side_is_valid(levels: Any, *, price_key: str, size_key: str) -> bool:
    if not isinstance(levels, list) or not levels:
        return False
    return all(
        isinstance(level, Mapping)
        and _positive_number(level.get(price_key))
        and _positive_number(level.get(size_key))
        for level in levels
    )


def classify_book(
    raw_book: Mapping[str, Any], identity: MarketIdentity
) -> Tuple[str, Tuple[str, ...]]:
    """Classify one raw public book without calculating liquidity or PnL."""
    if not isinstance(raw_book, Mapping):
        return "invalid", ("BOOK_INVALID",)

    if identity.venue == "hyperliquid":
        if raw_book.get("coin") != identity.symbol:
            return "invalid", ("IDENTITY_MISMATCH",)
        levels = raw_book.get("levels")
        if not isinstance(levels, list) or len(levels) != 2:
            return "invalid", ("BOOK_INVALID",)
        bids, asks = levels
        price_key, size_key = "px", "sz"
    elif identity.venue == "lighter":
        if raw_book.get("code") != 200:
            return "invalid", ("BOOK_INVALID",)
        bids, asks = raw_book.get("bids"), raw_book.get("asks")
        if not isinstance(bids, list) or not isinstance(asks, list):
            return "invalid", ("BOOK_INVALID",)
        price_key, size_key = "price", "remaining_base_amount"
    else:
        return "invalid", ("BOOK_INVALID",)

    if not bids and not asks:
        return "empty", ("BOOK_EMPTY",)
    if bids and not _side_is_valid(bids, price_key=price_key, size_key=size_key):
        return "invalid", ("BOOK_INVALID",)
    if asks and not _side_is_valid(asks, price_key=price_key, size_key=size_key):
        return "invalid", ("BOOK_INVALID",)
    if not bids or not asks:
        return "one_sided", ("BOOK_ONE_SIDED",)
    return "two_sided", ()


def scan_markets(
    catalog: Sequence[CatalogMarket],
    books: Mapping[MarketIdentity, Mapping[str, Any]],
    *,
    requested: Optional[Sequence[MarketIdentity]] = None,
    observed_at: Optional[str] = None,
) -> ScanReport:
    """Scan normalized markets through one deterministic public interface."""
    identities = [market.identity for market in catalog]
    counts = Counter(identities)
    local_id_counts = Counter(
        (
            identity.venue,
            identity.product_type,
            identity.venue_namespace,
            identity.local_id,
        )
        for identity in identities
    )
    symbol_counts = Counter(
        (
            identity.venue,
            identity.product_type,
            identity.venue_namespace,
            identity.symbol,
        )
        for identity in identities
    )
    known = set(identities)
    request_errors = []

    expected = tuple(requested) if requested is not None else tuple(books.keys())
    for identity in expected:
        if identity not in known:
            request_errors.append(RequestError(identity.selector, "UNKNOWN_SYMBOL"))

    for identity in books:
        if identity not in known and identity not in expected:
            request_errors.append(RequestError(identity.selector, "UNKNOWN_SYMBOL"))

    results = []
    for market in catalog:
        identity = market.identity
        if counts[identity] > 1:
            results.append(
                ScannedMarket(
                    identity,
                    market.catalog_status,
                    "invalid",
                    "invalid",
                    ("DUPLICATE_IDENTITY",),
                    market.index_in_meta,
                )
            )
            continue

        local_id_key = (
            identity.venue,
            identity.product_type,
            identity.venue_namespace,
            identity.local_id,
        )
        if local_id_counts[local_id_key] > 1:
            results.append(
                ScannedMarket(
                    identity,
                    market.catalog_status,
                    "invalid",
                    "invalid",
                    ("DUPLICATE_LOCAL_ID",),
                    market.index_in_meta,
                )
            )
            continue

        symbol_key = (
            identity.venue,
            identity.product_type,
            identity.venue_namespace,
            identity.symbol,
        )
        if symbol_counts[symbol_key] > 1:
            results.append(
                ScannedMarket(
                    identity,
                    market.catalog_status,
                    "invalid",
                    "invalid",
                    ("DUPLICATE_SYMBOL",),
                    market.index_in_meta,
                )
            )
            continue

        if market.catalog_status != "active":
            results.append(
                ScannedMarket(
                    identity,
                    market.catalog_status,
                    "not_inspected",
                    "stopped",
                    ("MARKET_NOT_ACTIVE",),
                    market.index_in_meta,
                )
            )
            continue

        raw_book = books.get(identity)
        if raw_book is None:
            results.append(
                ScannedMarket(
                    identity,
                    market.catalog_status,
                    "not_inspected",
                    "catalog_only",
                    ("BOOK_NOT_INSPECTED",),
                    market.index_in_meta,
                )
            )
            continue

        book_status, reason_codes = classify_book(raw_book, identity)
        scan_status = (
            "ready_for_market_mapping"
            if book_status == "two_sided"
            else ("invalid" if book_status == "invalid" else "stopped")
        )
        results.append(
            ScannedMarket(
                identity,
                market.catalog_status,
                book_status,
                scan_status,
                reason_codes,
                market.index_in_meta,
            )
        )

    return ScanReport(
        observed_at or utc_now(),
        tuple(results),
        tuple(
            sorted(
                set(request_errors),
                key=lambda error: (error.selector, error.reason_code),
            )
        ),
    )
