#!/usr/bin/env python3
"""Tests for the Day 9 parameter re-check: contract fields vs state fields.

The core lesson: contract parameters (leverage, precision, minimums, fees)
decide whether an order can be placed at all; market state (price, volume,
open interest) decides whether an opportunity might exist. A snapshot is a
point-in-time observation, not a fact sheet.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    from day9_parameter_recheck import (
        CONTRACT_FIELDS,
        DIFF_OUT,
        MARKETS,
        STATE_FIELDS,
        diff_parameters,
    )
except ModuleNotFoundError:
    from lab.day9_parameter_recheck import (
        CONTRACT_FIELDS,
        DIFF_OUT,
        MARKETS,
        STATE_FIELDS,
        diff_parameters,
    )


class Day9ParameterRecheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.diff = diff_parameters()
        cls.markets: dict = cls.diff["markets"]

    def test_diff_covers_both_markets(self) -> None:
        self.assertEqual(set(self.markets), set(MARKETS.values()))
        self.assertEqual(self.markets["WTI"]["market_id"], 145)
        self.assertEqual(self.markets["BRENTOIL"]["market_id"], 159)

    def test_contract_fields_are_stable_between_snapshots(self) -> None:
        # The contract-level definition (leverage, precision, minimums, fees)
        # must not have changed between the two snapshots. If this fails, the
        # venue changed its rules and every downstream calculation must re-check.
        for symbol in MARKETS.values():
            self.assertEqual(
                self.markets[symbol]["contract_changed"],
                [],
                f"{symbol} contract fields changed: {self.markets[symbol]['contract_changed']}",
            )

    def test_state_fields_did_change(self) -> None:
        # Market state must have moved (prices, volume, OI). A flat snapshot
        # would mean the diff is meaningless.
        for symbol in MARKETS.values():
            changed = {r["field"] for r in self.markets[symbol]["state_changed"]}
            self.assertTrue(
                {"mark_price", "index_price"}.issubset(changed),
                f"{symbol} state should include price moves, got {sorted(changed)}",
            )

    def test_every_changed_field_has_a_category(self) -> None:
        for symbol in MARKETS.values():
            for row in self.markets[symbol]["changed_fields"]:
                self.assertIn(row["category"], ("contract", "state", "other"))
                self.assertIn("old_value", row)
                self.assertIn("new_value", row)

    def test_old_and_new_snapshots_are_recorded(self) -> None:
        for symbol in MARKETS.values():
            old = Path(self.markets[symbol]["old_snapshot_file"])
            new = Path(self.markets[symbol]["new_snapshot_file"])
            self.assertTrue(old.exists(), f"old snapshot missing for {symbol}: {old}")
            self.assertTrue(new.exists(), f"new snapshot missing for {symbol}: {new}")
            self.assertNotEqual(old, new)

    def test_contract_and_state_sets_are_disjoint(self) -> None:
        self.assertEqual(CONTRACT_FIELDS & STATE_FIELDS, set())

    def test_diff_file_is_written_and_readable(self) -> None:
        self.assertTrue(DIFF_OUT.exists())
        data = json.loads(DIFF_OUT.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "day9-parameter-diff-v1")
        self.assertEqual(set(data["markets"]), set(MARKETS.values()))


if __name__ == "__main__":
    unittest.main()
