"""Market self-baselines, anomaly windows, and session/history analysis.

The workbench stops treating a single snapshot as a finding. This module turns
append-only continuous events into:

- per-market self-baselines (spread, depth, update frequency, price deviation,
  silent gaps);
- anomaly windows (magnitude, duration, repeat count, session labels);
- hour-of-day structure from longer saved history (volume / close-move / spread
  profile by UTC hour).

Classification vocabulary (kept explicit, no hidden single score):
  transient   — one short excursion far from the market's own baseline;
  repeating   — the same kind of excursion recurs within the window;
  persistent  — a long elevation that never returns to baseline;
  structural  — an excursion that recurs at the same time-of-day bucket.
"""

from __future__ import annotations

import gzip
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

SCHEMA = "day15-analysis-v1"


# ---------------------------------------------------------------------------
# Event loading
# ---------------------------------------------------------------------------

def _read_gzip_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


@dataclass
class MarketEvents:
    market: str
    venue: str
    recv_ns: list[int] = field(default_factory=list)
    mid: list[float] = field(default_factory=list)
    spread_bps: list[float] = field(default_factory=list)
    depth_top1: list[float] = field(default_factory=list)
    depth_top5: list[float] = field(default_factory=list)
    n_levels_bids: list[int] = field(default_factory=list)
    n_levels_asks: list[int] = field(default_factory=list)
    trade_px: list[float] = field(default_factory=list)
    trade_sz: list[float] = field(default_factory=list)
    trade_ns: list[int] = field(default_factory=list)
    ctx: list[dict[str, Any]] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.recv_ns)


def load_session_events(session_dir: Path) -> dict[str, MarketEvents]:
    """Load events from a session directory into per-market series."""
    per_market: dict[str, MarketEvents] = {}

    def ensure(market: str, venue: str) -> MarketEvents:
        entry = per_market.get(market)
        if entry is None:
            entry = MarketEvents(market=market, venue=venue)
            per_market[market] = entry
        return entry

    for venue, filename in (
        ("hyperliquid", "events_hyperliquid.jsonl.gz"),
        ("lighter", "events_lighter.jsonl.gz"),
    ):
        path = session_dir / filename
        if not path.exists():
            continue
        for record in _read_gzip_jsonl(path):
            market = str(record.get("market", "?"))
            kind = record.get("kind")
            payload = record.get("payload")
            if not isinstance(payload, Mapping):
                continue
            recv_ns = int(record.get("recv_ns", 0))
            if kind == "book":
                bids = payload.get("bids") or []
                asks = payload.get("asks") or []
                if not bids or not asks:
                    continue
                try:
                    bid_px = float(bids[0][0])
                    ask_px = float(asks[0][0])
                    bid_sz = float(bids[0][1])
                    ask_sz = float(asks[0][1])
                except (TypeError, ValueError, IndexError):
                    continue
                if ask_px <= bid_px:
                    continue  # crossed/locked book has no usable mid
                entry = ensure(market, venue)
                mid = (bid_px + ask_px) / 2.0
                spread_bps = (ask_px - bid_px) / mid * 10_000 if mid > 0 else 0.0
                entry.recv_ns.append(recv_ns)
                entry.mid.append(mid)
                entry.spread_bps.append(spread_bps)
                entry.depth_top1.append(bid_sz + ask_sz)
                top5_bid = sum(float(b[1]) for b in bids[:5])
                top5_ask = sum(float(a[1]) for a in asks[:5])
                entry.depth_top5.append(top5_bid + top5_ask)
                entry.n_levels_bids.append(len(bids))
                entry.n_levels_asks.append(len(asks))
            elif kind == "trade":
                entry = ensure(market, venue)
                try:
                    entry.trade_px.append(float(payload["px"]))
                    entry.trade_sz.append(float(payload["sz"]))
                except (KeyError, TypeError, ValueError):
                    continue
                entry.trade_ns.append(recv_ns)
            elif kind == "ctx":
                ensure(market, venue).ctx.append(dict(payload))
    return per_market


def load_health_events(session_dir: Path) -> list[dict[str, Any]]:
    path = session_dir / "health.jsonl.gz"
    if not path.exists():
        return []
    return _read_gzip_jsonl(path)


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def _median(values: Sequence[float]) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    n = len(ordered)
    if n % 2 == 1:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0


def _mad(values: Sequence[float]) -> float:
    """Median absolute deviation, scaled to a sigma-like unit (1.4826)."""
    if not values:
        return float("nan")
    median = _median(values)
    deviations = [abs(v - median) for v in values]
    return 1.4826 * _median(deviations)


def _p95(values: Sequence[float]) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(math.ceil(0.95 * len(ordered)) - 1))
    return ordered[max(index, 0)]


def _fmt(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return round(value, 6)


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------

@dataclass
class MarketBaseline:
    market: str
    venue: str
    n_events: int = 0
    span_s: float = 0.0
    interarrival_median_s: float = 0.0
    interarrival_p95_s: float = 0.0
    spread_median_bps: float = 0.0
    spread_p95_bps: float = 0.0
    spread_mad_bps: float = 0.0
    depth_top1_median: float = 0.0
    depth_top5_median: float = 0.0
    levels_median: float = 0.0
    ret_10s_std_bps: float = 0.0
    events_per_10s_median: float = 0.0
    silent_gap_count: int = 0
    silent_gap_total_s: float = 0.0
    n_trades: int = 0
    trade_volume_base: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "venue": self.venue,
            "n_events": self.n_events,
            "span_s": _fmt(self.span_s),
            "interarrival_median_s": _fmt(self.interarrival_median_s),
            "interarrival_p95_s": _fmt(self.interarrival_p95_s),
            "spread_median_bps": _fmt(self.spread_median_bps),
            "spread_p95_bps": _fmt(self.spread_p95_bps),
            "spread_mad_bps": _fmt(self.spread_mad_bps),
            "depth_top1_median": _fmt(self.depth_top1_median),
            "depth_top5_median": _fmt(self.depth_top5_median),
            "levels_median": _fmt(self.levels_median),
            "ret_10s_std_bps": _fmt(self.ret_10s_std_bps),
            "events_per_10s_median": _fmt(self.events_per_10s_median),
            "silent_gap_count": self.silent_gap_count,
            "silent_gap_total_s": _fmt(self.silent_gap_total_s),
            "n_trades": self.n_trades,
            "trade_volume_base": _fmt(self.trade_volume_base),
        }


def build_baseline(
    events: MarketEvents, silent_threshold_s: float = 30.0
) -> MarketBaseline:
    baseline = MarketBaseline(market=events.market, venue=events.venue, n_events=events.n)
    if events.n == 0:
        return baseline
    first_ns = events.recv_ns[0]
    last_ns = events.recv_ns[-1]
    baseline.span_s = max((last_ns - first_ns) / 1e9, 1e-6)

    interarrivals = [
        (events.recv_ns[i] - events.recv_ns[i - 1]) / 1e9
        for i in range(1, events.n)
        if events.recv_ns[i] > events.recv_ns[i - 1]
    ]
    if interarrivals:
        baseline.interarrival_median_s = _median(interarrivals)
        baseline.interarrival_p95_s = _p95(interarrivals)
    baseline.spread_median_bps = _median(events.spread_bps)
    baseline.spread_p95_bps = _p95(events.spread_bps)
    baseline.spread_mad_bps = _mad(events.spread_bps)
    baseline.depth_top1_median = _median(events.depth_top1)
    baseline.depth_top5_median = _median(events.depth_top5)
    baseline.levels_median = _median(
        [b + a for b, a in zip(events.n_levels_bids, events.n_levels_asks)]
    )

    # 10-second log-return deviation of the mid path.
    buckets: dict[int, float] = {}
    for ns, mid in zip(events.recv_ns, events.mid):
        bucket = int(ns / 10e9)
        buckets[bucket] = mid  # last mid in bucket
    bucket_keys = sorted(buckets)
    returns_bps = []
    for previous, current in zip(bucket_keys, bucket_keys[1:]):
        if current - previous != 1 or buckets[previous] <= 0:
            continue
        returns_bps.append(
            math.log(buckets[current] / buckets[previous]) * 10_000
        )
    baseline.ret_10s_std_bps = (
        math.sqrt(
            sum(r * r for r in returns_bps) / len(returns_bps)
            - (sum(returns_bps) / len(returns_bps)) ** 2
        )
        if returns_bps
        else 0.0
    )

    per_10s: dict[int, int] = {}
    for ns in events.recv_ns:
        per_10s[int(ns / 10e9)] = per_10s.get(int(ns / 10e9), 0) + 1
    baseline.events_per_10s_median = _median(list(per_10s.values()))

    for gap_s in interarrivals:
        if gap_s > silent_threshold_s:
            baseline.silent_gap_count += 1
            baseline.silent_gap_total_s += gap_s

    baseline.n_trades = len(events.trade_px)
    baseline.trade_volume_base = sum(events.trade_sz)
    return baseline


# ---------------------------------------------------------------------------
# Anomaly windows
# ---------------------------------------------------------------------------

@dataclass
class AnomalyWindow:
    market: str
    venue: str
    feature: str
    start_ns: int
    end_ns: int
    duration_s: float
    peak: float
    threshold: float
    ratio: float
    mean: float
    n_events: int
    repeats: int
    classification: str
    hour_utc: int

    def to_dict(self) -> dict[str, Any]:
        start_utc = datetime.fromtimestamp(self.start_ns / 1e9, tz=timezone.utc)
        end_utc = datetime.fromtimestamp(self.end_ns / 1e9, tz=timezone.utc)
        return {
            "market": self.market,
            "venue": self.venue,
            "feature": self.feature,
            "start_utc": start_utc.isoformat().replace("+00:00", "Z"),
            "end_utc": end_utc.isoformat().replace("+00:00", "Z"),
            "duration_s": _fmt(self.duration_s),
            "peak": _fmt(self.peak),
            "threshold": _fmt(self.threshold),
            "ratio": _fmt(self.ratio),
            "mean": _fmt(self.mean),
            "n_events": self.n_events,
            "repeats": self.repeats,
            "classification": self.classification,
            "hour_utc": self.hour_utc,
        }


def detect_anomalies(
    events: MarketEvents,
    baseline: MarketBaseline,
    k: float = 6.0,
    min_duration_s: float = 3.0,
    max_run_gap_s: float = 5.0,
) -> list[AnomalyWindow]:
    """Find contiguous excursions of spread_bps above baseline median + k*MAD.

    Consecutive events further apart than ``max_run_gap_s`` split a run (a quiet
    feed must not stitch two separate events into one long anomaly).
    """
    if events.n < 10:
        return []
    # A zero-MAD (perfectly calm) series must not make the median itself
    # anomalous: the excursion threshold always sits above 1.5x the median.
    threshold = max(
        baseline.spread_median_bps + k * baseline.spread_mad_bps,
        baseline.spread_median_bps * 1.5,
    )
    if not math.isfinite(threshold) or threshold <= 0:
        return []
    runs: list[list[int]] = []
    current: list[int] = []
    for index in range(events.n):
        if events.spread_bps[index] >= threshold:
            # Out-of-order timestamps and feed gaps both split a run: a silent or
            # reordering feed must not stitch separate events into one anomaly.
            if current and (
                (events.recv_ns[index] - events.recv_ns[current[-1]]) / 1e9
                > max_run_gap_s
                or events.recv_ns[index] <= events.recv_ns[current[-1]]
            ):
                runs.append(current)
                current = []
            current.append(index)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)

    windows: list[AnomalyWindow] = []
    for run in runs:
        duration_s = (events.recv_ns[run[-1]] - events.recv_ns[run[0]]) / 1e9
        if duration_s < min_duration_s:
            continue
        values = [events.spread_bps[i] for i in run]
        peak = max(values)
        mean = sum(values) / len(values)
        start_ns = events.recv_ns[run[0]]
        end_ns = events.recv_ns[run[-1]]
        hour_utc = datetime.fromtimestamp(start_ns / 1e9, tz=timezone.utc).hour
        windows.append(
            AnomalyWindow(
                market=events.market,
                venue=events.venue,
                feature="spread_bps",
                start_ns=start_ns,
                end_ns=end_ns,
                duration_s=duration_s,
                peak=peak,
                threshold=threshold,
                ratio=peak / threshold if threshold else 0.0,
                mean=mean,
                n_events=len(run),
                repeats=1,
                classification="transient",
                hour_utc=hour_utc,
            )
        )

    for window in windows:
        same_hour = sum(
            1 for other in windows if other.hour_utc == window.hour_utc
        )
        if window.duration_s > 120.0:
            window.classification = "persistent"
        elif (
            len(windows) >= 2
            and same_hour >= 2
            and same_hour < len(windows)
        ):
            # The excursion recurs at the same time-of-day bucket across
            # different hours, not merely several times within one short span.
            window.classification = "structural"
        elif len(windows) >= 2:
            window.classification = "repeating"
        window.repeats = len(windows)
    return windows


# ---------------------------------------------------------------------------
# Hour-of-day structure from saved history
# ---------------------------------------------------------------------------

@dataclass
class HourProfile:
    hour_utc: int
    n_rows: int
    volume_median_base: float
    move_median_bps: float
    spread_median_usd: float
    structural: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "hour_utc": self.hour_utc,
            "n_rows": self.n_rows,
            "volume_median_base": _fmt(self.volume_median_base),
            "move_median_bps": _fmt(self.move_median_bps),
            "spread_median_usd": _fmt(self.spread_median_usd),
            "structural": self.structural,
        }


def analyze_hour_history(
    path: Path,
    left_key: str = "wti_close",
    right_key: str = "brentoil_close",
    volume_key: str = "wti_volume_base",
    structural_volume_ratio: float = 1.5,
) -> list[HourProfile]:
    """Hour-of-day profile over a saved hourly series (UTC buckets)."""
    per_hour: dict[int, list[dict[str, Any]]] = {}
    with open(path, "r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            ts = row.get("timestamp_utc") or row.get("timestamp_ms")
            hour = None
            if isinstance(ts, str):
                try:
                    hour = datetime.fromisoformat(ts.replace("Z", "+00:00")).hour
                except ValueError:
                    hour = None
            elif isinstance(ts, (int, float)):
                hour = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).hour
            if hour is None:
                continue
            per_hour.setdefault(hour, []).append(row)

    profiles: list[HourProfile] = []
    hour_keys = sorted(per_hour)
    if not hour_keys:
        return profiles
    all_volumes = [
        float(row.get(volume_key, 0.0) or 0.0)
        for hour in hour_keys
        for row in per_hour[hour]
    ]
    volume_median_all = _median(all_volumes) if all_volumes else 0.0
    for hour in hour_keys:
        rows = per_hour[hour]
        volumes = [float(row.get(volume_key, 0.0) or 0.0) for row in rows]
        moves = []
        spreads = []
        for row in rows:
            left = row.get(left_key)
            right = row.get(right_key)
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                if left > 0:
                    moves.append(abs(left - right) / left * 10_000)
                spreads.append(right - left)
        profile = HourProfile(
            hour_utc=hour,
            n_rows=len(rows),
            volume_median_base=_median(volumes) if volumes else 0.0,
            move_median_bps=_median(moves) if moves else 0.0,
            spread_median_usd=_median(spreads) if spreads else 0.0,
            structural=volume_median_all > 0
            and (_median(volumes) if volumes else 0.0) > structural_volume_ratio * volume_median_all,
        )
        profiles.append(profile)
    return profiles


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report(
    session_dir: Path,
    history_path: Optional[Path] = None,
    k: float = 6.0,
    silent_threshold_s: float = 30.0,
) -> dict[str, Any]:
    per_market = load_session_events(session_dir)
    health = load_health_events(session_dir)
    session_meta: dict[str, Any] = {}
    session_json = session_dir / "session.json"
    if session_json.exists():
        session_meta = json.loads(session_json.read_text(encoding="utf-8"))

    baselines = []
    anomalies = []
    for market in sorted(per_market):
        events = per_market[market]
        baseline = build_baseline(events, silent_threshold_s=silent_threshold_s)
        baselines.append(baseline.to_dict())
        anomalies.extend(
            window.to_dict()
            for window in detect_anomalies(events, baseline, k=k)
        )
    anomalies.sort(key=lambda item: item["start_utc"])

    health_summary: list[dict[str, Any]] = []
    for event in health:
        health_summary.append(
            {
                "at_utc": datetime.fromtimestamp(
                    event.get("at_ns", 0) / 1e9, tz=timezone.utc
                )
                .isoformat()
                .replace("+00:00", "Z"),
                "venue": event.get("venue"),
                "kind": event.get("kind"),
                "detail": {k2: v for k2, v in event.items() if k2 not in ("schema", "session", "at_ns", "venue", "kind")},
            }
        )

    return {
        "schema": SCHEMA,
        "session_id": session_meta.get("session_id"),
        "session_dir": str(session_dir),
        "analysis_config": {
            "k_mad": k,
            "silent_threshold_s": silent_threshold_s,
        },
        "session_meta": {
            key: value
            for key, value in session_meta.items()
            if key not in ("targets", "notes", "boundary")
        },
        "baselines": baselines,
        "anomaly_windows": anomalies,
        "health_events": health_summary,
        "hour_history": (
            [profile.to_dict() for profile in analyze_hour_history(history_path)]
            if history_path is not None and history_path.exists()
            else []
        ),
        "boundary": (
            "Baselines and anomaly windows are computed from the market's own "
            "recent data; they are research features, not trade signals. A spread "
            "excursion above baseline does not imply tradable profit after fees."
        ),
    }


def build_parser() -> Any:
    import argparse

    parser = argparse.ArgumentParser(description="Day15 continuous data analysis")
    parser.add_argument("--session-dir", type=Path, required=True)
    parser.add_argument(
        "--history",
        type=Path,
        default=Path("lab/data/lighter_rwa_aligned_1h.jsonl"),
    )
    parser.add_argument("--k", type=float, default=6.0)
    parser.add_argument("--silent-s", type=float, default=30.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/runs/day15-analysis.json"),
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(
        args.session_dir,
        history_path=args.history,
        k=args.k,
        silent_threshold_s=args.silent_s,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(args.output), "baselines": len(report["baselines"]), "anomalies": len(report["anomaly_windows"]), "health_events": len(report["health_events"]), "hour_history": len(report["hour_history"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
