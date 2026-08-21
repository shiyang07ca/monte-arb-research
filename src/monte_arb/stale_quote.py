"""Stale-quote detection for cross-venue candidate snapshots.

Automates the "stale quote" trap found in the BOT case study: a wide
top-of-book spread plus a large cross-venue mid divergence means the quote
structure itself is untrustworthy, even when depth looks real.

Three signals, each mapped to a data-quality code:

- STALE_HYPERLIQUID_SOURCE: Hyperliquid quote carries a source timestamp
  older than STALE_SOURCE_MAX_AGE_MS at snapshot time.
- WIDE_LIGHTER_SPREAD: Lighter top-of-book spread wider than
  WIDE_SPREAD_MAX_BPS. Lighter quotes have no source timestamp, so spread
  structure is the only age proxy available.
- CROSS_VENUE_DIVERGENCE: Lighter mid vs Hyperliquid mid diverge by more
  than CROSS_VENUE_MAX_DIVERGENCE_BPS. Two venues tracking the same
  underlying should not drift far apart in a snapshot.

Thresholds are explicit constants so the detector stays auditable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:  # pragma: no cover - import-time only
    from .candidate_workbench import BookQuote, SnapshotItem

STALE_SOURCE_MAX_AGE_MS = 60_000  # 60 s
WIDE_SPREAD_MAX_BPS = 100.0  # 1%
CROSS_VENUE_MAX_DIVERGENCE_BPS = 30.0  # 0.3% (BOT case: ~40 bps flagged)

_STALE = "STALE_HYPERLIQUID_SOURCE"
_WIDE = "WIDE_LIGHTER_SPREAD"
_DIVERGE = "CROSS_VENUE_DIVERGENCE"


def _to_decimal(value: Optional[str]) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _bps(price: Decimal, reference: Decimal) -> float:
    if not reference or not price:
        return 0.0
    return float((price - reference) / reference * 10_000)


def _spread_bps(quote: BookQuote) -> Optional[float]:
    bid = _to_decimal(quote.best_bid)
    ask = _to_decimal(quote.best_ask)
    if not bid or not ask or bid <= 0:
        return None
    return _bps(ask, bid)


def _mid(quote: BookQuote) -> Optional[Decimal]:
    bid = _to_decimal(quote.best_bid)
    ask = _to_decimal(quote.best_ask)
    if not bid or not ask:
        return None
    return (bid + ask) / Decimal(2)


def detect_stale_quote_codes(
    left: SnapshotItem,
    right: SnapshotItem,
    *,
    observed_at: Optional[datetime] = None,
) -> Tuple[str, ...]:
    """Return stale-quote data-quality codes for a candidate pair.

    left is the Lighter item, right is the Hyperliquid item. Codes are only
    emitted when the evidence supports them; a missing timestamp or an
    unusable price never fabricates a signal.
    """
    codes: list[str] = []
    left_quote = left.quote
    right_quote = right.quote
    if left_quote is None or right_quote is None:
        return ()

    # Hyperliquid source age.
    if right_quote.source_time_ms is not None:
        now_ms = (
            int(observed_at.timestamp() * 1000) if observed_at is not None else None
        )
        if (
            now_ms is not None
            and now_ms - right_quote.source_time_ms > STALE_SOURCE_MAX_AGE_MS
        ):
            codes.append(_STALE)

    # Lighter spread structure (no source timestamp -> spread is the age proxy).
    left_spread = _spread_bps(left_quote)
    if left_spread is not None and left_spread > WIDE_SPREAD_MAX_BPS:
        codes.append(_WIDE)

    # Cross-venue mid divergence.
    left_mid = _mid(left_quote)
    right_mid = _mid(right_quote)
    if left_mid and right_mid and left_mid > 0 and right_mid > 0:
        divergence = abs(_bps(left_mid, right_mid))
        if divergence > CROSS_VENUE_MAX_DIVERGENCE_BPS:
            codes.append(_DIVERGE)

    return tuple(sorted(set(codes)))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
