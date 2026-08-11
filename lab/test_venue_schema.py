#!/usr/bin/env python3
"""Tests for Day 8 venue schema normalization."""
from __future__ import annotations

import unittest
from pathlib import Path

try:
    from venue_schema import (
        SNAPSHOT_CSV,
        build_mapping,
        build_rows,
        binance_rows,
        hyperliquid_rows,
        lighter_rows,
        write_outputs,
    )
except ModuleNotFoundError:
    from lab.venue_schema import (
        SNAPSHOT_CSV,
        build_mapping,
        build_rows,
        binance_rows,
        hyperliquid_rows,
        lighter_rows,
        write_outputs,
    )


class VenueSchemaTests(unittest.TestCase):
    def test_rows_cover_all_three_venues(self) -> None:
        rows = build_rows()
        venues = {row["venue"] for row in rows}
        self.assertEqual(venues, {"lighter", "binance", "hyperliquid"})
        self.assertGreater(len(rows), 100)

    def test_lighter_rows_have_no_invented_timestamp(self) -> None:
        rows = [row for row in build_rows() if row["venue"] == "lighter"]
        self.assertEqual(len(rows), 80)  # 2 markets x 2 sides x 20 levels
        self.assertTrue(all(row["source_timestamp"] == "" for row in rows))
        self.assertTrue(all(row["timestamp_semantics"] == "missing_source_timestamp" for row in rows))
        self.assertTrue(all(row["size_semantics"] == "order_level_remaining" for row in rows))

    def test_binance_rows_use_event_time_and_aggregated_sizes(self) -> None:
        rows = [row for row in build_rows() if row["venue"] == "binance" and row["side"] != "funding"]
        self.assertEqual(len(rows), 40)
        self.assertTrue(all(row["timestamp_semantics"] == "event_time_E" for row in rows))
        self.assertTrue(all(row["size_semantics"] == "aggregated" for row in rows))

    def test_hyperliquid_rows_keep_level_count_in_size_semantics(self) -> None:
        rows = [row for row in build_rows() if row["venue"] == "hyperliquid" and row["side"] != "funding"]
        self.assertEqual(len(rows), 40)
        self.assertTrue(all(row["timestamp_semantics"] == "book_time" for row in rows))
        self.assertTrue(all(row["size_semantics"].startswith("aggregated_n=") for row in rows))

    def test_funding_rows_parse_rates_and_keep_timestamp_semantics(self) -> None:
        rows = [row for row in build_rows() if row["side"] == "funding"]
        venues = {row["venue"] for row in rows}
        self.assertEqual(venues, {"binance", "hyperliquid"})
        self.assertTrue(all(row["size"] != "" for row in rows))
        self.assertTrue(all(row["timestamp_semantics"] == "funding_time_ms" for row in rows))
        self.assertEqual(sum(row["venue"] == "binance" for row in rows), 5)
        self.assertEqual(sum(row["venue"] == "hyperliquid" for row in rows), 168)

    def test_unknowns_are_explicit_in_summary(self) -> None:
        rows = build_rows()
        summary = write_outputs(rows, build_mapping())
        self.assertGreaterEqual(len(summary["not_equivalent_fields"]), 5)
        self.assertIn("lighter orderBookOrders snapshot has no public timestamp field", summary["unknowns"])
        self.assertTrue(SNAPSHOT_CSV.exists())

    def test_mapping_has_at_least_five_not_equivalent_fields(self) -> None:
        mapping = build_mapping()
        not_equivalent = [item for item in mapping if item["equivalent"] == "not_equivalent"]
        self.assertGreaterEqual(len(not_equivalent), 5)


if __name__ == "__main__":
    unittest.main()
