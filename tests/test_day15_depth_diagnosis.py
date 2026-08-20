from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from monte_arb.day15_analysis import MarketEvents
from monte_arb.day15_depth_diagnosis import depth_structure, mid_alignment


def _market(market: str, venue: str, mids: list[float], levels: list[int]) -> MarketEvents:
    events = MarketEvents(market=market, venue=venue)
    events.recv_ns = [1_000_000_000_000 + i * 1_000_000_000 for i in range(len(mids))]
    events.mid = mids
    events.spread_bps = [1.0] * len(mids)
    events.depth_top1 = [10.0] * len(mids)
    events.depth_top5 = [40.0] * len(mids)
    events.n_levels_bids = levels
    events.n_levels_asks = levels
    return events


class TestDepthStructure(unittest.TestCase):
    def test_level_counts_and_depth_reported(self) -> None:
        events = _market("159", "lighter", [89.0] * 5, [18] * 5)
        rows = depth_structure({"159": events})
        self.assertEqual(rows[0]["market"], "159")
        self.assertEqual(rows[0]["median_levels_bid"], 18.0)
        self.assertEqual(rows[0]["median_depth_top1"], 10.0)
        self.assertEqual(rows[0]["median_depth_top5"], 40.0)

    def test_empty_market_skipped(self) -> None:
        rows = depth_structure({"X": MarketEvents(market="X", venue="lighter")})
        self.assertEqual(rows, [])


class TestMidAlignment(unittest.TestCase):
    def test_aligned_seconds_and_diff_bps(self) -> None:
        lighter = _market("159", "lighter", [89.10, 89.11, 89.12], [18] * 3)
        hyperliquid = _market("xyz:BRENTOIL", "hyperliquid", [89.00, 89.01, 89.02], [18] * 3)
        report = mid_alignment(lighter, hyperliquid)
        self.assertEqual(report["n_aligned_seconds"], 3)
        # lighter is consistently +0.10 USD → ~11.2 bps at 89
        self.assertAlmostEqual(report["diff_usd_median"], 0.10, places=4)
        self.assertAlmostEqual(report["diff_bps_median"], 0.10 / 89.01 * 10_000, places=1)

    def test_missing_side_yields_zero_aligned(self) -> None:
        lighter = _market("159", "lighter", [89.10], [18])
        empty = MarketEvents(market="xyz:BRENTOIL", venue="hyperliquid")
        report = mid_alignment(lighter, empty)
        self.assertEqual(report["n_aligned_seconds"], 0)


class TestReportRoundtrip(unittest.TestCase):
    def test_build_report_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session_dir = Path(tmp) / "s"
            session_dir.mkdir()
            # one usable book event for lighter 159
            record = {
                "schema": "day15-continuous-events-v1",
                "session": "s",
                "recv_ns": 1_000_000_000_000,
                "venue": "lighter",
                "kind": "book",
                "market": "159",
                "payload": {
                    "ts_ms": 1787000000000,
                    "bids": [["89.00", "2.0"]],
                    "asks": [["89.02", "3.0"]],
                },
            }
            with gzip.open(session_dir / "events_lighter.jsonl.gz", "wt", encoding="utf-8") as stream:
                stream.write(json.dumps(record, separators=(",", ":")) + "\n")
            from monte_arb.day15_depth_diagnosis import build_report

            report = build_report(session_dir)
            self.assertEqual(report["schema"], "day15-experiment-b-v1")
            self.assertGreaterEqual(len(report["depth_structure"]), 1)
            self.assertIn("mid_alignment", report)
            self.assertIn("feed_integrity", report)


if __name__ == "__main__":
    unittest.main()
