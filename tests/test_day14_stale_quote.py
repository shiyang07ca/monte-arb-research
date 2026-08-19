"""Day14 stale-quote detection tests."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from monte_arb.market import MarketIdentity
from monte_arb.stale_quote import (
    STALE_SOURCE_MAX_AGE_MS,
    WIDE_SPREAD_MAX_BPS,
    detect_stale_quote_codes,
)
from monte_arb.workbench import BookQuote, SnapshotItem

WTI = MarketIdentity("lighter", "perp", "default", "WTI", "145")
CL = MarketIdentity("hyperliquid", "perp", "xyz", "xyz:CL", "110029")

NOW = datetime(2026, 8, 19, 8, 0, 0, tzinfo=timezone.utc)
NOW_MS = int(NOW.timestamp() * 1000)


def lighter_item(bid: str, ask: str) -> SnapshotItem:
    return SnapshotItem(
        identity=WTI,
        catalog_status="active",
        book_status="two_sided",
        quote=BookQuote(
            identity=WTI,
            best_bid=bid,
            best_ask=ask,
            bid_size="10",
            ask_size="10",
            source_time_ms=None,
        ),
        funding=None,
        source_time_ms=None,
    )


def hl_item(bid: str, ask: str, *, source_time_ms: int | None = NOW_MS) -> SnapshotItem:
    return SnapshotItem(
        identity=CL,
        catalog_status="active",
        book_status="two_sided",
        quote=BookQuote(
            identity=CL,
            best_bid=bid,
            best_ask=ask,
            bid_size="10",
            ask_size="10",
            source_time_ms=source_time_ms,
        ),
        funding=None,
        source_time_ms=source_time_ms,
    )


class StaleQuoteTests(unittest.TestCase):
    def test_healthy_pair_emits_no_codes(self) -> None:
        codes = detect_stale_quote_codes(
            lighter_item("100", "100.01"),  # 1 bps spread
            hl_item("100.01", "100.02"),  # fresh, aligned
            observed_at=NOW,
        )
        self.assertEqual(codes, ())

    def test_old_hyperliquid_source_is_flagged_stale(self) -> None:
        old = NOW_MS - STALE_SOURCE_MAX_AGE_MS - 1000
        codes = detect_stale_quote_codes(
            lighter_item("100", "100.01"),
            hl_item("100.01", "100.02", source_time_ms=old),
            observed_at=NOW,
        )
        self.assertIn("STALE_HYPERLIQUID_SOURCE", codes)

    def test_wide_lighter_spread_is_flagged(self) -> None:
        # BOT case: 118 bps Lighter spread.
        codes = detect_stale_quote_codes(
            lighter_item("28.573", "28.914"),
            hl_item("28.616", "28.641"),
            observed_at=NOW,
        )
        self.assertIn("WIDE_LIGHTER_SPREAD", codes)
        self.assertGreater((28.914 - 28.573) / 28.573 * 10_000, WIDE_SPREAD_MAX_BPS)

    def test_cross_venue_divergence_is_flagged(self) -> None:
        # Lighter mid ~28.74 vs HL mid ~28.63 -> ~0.4% divergence.
        codes = detect_stale_quote_codes(
            lighter_item("28.573", "28.914"),
            hl_item("28.616", "28.641"),
            observed_at=NOW,
        )
        self.assertIn("CROSS_VENUE_DIVERGENCE", codes)

    def test_small_divergence_not_flagged(self) -> None:
        codes = detect_stale_quote_codes(
            lighter_item("100", "100.01"),
            hl_item("100.02", "100.03"),
            observed_at=NOW,
        )
        self.assertNotIn("CROSS_VENUE_DIVERGENCE", codes)

    def test_missing_observed_at_skips_age_check_but_keeps_structure(self) -> None:
        codes = detect_stale_quote_codes(
            lighter_item("28.573", "28.914"),
            hl_item("28.616", "28.641"),
            observed_at=None,
        )
        self.assertNotIn("STALE_HYPERLIQUID_SOURCE", codes)
        self.assertIn("WIDE_LIGHTER_SPREAD", codes)

    def test_missing_quote_emits_nothing(self) -> None:
        item = SnapshotItem(
            identity=WTI,
            catalog_status="active",
            book_status="not_inspected",
            quote=None,
            funding=None,
            source_time_ms=None,
        )
        codes = detect_stale_quote_codes(item, item, observed_at=NOW)
        self.assertEqual(codes, ())

    def test_observed_at_iso_string_parses_in_workbench(self) -> None:
        from monte_arb.workbench import _parse_observed_at

        parsed = _parse_observed_at("2026-08-19T08:00:00.000000Z")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.tzinfo, timezone.utc)
        self.assertIsNone(_parse_observed_at("not-a-date"))


if __name__ == "__main__":
    unittest.main()
