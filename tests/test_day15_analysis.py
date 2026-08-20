from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from monte_arb.day15_analysis import (
    MarketEvents,
    analyze_hour_history,
    build_baseline,
    detect_anomalies,
    load_session_events,
)


def _market_events(
    spreads_bps: list[float],
    start_ns: int = 1_000_000_000_000,
    step_ns: int = 1_000_000_000,
) -> MarketEvents:
    events = MarketEvents(market="WTI", venue="lighter")
    events.recv_ns = [start_ns + i * step_ns for i in range(len(spreads_bps))]
    events.mid = [84.0 + i * 0.001 for i in range(len(spreads_bps))]
    events.spread_bps = spreads_bps
    events.depth_top1 = [5.0] * len(spreads_bps)
    events.depth_top5 = [20.0] * len(spreads_bps)
    events.n_levels_bids = [10] * len(spreads_bps)
    events.n_levels_asks = [10] * len(spreads_bps)
    return events


class TestBaseline(unittest.TestCase):
    def test_median_and_mad_of_calm_series(self) -> None:
        # 120 seconds of calm quotes at 1 bps plus two outliers.
        spreads = [1.0] * 120
        spreads[30] = 50.0
        spreads[90] = 40.0
        events = _market_events(spreads)
        baseline = build_baseline(events)
        self.assertEqual(baseline.n_events, 120)
        self.assertAlmostEqual(baseline.spread_median_bps, 1.0, places=6)
        self.assertAlmostEqual(baseline.spread_mad_bps, 0.0, places=6)
        self.assertAlmostEqual(baseline.events_per_10s_median, 10.0, places=6)
        self.assertEqual(baseline.span_s, 119.0)

    def test_interarrival_and_silent_gap(self) -> None:
        events = _market_events([1.0] * 10, step_ns=60_000_000_000)  # 60 s apart
        baseline = build_baseline(events, silent_threshold_s=30.0)
        self.assertEqual(baseline.silent_gap_count, 9)
        self.assertAlmostEqual(baseline.silent_gap_total_s, 9 * 60.0, places=3)

    def test_empty_events(self) -> None:
        baseline = build_baseline(MarketEvents(market="X", venue="lighter"))
        self.assertEqual(baseline.n_events, 0)


class TestAnomalyDetection(unittest.TestCase):
    def test_transient_spike(self) -> None:
        spreads = [1.0] * 300
        for i in range(60, 65):  # 5 s wide spike at 40 bps
            spreads[i] = 40.0
        events = _market_events(spreads)
        baseline = build_baseline(events)
        windows = detect_anomalies(events, baseline, k=6.0, min_duration_s=3.0)
        self.assertEqual(len(windows), 1)
        window = windows[0]
        self.assertEqual(window.classification, "transient")
        self.assertAlmostEqual(window.peak, 40.0, places=6)
        self.assertGreater(window.ratio, 1.0)

    def test_repeating_spikes_are_marked_repeating(self) -> None:
        spreads = [1.0] * 300
        for start in (60, 120, 180):
            for i in range(start, start + 4):
                spreads[i] = 35.0
        events = _market_events(spreads)
        baseline = build_baseline(events)
        windows = detect_anomalies(events, baseline, k=6.0)
        self.assertEqual(len(windows), 3)
        self.assertTrue(all(w.classification == "repeating" for w in windows))

    def test_same_hour_repeats_marked_structural(self) -> None:
        # Four spike groups: two in UTC hour 0 and two in UTC hour 2. The
        # recurrence is tied to time-of-day buckets, not one short span.
        spreads = [1.0] * 400
        for start in (100, 110, 320, 330):
            for i in range(start, start + 4):
                spreads[i] = 30.0
        events = _market_events(spreads, step_ns=1_000_000_000)
        # Timeline (nanoseconds): seconds 0..299 (hour 0), then a jump to hour 2.
        events.recv_ns = [
            i * 1_000_000_000 for i in range(300)
        ] + [
            (7200 + i) * 1_000_000_000 for i in range(300, 400)
        ]
        baseline = build_baseline(events)
        windows = detect_anomalies(events, baseline, k=6.0)
        self.assertEqual(len(windows), 4)
        self.assertTrue(all(w.classification == "structural" for w in windows))
        self.assertEqual({w.hour_utc for w in windows}, {0, 2})

    def test_long_elevation_persistent(self) -> None:
        # Calm majority (600 events) with one 150-event elevation: the market's
        # own baseline stays at the calm level, and the elevation is persistent.
        spreads = [1.0] * 400 + [30.0] * 150 + [1.0] * 200
        events = _market_events(spreads)
        baseline = build_baseline(events)
        windows = detect_anomalies(events, baseline, k=6.0, min_duration_s=3.0)
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0].classification, "persistent")
        self.assertGreater(windows[0].duration_s, 120.0)

    def test_run_split_by_feed_gap(self) -> None:
        # Two 4-second spikes separated by a 60 s feed gap must not merge into
        # one long anomaly: a silent feed must not stitch events together.
        spreads = [1.0] * 120
        for i in range(40, 44):
            spreads[i] = 40.0
        for i in range(100, 104):
            spreads[i] = 42.0
        events = _market_events(spreads, step_ns=1_000_000_000)
        # Inject a 60 s gap: the whole tail after index 99 shifts later.
        base = events.recv_ns[99] + 60_000_000_000
        for index in range(100, 120):
            events.recv_ns[index] = base + (index - 100) * 1_000_000_000
        baseline = build_baseline(events)
        windows = detect_anomalies(events, baseline, k=6.0, min_duration_s=3.0)
        self.assertEqual(len(windows), 2)


class TestSessionLoading(unittest.TestCase):
    def test_load_session_events_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session_dir = Path(tmp) / "session"
            session_dir.mkdir()
            records = [
                {
                    "schema": "day15-continuous-events-v1",
                    "session": "s",
                    "recv_ns": 1_000_000_000_000 + i * 1_000_000_000,
                    "venue": "hyperliquid",
                    "kind": "book",
                    "market": "xyz:CL",
                    "payload": {
                        "ts_ms": 1787000000000 + i,
                        "bids": [["84.00", "2.0"]],
                        "asks": [["84.02", "3.0"]],
                    },
                }
                for i in range(5)
            ]
            with gzip.open(session_dir / "events_hyperliquid.jsonl.gz", "wt", encoding="utf-8") as stream:
                for record in records:
                    stream.write(json.dumps(record, separators=(",", ":")) + "\n")
            per_market = load_session_events(session_dir)
            self.assertIn("xyz:CL", per_market)
            events = per_market["xyz:CL"]
            self.assertEqual(events.n, 5)
            self.assertAlmostEqual(events.spread_bps[0], (84.02 - 84.00) / 84.01 * 10_000, places=3)

    def test_crossed_book_row_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session_dir = Path(tmp) / "session"
            session_dir.mkdir()
            record = {
                "schema": "day15-continuous-events-v1",
                "session": "s",
                "recv_ns": 1_000_000_000_000,
                "venue": "lighter",
                "kind": "book",
                "market": "145",
                "payload": {"bids": [["85.00", "1.0"]], "asks": [["84.50", "1.0"]]},
            }
            with gzip.open(session_dir / "events_lighter.jsonl.gz", "wt", encoding="utf-8") as stream:
                stream.write(json.dumps(record, separators=(",", ":")) + "\n")
            per_market = load_session_events(session_dir)
            self.assertNotIn("145", per_market)  # crossed book has no usable mid


class TestHourHistory(unittest.TestCase):
    def test_hour_profile_buckets_and_structural_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.jsonl"
            rows = []
            # 10 quiet hours at volume 100, one active hour at volume 400 (repeated 8x).
            for hour in range(0, 10):
                for _ in range(4):
                    rows.append(
                        {
                            "timestamp_utc": f"2026-07-16T{hour:02d}:00:00+00:00",
                            "wti_close": 80.0 + hour,
                            "brentoil_close": 83.0 + hour,
                            "wti_volume_base": 100.0,
                        }
                    )
            for _ in range(8):
                rows.append(
                    {
                        "timestamp_utc": "2026-07-16T14:00:00+00:00",
                        "wti_close": 90.0,
                        "brentoil_close": 94.0,
                        "wti_volume_base": 400.0,
                    }
                )
            with open(path, "w", encoding="utf-8") as stream:
                for row in rows:
                    stream.write(json.dumps(row) + "\n")
            profiles = analyze_hour_history(path, structural_volume_ratio=1.5)
            by_hour = {profile.hour_utc: profile for profile in profiles}
            self.assertEqual(len(by_hour), 11)
            self.assertTrue(by_hour[14].structural)
            self.assertFalse(by_hour[0].structural)
            self.assertAlmostEqual(by_hour[14].spread_median_usd, 4.0, places=6)
            self.assertAlmostEqual(by_hour[0].move_median_bps, 3.0 / 80.0 * 10_000, places=1)


if __name__ == "__main__":
    unittest.main()
