"""Depth diagnostics for persistent cross-venue spread differences.

Three read-only checks against real data:

1. FEED_INTEGRITY — compare a REST full book with the WS stream around the same
   moment: does the WS stream drop levels (pipeline artifact) or reproduce the
   REST book (real market structure)?
2. DEPTH_STRUCTURE — bid/ask depth distribution per market: is the wide Lighter
   spread accompanied by thin or one-sided depth?
3. MID_ALIGNMENT — align both venues' BRENTOIL mid prices on a one-second grid
   and measure the cross-venue mid difference distribution.

No PnL is calculated anywhere; results are research features only.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from .quote_collector import _parse, _request
from .market_event_analysis import MarketEvents, _median, load_session_events
from .market import MarketIdentity

LIGHTER_BRENT = MarketIdentity("lighter", "perp", "default", "BRENTOIL", "159")
HL_BRENT = MarketIdentity("hyperliquid", "perp", "xyz", "xyz:BRENTOIL", "110049")
LIGHTER_WTI = MarketIdentity("lighter", "perp", "default", "WTI", "145")

SCHEMA = "day15-experiment-b-v1"


def fetch_rest_book(identity: MarketIdentity, timeout: float = 20.0) -> dict[str, Any]:
    """Fetch a full REST book for one identity; returns normalized level pairs.

    Records BOTH wall-clock ns (comparable with WS event recv_ns) and the
    monotonic ns used by the quote collector internals.
    """
    started_wall_ns = time.time_ns()
    response = _request(identity, timeout)
    received_wall_ns = time.time_ns()
    observation = _parse(response)
    # _parse only keeps BBO; refetch raw rows via the raw response payload.
    import json as _json

    payload = _json.loads(response.raw)
    if identity.venue == "lighter":
        bids = payload.get("bids") or []
        asks = payload.get("asks") or []
        rows = (
            lambda side: [
                [str(r.get("price")), str(r.get("remaining_base_amount", r.get("size")))]
                for r in side
            ]
        )
        return {
            "identity": identity.to_dict(),
            "request_started_ns": response.request_started_ns,
            "response_received_ns": response.response_received_ns,
            "request_started_wall_ns": started_wall_ns,
            "response_received_wall_ns": received_wall_ns,
            "bids": rows(bids),
            "asks": rows(asks),
            "bbobid": observation.best_bid,
            "bboask": observation.best_ask,
        }
    levels = payload.get("levels") or []
    sides = payload.get("sides")
    if isinstance(sides, list) and len(sides) == 2 and sides[0] == "asks":
        asks, bids = levels
    else:
        bids, asks = levels
    rows = lambda side: [[str(r.get("px")), str(r.get("sz"))] for r in side]  # noqa: E731
    return {
        "identity": identity.to_dict(),
        "request_started_ns": response.request_started_ns,
        "response_received_ns": response.response_received_ns,
        "request_started_wall_ns": started_wall_ns,
        "response_received_wall_ns": received_wall_ns,
        "bids": rows(bids),
        "asks": rows(asks),
        "bbobid": observation.best_bid,
        "bboask": observation.best_ask,
    }


def compare_feeds(
    session_dir: Path,
    targets: Sequence[MarketIdentity],
    rest_rounds: int = 4,
    max_ws_skew_ms: float = 3_000.0,
    rest_snapshots: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
) -> list[dict[str, Any]]:
    """REST full book vs nearest WS snapshot per target; detects dropped levels.

    ``rest_snapshots`` (optional) maps market symbol -> pre-fetched REST books
    captured while the WS stream was live; without it, REST is re-fetched at
    analysis time, which is NOT the same moment as the WS session.
    """
    per_market = load_session_events(session_dir)
    results = []
    for identity in targets:
        ws_events = per_market.get(identity.symbol)
        if identity.venue == "lighter":
            ws_events = per_market.get(identity.local_id) or ws_events
        pre_fetched = (rest_snapshots or {}).get(identity.symbol) or (
            rest_snapshots or {}
        ).get(identity.local_id)
        for round_index in range(rest_rounds):
            if pre_fetched is not None and round_index < len(pre_fetched):
                rest = dict(pre_fetched[round_index])
            else:
                try:
                    rest = fetch_rest_book(identity)
                except Exception as exc:  # noqa: BLE001
                    results.append(
                        {
                            "market": identity.symbol,
                            "round": round_index,
                            "status": "REST_FAILED",
                            "detail": str(exc)[:200],
                        }
                    )
                    continue
            # Nearest WS book event within the REST request window. Use the
            # wall-clock window; monotonic ns is NOT comparable with WS recv_ns.
            nearest = None
            if ws_events is not None and ws_events.recv_ns:
                request_mid_ns: Optional[int] = None
                if rest.get("request_started_wall_ns") and rest.get(
                    "response_received_wall_ns"
                ):
                    request_mid_ns = (
                        rest["request_started_wall_ns"] + rest["response_received_wall_ns"]
                    ) // 2
                elif isinstance(rest.get("request_started_wall_ns"), int):
                    request_mid_ns = rest["request_started_wall_ns"]
                if request_mid_ns is not None:
                    candidates = [
                        (abs(ns - request_mid_ns), idx)
                        for idx, ns in enumerate(ws_events.recv_ns)
                    ]
                    skew_ns, idx = min(candidates)
                    if skew_ns / 1e6 <= max_ws_skew_ms:
                        nearest = {
                            "skew_ms": round(skew_ns / 1e6, 1),
                            "ws_bid_levels": ws_events.n_levels_bids[idx],
                            "ws_ask_levels": ws_events.n_levels_asks[idx],
                        }
                        # WS BBO is not retained per event in MarketEvents (only
                        # mid and spread); level-count comparison is the check.
            rest_bid_levels = len(rest["bids"])
            rest_ask_levels = len(rest["asks"])
            row: dict[str, Any] = {
                "market": identity.symbol,
                "round": round_index,
                "status": "OK",
                "rest_bid_levels": rest_bid_levels,
                "rest_ask_levels": rest_ask_levels,
                "rest_bbo_bid": rest["bbobid"],
                "rest_bbo_ask": rest["bboask"],
                "ws_nearby": nearest is not None,
            }
            if nearest is not None:
                row["ws_skew_ms"] = nearest["skew_ms"]
                row["ws_bid_levels"] = nearest["ws_bid_levels"]
                row["ws_ask_levels"] = nearest["ws_ask_levels"]
                row["level_delta_bids"] = rest_bid_levels - nearest["ws_bid_levels"]
                row["level_delta_asks"] = rest_ask_levels - nearest["ws_ask_levels"]
            results.append(row)
            time.sleep(0.5)
    return results


def depth_structure(events_by_market: Mapping[str, MarketEvents]) -> list[dict[str, Any]]:
    """Bid/ask depth and level-count structure per market."""
    out = []
    for market, events in sorted(events_by_market.items()):
        if events.n == 0:
            continue
        bid_levels = _median(events.n_levels_bids)
        ask_levels = _median(events.n_levels_asks)
        out.append(
            {
                "market": market,
                "venue": events.venue,
                "n_events": events.n,
                "median_levels_bid": round(bid_levels, 1),
                "median_levels_ask": round(ask_levels, 1),
                "median_depth_top1": round(_median(events.depth_top1), 1),
                "median_depth_top5": round(_median(events.depth_top5), 1),
                "spread_median_bps": round(_median(events.spread_bps), 3),
            }
        )
    return out


def mid_alignment(
    lighter: MarketEvents, hyperliquid: MarketEvents
) -> dict[str, Any]:
    """Align both venues' mids on a one-second grid; measure the difference."""
    grid: dict[int, dict[str, float]] = {}

    def put(events: MarketEvents, key: str) -> None:
        for ns, mid in zip(events.recv_ns, events.mid):
            bucket = int(ns / 1e9)
            grid.setdefault(bucket, {})[key] = mid

    put(lighter, "lighter")
    put(hyperliquid, "hyperliquid")
    diffs = []
    for bucket in sorted(grid):
        row = grid[bucket]
        if "lighter" in row and "hyperliquid" in row:
            diffs.append(
                {
                    "bucket_utc": datetime.fromtimestamp(bucket, tz=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "lighter_mid": row["lighter"],
                    "xyz_mid": row["hyperliquid"],
                    "diff_usd": row["lighter"] - row["hyperliquid"],
                    "diff_bps": (row["lighter"] - row["hyperliquid"])
                    / row["hyperliquid"]
                    * 10_000,
                }
            )
    if not diffs:
        return {"n_aligned_seconds": 0}
    diff_bps = [d["diff_bps"] for d in diffs]
    return {
        "n_aligned_seconds": len(diffs),
        "diff_usd_median": round(_median([d["diff_usd"] for d in diffs]), 6),
        "diff_bps_median": round(_median(diff_bps), 3),
        "diff_bps_p95_abs": round(sorted(abs(v) for v in diff_bps)[
            min(len(diff_bps) - 1, int(0.95 * len(diff_bps)))
        ], 3),
        "seconds": diffs[:50],
    }


def run_live_comparison(
    duration_s: float,
    out_root: Path,
    rest_interval_s: float = 5.0,
) -> dict[str, Any]:
    """Run a bounded WS capture while polling REST books; then compare feeds.

    This is the only honest FEED_INTEGRITY design: the REST snapshot and the WS
    events must belong to the same wall-clock window.
    """
    import subprocess
    import sys

    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)
    collector = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "monte_arb.market_event_collector",
            "--duration",
            str(duration_s),
            "--out",
            str(out_root),
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    snapshots: dict[str, list[dict[str, Any]]] = {
        identity.symbol: [] for identity in (LIGHTER_BRENT, HL_BRENT, LIGHTER_WTI)
    }
    deadline = time.monotonic() + duration_s
    while time.monotonic() < deadline:
        for identity in (LIGHTER_BRENT, HL_BRENT, LIGHTER_WTI):
            try:
                snapshots[identity.symbol].append(fetch_rest_book(identity))
            except Exception as exc:  # noqa: BLE001
                snapshots[identity.symbol].append(
                    {"market": identity.symbol, "status": "REST_FAILED", "detail": str(exc)[:200]}
                )
        time.sleep(rest_interval_s)
    collector.wait(timeout=60)

    sessions = sorted(out_root.glob("*/session.json"))
    if not sessions:
        raise RuntimeError("live capture produced no session")
    session_dir = sessions[-1].parent
    (session_dir / "rest_snapshots.json").write_text(
        json.dumps(snapshots, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return build_report(session_dir, rest_snapshots=snapshots)


def build_report(
    session_dir: Path, rest_snapshots: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None
) -> dict[str, Any]:
    per_market = load_session_events(session_dir)
    report = {
        "schema": SCHEMA,
        "session_dir": str(session_dir),
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "feed_integrity": compare_feeds(
            session_dir,
            targets=(LIGHTER_BRENT, HL_BRENT, LIGHTER_WTI),
            rest_snapshots=rest_snapshots,
        ),
        "depth_structure": depth_structure(per_market),
        "mid_alignment": mid_alignment(
            per_market.get("159", MarketEvents(market="159", venue="lighter")),
            per_market.get("xyz:BRENTOIL", MarketEvents(market="xyz:BRENTOIL", venue="hyperliquid")),
        ),
        "boundary": (
            "Read-only diagnostics. Level counts and mid differences are research "
            "features; they do not measure executable PnL after fees and slippage."
        ),
    }
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Day15 experiment B diagnostics")
    parser.add_argument("--session-dir", type=Path, default=None)
    parser.add_argument("--live-duration", type=float, default=0.0)
    parser.add_argument("--live-out", type=Path, default=Path("research/raw/day15/live-b"))
    parser.add_argument("--rest-interval-s", type=float, default=5.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/runs/day15-experiment-b.json"),
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.live_duration > 0:
        report = run_live_comparison(
            args.live_duration, args.live_out, rest_interval_s=args.rest_interval_s
        )
    elif args.session_dir is not None:
        report = build_report(args.session_dir)
    else:
        raise SystemExit("provide --session-dir or --live-duration")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "integrity_rows": len(report["feed_integrity"]),
                "depth_markets": len(report["depth_structure"]),
                "aligned_seconds": report["mid_alignment"].get("n_aligned_seconds", 0),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
