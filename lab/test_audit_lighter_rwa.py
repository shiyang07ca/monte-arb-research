#!/usr/bin/env python3
"""Small, dependency-free tests for the read-only audit seams."""
from __future__ import annotations

import math
import unittest

try:
    from audit_lighter_rwa import (
        order_book_detail,
        paper_quantity_for_quote,
        validate_instrument_snapshot,
    )
except ModuleNotFoundError:  # Allows both repo-root and lab-directory execution.
    from lab.audit_lighter_rwa import (
        order_book_detail,
        paper_quantity_for_quote,
        validate_instrument_snapshot,
    )


class InstrumentSnapshotTests(unittest.TestCase):
    def test_current_market_ids_and_required_fields(self) -> None:
        self.assertEqual(order_book_detail("WTI")["market_id"], 145)
        self.assertEqual(order_book_detail("BRENTOIL")["market_id"], 159)
        self.assertEqual(validate_instrument_snapshot("WTI", 145), [])
        self.assertEqual(validate_instrument_snapshot("BRENTOIL", 159), [])

    def test_paper_quantity_respects_minimums_and_precision(self) -> None:
        for symbol in ("WTI", "BRENTOIL"):
            result = paper_quantity_for_quote(symbol, 10.0)
            detail = order_book_detail(symbol)
            step = 10 ** -int(detail["size_decimals"])
            self.assertGreaterEqual(
                result["actual_quote_notional"], result["minimum_quote_amount"]
            )
            self.assertGreaterEqual(
                result["base_quantity"], float(detail["min_base_amount"])
            )
            self.assertAlmostEqual(
                result["base_quantity"] / step,
                round(result["base_quantity"] / step),
            )

    def test_invalid_market_id_is_reported(self) -> None:
        self.assertTrue(validate_instrument_snapshot("WTI", 159))


class PureMathTests(unittest.TestCase):
    def test_quantity_rounding_is_upward(self) -> None:
        raw = 1.001
        step = 0.01
        rounded = math.ceil(raw / step - 1e-12) * step
        self.assertEqual(rounded, 1.01)


if __name__ == "__main__":
    unittest.main()