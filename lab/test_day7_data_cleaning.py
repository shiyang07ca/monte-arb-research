#!/usr/bin/env python3
"""Tests for the auditable Day 7 cleaning boundaries."""
from __future__ import annotations

import csv
import unittest
from pathlib import Path

try:
    from day7_data_cleaning import (
        CLEAN_CSV,
        JUMP_THRESHOLD,
        build_records,
        interval_flags,
        raw_field_flags,
        split_timestamps,
        write_outputs,
    )
except ModuleNotFoundError:
    from lab.day7_data_cleaning import (
        CLEAN_CSV,
        JUMP_THRESHOLD,
        build_records,
        interval_flags,
        raw_field_flags,
        split_timestamps,
        write_outputs,
    )


class Day7CleaningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records, cls.summary = build_records()

    def test_current_snapshot_keeps_union_and_marks_funding_only(self) -> None:
        self.assertEqual(len(self.records), 1500)
        self.assertEqual(self.summary["output"]["candle_and_funding_rows"], 1000)
        self.assertEqual(self.summary["output"]["funding_only_rows"], 500)
        self.assertEqual(self.summary["output"]["candle_only_rows"], 0)
        self.assertEqual(self.summary["output"]["combined_eligible_rows"], 1000)

    def test_no_interpolation_and_no_duplicate_in_current_snapshot(self) -> None:
        self.assertEqual(self.summary["per_market"]["WTI"]["candle_missing_interval_rows"], 0)
        self.assertEqual(self.summary["per_market"]["BRENTOIL"]["candle_missing_interval_rows"], 0)
        self.assertEqual(self.summary["per_market"]["WTI"]["duplicate_candle_timestamps"], 0)
        self.assertEqual(self.summary["per_market"]["BRENTOIL"]["duplicate_candle_timestamps"], 0)
        self.assertEqual(self.summary["per_market"]["WTI"]["duplicate_funding_timestamps"], 0)
        self.assertEqual(self.summary["per_market"]["BRENTOIL"]["duplicate_funding_timestamps"], 0)

    def test_jump_is_flagged_not_silently_removed(self) -> None:
        flagged = [row for row in self.records if row["close_jump_gt_5pct"] == "true"]
        self.assertGreaterEqual(len(flagged), 1)
        self.assertTrue(all(row["admission_status"] == "eligible_with_jump_flag" for row in flagged))
        self.assertTrue(all(row["combined_pair_eligible"] == "true" for row in flagged))
        self.assertEqual(JUMP_THRESHOLD, 0.05)

    def test_split_is_chronological_and_non_overlapping(self) -> None:
        split_map, summary = split_timestamps(range(750))
        self.assertEqual(summary["ranges"]["train"]["timestamps"], 450)
        self.assertEqual(summary["ranges"]["validation"]["timestamps"], 150)
        self.assertEqual(summary["ranges"]["test"]["timestamps"], 150)
        self.assertLess(max(k for k, v in split_map.items() if v == "train"), min(k for k, v in split_map.items() if v == "validation"))
        self.assertLess(max(k for k, v in split_map.items() if v == "validation"), min(k for k, v in split_map.items() if v == "test"))

    def test_flag_helpers_do_not_turn_missing_or_zero_into_silent_data(self) -> None:
        invalid, zero, fields = raw_field_flags({"t": 1, "o": "0", "h": "2", "l": "1", "c": "2", "v": "3", "V": "4"}, ("t", "o", "h", "l", "c", "v", "V"))
        self.assertFalse(invalid)
        self.assertTrue(zero)
        self.assertIn("o", fields)
        flags = interval_flags([0, 3 * 60 * 60 * 1000])
        self.assertEqual(flags[3 * 60 * 60 * 1000], (True, 2))

    def test_output_schema_can_be_written_and_reloaded(self) -> None:
        write_outputs(self.records, self.summary)
        with CLEAN_CSV.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), len(self.records))
        self.assertIn("combined_pair_eligible", rows[0])
        self.assertIn("source_candle_file", rows[0])


if __name__ == "__main__":
    unittest.main()
