#!/usr/bin/env python3
"""Audit and align read-only Lighter WTI/BRENTOIL responses.

The script keeps the raw responses untouched, reports coverage and data-quality
flags, and writes a descriptive-only audit plus a common hourly series. It does
not fit a strategy, send orders, or authenticate.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "lab" / "data" / "lighter_rwa_raw"
DATA = ROOT / "lab" / "data"


def read_json(name: str):
    return json.loads((RAW / name).read_text())


def iso_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()


def iso_s(value: int) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def candle_rows(symbol: str, resolution: str) -> list[dict]:
    return read_json(f"{symbol}_candles_{resolution}.json")["c"]


def funding_rows(symbol: str) -> list[dict]:
    return read_json(f"{symbol}_fundings_1h.json")["fundings"]


def correlation(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("correlation needs two equal non-empty series")
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (len(xs) - 1)
    sx, sy = statistics.stdev(xs), statistics.stdev(ys)
    return cov / (sx * sy)


def describe_daily(symbol: str) -> dict[str, object]:
    rows = candle_rows(symbol, "1d")
    groups: dict[int, list[dict]] = {}
    for row in rows:
        groups.setdefault(int(row["t"]), []).append(row)
    timestamps = sorted(groups)
    return {
        "rows": len(rows),
        "unique_timestamps": len(timestamps),
        "duplicate_rows": sum(len(group) - 1 for group in groups.values()),
        "duplicate_timestamps": [
            {"t": timestamp, "count": len(group)}
            for timestamp, group in groups.items()
            if len(group) > 1
        ],
        "range_utc": [iso_ms(timestamps[0]), iso_ms(timestamps[-1])]
        if timestamps
        else None,
    }


def describe_funding(symbol: str) -> dict[str, object]:
    rows = funding_rows(symbol)
    timestamps = [int(row["timestamp"]) for row in rows]
    values = [float(row["value"]) for row in rows]
    rates = [float(row["rate"]) for row in rows]
    return {
        "rows": len(rows),
        "unique_timestamps": len(set(timestamps)),
        "range_utc": [iso_s(min(timestamps)), iso_s(max(timestamps))],
        "value_min": min(values),
        "value_max": max(values),
        "value_mean": statistics.mean(values),
        "rate_min": min(rates),
        "rate_max": max(rates),
        "direction_counts": dict(Counter(row.get("direction") for row in rows)),
    }


def main() -> int:
    wti = candle_rows("WTI", "1h")
    brent = candle_rows("BRENTOIL", "1h")
    wti_by_time = {int(row["t"]): row for row in wti}
    brent_by_time = {int(row["t"]): row for row in brent}
    common = sorted(set(wti_by_time) & set(brent_by_time))
    if not common:
        raise RuntimeError("no common hourly timestamps")

    closes = [
        (float(wti_by_time[t]["c"]), float(brent_by_time[t]["c"]))
        for t in common
    ]
    differences = [wti_close - brent_close for wti_close, brent_close in closes]
    ratios = [wti_close / brent_close for wti_close, brent_close in closes]
    wti_returns = [
        math.log(closes[i][0] / closes[i - 1][0]) for i in range(1, len(closes))
    ]
    brent_returns = [
        math.log(closes[i][1] / closes[i - 1][1]) for i in range(1, len(closes))
    ]

    wti_funding = {int(row["timestamp"]): row for row in funding_rows("WTI")}
    brent_funding = {
        int(row["timestamp"]): row for row in funding_rows("BRENTOIL")
    }
    funding_common = sorted(set(wti_funding) & set(brent_funding))
    funding_differences = [
        float(wti_funding[t]["value"]) - float(brent_funding[t]["value"])
        for t in funding_common
    ]

    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Lighter public API; raw responses in lab/data/lighter_rwa_raw/",
        "raw_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(RAW.glob("*.json"))
        },
        "markets": {"WTI": 145, "BRENTOIL": 159},
        "coverage": {
            "candles_1h": {
                "WTI": {
                    "rows": len(wti),
                    "range_utc": [iso_ms(min(wti_by_time)), iso_ms(max(wti_by_time))],
                    "unique_timestamps": len(wti_by_time),
                },
                "BRENTOIL": {
                    "rows": len(brent),
                    "range_utc": [
                        iso_ms(min(brent_by_time)),
                        iso_ms(max(brent_by_time)),
                    ],
                    "unique_timestamps": len(brent_by_time),
                },
                "common_rows": len(common),
                "common_range_utc": [iso_ms(common[0]), iso_ms(common[-1])],
            },
            "daily_raw": {
                "WTI": describe_daily("WTI"),
                "BRENTOIL": describe_daily("BRENTOIL"),
            },
            "fundings_1h": {
                "WTI": describe_funding("WTI"),
                "BRENTOIL": describe_funding("BRENTOIL"),
            },
        },
        "descriptive_only": {
            "log_close_return_rows": len(wti_returns),
            "log_close_return_correlation": correlation(wti_returns, brent_returns),
            "fixed_close_difference": {
                "min": min(differences),
                "max": max(differences),
                "first": differences[0],
                "last": differences[-1],
            },
            "close_ratio": {
                "min": min(ratios),
                "max": max(ratios),
                "first": ratios[0],
                "last": ratios[-1],
            },
            "funding_value_difference_wti_minus_brent": {
                "rows": len(funding_differences),
                "mean": statistics.mean(funding_differences),
                "min": min(funding_differences),
                "max": max(funding_differences),
            },
        },
        "decision": "BLOCKED_FOR_STRATEGY_CONCLUSION",
        "blockers": [
            "HISTORY_DEPTH_INSUFFICIENT: one candles response is capped at 500 rows; the current common hourly sample is about 21 days.",
            "ROLL_SEMANTICS_MUST_BE_MODELED: WTI and BRENTOIL have different roll windows and roll times.",
            "FUNDING_LEDGER_UNKNOWN: API value/rate/direction fields are not yet verified against an account cash ledger.",
            "DEPTH_AND_EXIT_UNKNOWN: no target-size order-book replay or exit-slippage study has been completed.",
            "PERMISSION_UNKNOWN: account, region, and live-trading permissions are not part of this public read-only audit.",
        ],
    }
    (DATA / "lighter_rwa_data_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n"
    )

    aligned = []
    for timestamp in common:
        wti_row, brent_row = wti_by_time[timestamp], brent_by_time[timestamp]
        aligned.append(
            json.dumps(
                {
                    "timestamp_ms": timestamp,
                    "timestamp_utc": iso_ms(timestamp),
                    "wti_close": float(wti_row["c"]),
                    "brentoil_close": float(brent_row["c"]),
                    "wti_volume_base": float(wti_row["v"]),
                    "brentoil_volume_base": float(brent_row["v"]),
                    "wti_quote_volume": float(wti_row["V"]),
                    "brentoil_quote_volume": float(brent_row["V"]),
                },
                ensure_ascii=False,
            )
        )
    (DATA / "lighter_rwa_aligned_1h.jsonl").write_text("\n".join(aligned) + "\n")
    print(
        json.dumps(
            {
                "audit": str(DATA / "lighter_rwa_data_audit.json"),
                "aligned": str(DATA / "lighter_rwa_aligned_1h.jsonl"),
                "common_rows": len(common),
                "log_return_correlation": audit["descriptive_only"][
                    "log_close_return_correlation"
                ],
                "daily_duplicate_rows": {
                    symbol: audit["coverage"]["daily_raw"][symbol]["duplicate_rows"]
                    for symbol in ("WTI", "BRENTOIL")
                },
                "decision": audit["decision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
