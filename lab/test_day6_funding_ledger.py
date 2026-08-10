#!/usr/bin/env python3
import unittest
from decimal import Decimal

from lab.day6_funding_ledger import (
    PAPER_TIMESTAMP,
    build_snapshot,
    funding_cash_flow,
    payer_receiver,
)


class FundingFormulaTests(unittest.TestCase):
    def test_positive_rate_long_pays(self) -> None:
        result = funding_cash_flow(
            1, Decimal("0.134"), Decimal("1"), Decimal("74.670"), Decimal("0.0004")
        )
        self.assertEqual(result, Decimal("-0.0040023120"))
        self.assertEqual(payer_receiver(Decimal("0.0004"), 1), "pay")

    def test_positive_rate_short_receives(self) -> None:
        result = funding_cash_flow(
            -1, Decimal("0.134"), Decimal("1"), Decimal("74.670"), Decimal("0.0004")
        )
        self.assertEqual(result, Decimal("0.0040023120"))
        self.assertEqual(payer_receiver(Decimal("0.0004"), -1), "receive")

    def test_negative_rate_reverses_direction(self) -> None:
        self.assertEqual(payer_receiver(Decimal("-0.0004"), 1), "receive")
        self.assertEqual(payer_receiver(Decimal("-0.0004"), -1), "pay")
        self.assertEqual(funding_cash_flow(1, Decimal("1"), Decimal("1"), Decimal("100"), Decimal("-0.001")), Decimal("0.100"))

    def test_invalid_position_sign_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            funding_cash_flow(0, Decimal("1"), Decimal("1"), Decimal("100"), Decimal("0.001"))


class SnapshotTests(unittest.TestCase):
    def test_snapshot_keeps_api_fields_and_unknown_boundaries(self) -> None:
        snapshot = build_snapshot()
        self.assertEqual(snapshot["paper_timestamp_utc"], "2026-08-03T00:00:00+00:00")
        self.assertEqual(snapshot["raw_funding_observations"]["WTI"]["api_rate"], "0.0004")
        self.assertEqual(
            snapshot["raw_funding_observations"]["WTI"]["api_value_cash_flow_status"],
            "unknown_unit_and_position_mapping",
        )
        self.assertEqual(len(snapshot["paper_ledger"]), 4)
        self.assertTrue(all(row["cash_flow_status"] == "paper_only_not_time_aligned" for row in snapshot["paper_ledger"]))
        self.assertEqual(PAPER_TIMESTAMP, 1785715200)


if __name__ == "__main__":
    unittest.main()
