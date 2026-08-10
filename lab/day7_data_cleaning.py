#!/usr/bin/env python3
"""Day 7: auditable, reproducible cleaning for the local Lighter snapshot.

Raw JSON is never overwritten.  The generated long-form CSV keeps the union of
candle and funding timestamps, attaches quality/admission flags, and records
source paths.  It does not interpolate, silently drop jumps, fit a strategy, or
send authenticated requests.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "lab" / "data" / "lighter_rwa_raw"
DATA_DIR = ROOT / "lab" / "data"
CLEAN_CSV = DATA_DIR / "lighter_rwa_clean_1h.csv"
SUMMARY_JSON = DATA_DIR / "day7_cleaning_summary.json"
REPORT_MD = ROOT / "notes" / "data-quality-report.md"

VERSION = "day7-v1"
HOUR_MS = 60 * 60 * 1000
JUMP_THRESHOLD = 0.05
MARKET_IDS = {"WTI": 145, "BRENTOIL": 159}
CANDLE_REQUIRED = ("t", "o", "h", "l", "c", "v", "V")
CANDLE_NUMERIC = ("o", "h", "l", "c", "v", "V")
FUNDING_REQUIRED = ("timestamp", "value", "rate", "direction")
FUNDING_NUMERIC = ("value", "rate")
CSV_FIELDS = [
    "cleaning_version", "symbol", "market_id", "timestamp_utc", "timestamp_ms",
    "source_candle_file", "source_funding_file", "record_type", "split",
    "roll_coverage_status", "market_state_status", "open", "high", "low", "close",
    "volume_base", "volume_quote", "funding_value", "funding_rate",
    "funding_direction", "candle_present", "funding_present",
    "candle_duplicate_count", "funding_duplicate_count", "missing_interval",
    "missing_hours_before", "invalid_numeric", "non_positive_price",
    "zero_or_omitted_field", "close_jump_gt_5pct", "close_return",
    "price_stats_eligible", "funding_stats_eligible", "combined_pair_eligible",
    "admission_status", "exclusion_reason", "raw_candle_timestamp",
    "raw_funding_timestamp",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iso_ms(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).isoformat()


def raw_paths(symbol: str) -> tuple[Path, Path]:
    return RAW_DIR / f"{symbol}_candles_1h.json", RAW_DIR / f"{symbol}_fundings_1h.json"


def load_source(symbol: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candle_path, funding_path = raw_paths(symbol)
    return (
        json.loads(candle_path.read_text())["c"],
        json.loads(funding_path.read_text())["fundings"],
    )


def as_finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def group_by_timestamp(rows: Iterable[dict[str, Any]], key: str) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        try:
            grouped[int(row[key])].append(row)
        except (KeyError, TypeError, ValueError):
            # Current source has no such row; an invalid timestamp is not aligned.
            continue
    return dict(grouped)


def interval_flags(timestamps: Iterable[int]) -> dict[int, tuple[bool, int]]:
    """Return (gap_before, missing_hours_before) for each sorted timestamp."""
    ordered = sorted(set(timestamps))
    flags: dict[int, tuple[bool, int]] = {}
    previous: int | None = None
    for timestamp in ordered:
        if previous is None:
            flags[timestamp] = (False, 0)
        else:
            delta = timestamp - previous
            missing_hours = max(0, int(delta // HOUR_MS) - 1) if delta >= HOUR_MS else 0
            flags[timestamp] = (delta != HOUR_MS, missing_hours)
        previous = timestamp
    return flags


def raw_field_flags(
    row: dict[str, Any] | None,
    required: tuple[str, ...],
    numeric_fields: tuple[str, ...] | None = None,
) -> tuple[bool, bool, str]:
    """Return invalid_numeric, zero_or_omitted, and a stable field list.

    Zero is recorded as a quality flag, not automatically treated as invalid:
    a zero funding rate can be a legitimate observation.  Missing/zero fields
    are kept separate from numeric parse failures so the caller can choose the
    relevant admission rule for price or funding statistics.
    """
    numeric = set(numeric_fields or tuple(field for field in required if field not in {"t", "timestamp"}))
    if row is None:
        return False, True, "record_missing"
    flagged: list[str] = []
    invalid = False
    for field in required:
        if field not in row:
            flagged.append(field)
            continue
        if field not in numeric:
            if row[field] in (None, ""):
                flagged.append(field)
            continue
        number = as_finite_float(row[field])
        if number is None:
            invalid = True
        elif number == 0:
            flagged.append(field)
    return invalid, bool(flagged), "|".join(flagged)


def required_fields_present(row: dict[str, Any] | None, required: tuple[str, ...]) -> bool:
    return row is not None and all(field in row and row[field] not in (None, "") for field in required)


def split_timestamps(timestamps: Iterable[int]) -> tuple[dict[int, str], dict[str, Any]]:
    ordered = sorted(set(timestamps))
    if not ordered:
        raise ValueError("cannot split an empty timestamp set")
    first_cut = max(1, int(len(ordered) * 0.60))
    second_cut = min(len(ordered), max(first_cut + 1, int(len(ordered) * 0.80)))
    labels: dict[int, str] = {}
    for index, timestamp in enumerate(ordered):
        labels[timestamp] = "train" if index < first_cut else "validation" if index < second_cut else "test"
    ranges: dict[str, Any] = {}
    for split in ("train", "validation", "test"):
        members = [timestamp for timestamp in ordered if labels[timestamp] == split]
        ranges[split] = {
            "timestamps": len(members),
            "range_utc": [iso_ms(members[0]), iso_ms(members[-1])] if members else None,
        }
    return labels, {"method": "chronological_unique_timestamp_60_20_20", "unique_timestamps": len(ordered), "ranges": ranges}


def roll_coverage_status(timestamp_ms: int) -> str:
    date = datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).date()
    if date < datetime(2026, 8, 7, tzinfo=timezone.utc).date():
        return "pre_roll"
    if date <= datetime(2026, 8, 13, tzinfo=timezone.utc).date():
        return "official_roll_example_window"
    return "post_example_window"


def _canonical(grouped: dict[int, list[dict[str, Any]]], timestamp: int) -> dict[str, Any] | None:
    rows = grouped.get(timestamp, [])
    return rows[0] if rows else None


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _build_market_records(symbol: str) -> tuple[list[dict[str, str]], dict[str, Any], dict[str, str], set[int]]:
    candle_path, funding_path = raw_paths(symbol)
    candles, fundings = load_source(symbol)
    candle_groups = group_by_timestamp(candles, "t")
    funding_groups = group_by_timestamp(fundings, "timestamp")
    candle_ms = sorted(candle_groups)
    funding_ms = sorted(timestamp * 1000 for timestamp in funding_groups)
    candle_intervals = interval_flags(candle_ms)
    funding_intervals = interval_flags(funding_ms)
    candle_by_ms = candle_groups
    funding_by_ms = {timestamp * 1000: rows for timestamp, rows in funding_groups.items()}
    timestamps = sorted(set(candle_by_ms) | set(funding_by_ms))

    previous_close: float | None = None
    records: list[dict[str, str]] = []
    jump_timestamps: list[str] = []
    invalid_source_rows = 0

    for timestamp_ms in timestamps:
        candle = _canonical(candle_by_ms, timestamp_ms)
        funding = _canonical(funding_by_ms, timestamp_ms)
        candle_rows = candle_by_ms.get(timestamp_ms, [])
        funding_rows = funding_by_ms.get(timestamp_ms, [])
        candle_present = candle is not None
        funding_present = funding is not None
        candle_duplicate_count = len(candle_rows)
        funding_duplicate_count = len(funding_rows)

        candle_invalid, _, candle_flags = raw_field_flags(candle, CANDLE_REQUIRED, CANDLE_NUMERIC)
        funding_invalid, _, funding_flags = raw_field_flags(funding, FUNDING_REQUIRED, FUNDING_NUMERIC)
        invalid_numeric = candle_invalid or funding_invalid
        if invalid_numeric:
            invalid_source_rows += 1
        quality_fields = []
        if candle_flags:
            quality_fields.append(f"candle:{candle_flags}")
        if funding_flags:
            quality_fields.append(f"funding:{funding_flags}")

        price_values = [as_finite_float(candle.get(field)) if candle else None for field in ("o", "h", "l", "c")]
        close = price_values[-1]
        non_positive_price = any(value is not None and value <= 0 for value in price_values)
        close_return: float | None = None
        close_jump = False
        if close is not None and previous_close not in (None, 0):
            close_return = close / previous_close - 1
            close_jump = abs(close_return) > JUMP_THRESHOLD
        if close_jump:
            jump_timestamps.append(iso_ms(timestamp_ms))
        if close is not None:
            previous_close = close

        candle_gap, candle_missing_hours = candle_intervals.get(timestamp_ms, (False, 0))
        funding_gap, funding_missing_hours = funding_intervals.get(timestamp_ms, (False, 0))
        missing_interval = candle_gap if candle_present else funding_gap
        missing_hours_before = candle_missing_hours if candle_present else funding_missing_hours
        record_type = "candle_and_funding" if candle_present and funding_present else "candle_only" if candle_present else "funding_only"

        price_valid = candle_present and required_fields_present(candle, CANDLE_REQUIRED) and not candle_invalid and not non_positive_price and all(value is not None for value in price_values)
        funding_valid = funding_present and required_fields_present(funding, FUNDING_REQUIRED) and not funding_invalid
        duplicate = candle_duplicate_count > 1 or funding_duplicate_count > 1
        price_eligible = price_valid and not duplicate and not candle_gap
        funding_eligible = funding_valid and not duplicate and not funding_gap
        combined_eligible = price_eligible and funding_eligible and candle_present and funding_present

        reasons: list[str] = []
        if not candle_present:
            reasons.append("missing_candle")
        if not funding_present:
            reasons.append("missing_funding")
        if invalid_numeric:
            reasons.append("invalid_numeric")
        if non_positive_price:
            reasons.append("non_positive_price")
        if duplicate:
            reasons.append("duplicate_timestamp_explicit_review")
        if missing_interval:
            reasons.append("missing_interval_no_interpolation")
        if combined_eligible and close_jump:
            admission_status = "eligible_with_jump_flag"
        elif combined_eligible:
            admission_status = "eligible"
        elif price_eligible or funding_eligible:
            admission_status = "partially_eligible"
        else:
            admission_status = "not_eligible"

        records.append({
            "cleaning_version": VERSION,
            "symbol": symbol,
            "market_id": str(MARKET_IDS[symbol]),
            "timestamp_utc": iso_ms(timestamp_ms),
            "timestamp_ms": str(timestamp_ms),
            "source_candle_file": candle_path.relative_to(ROOT).as_posix(),
            "source_funding_file": funding_path.relative_to(ROOT).as_posix(),
            "record_type": record_type,
            "split": "__SPLIT_LATER__",
            "roll_coverage_status": roll_coverage_status(timestamp_ms),
            "market_state_status": "unknown_from_public_candle_snapshot",
            "open": _text(candle.get("o") if candle else None),
            "high": _text(candle.get("h") if candle else None),
            "low": _text(candle.get("l") if candle else None),
            "close": _text(candle.get("c") if candle else None),
            "volume_base": _text(candle.get("v") if candle else None),
            "volume_quote": _text(candle.get("V") if candle else None),
            "funding_value": _text(funding.get("value") if funding else None),
            "funding_rate": _text(funding.get("rate") if funding else None),
            "funding_direction": _text(funding.get("direction") if funding else None),
            "candle_present": str(candle_present).lower(),
            "funding_present": str(funding_present).lower(),
            "candle_duplicate_count": str(candle_duplicate_count),
            "funding_duplicate_count": str(funding_duplicate_count),
            "missing_interval": str(bool(missing_interval)).lower(),
            "missing_hours_before": str(missing_hours_before),
            "invalid_numeric": str(invalid_numeric).lower(),
            "non_positive_price": str(non_positive_price).lower(),
            "zero_or_omitted_field": "|".join(quality_fields),
            "close_jump_gt_5pct": str(close_jump).lower(),
            "close_return": "" if close_return is None else f"{close_return:.12g}",
            "price_stats_eligible": str(price_eligible).lower(),
            "funding_stats_eligible": str(funding_eligible).lower(),
            "combined_pair_eligible": str(combined_eligible).lower(),
            "admission_status": admission_status,
            "exclusion_reason": "|".join(reasons),
            "raw_candle_timestamp": _text(candle.get("t") if candle else None),
            "raw_funding_timestamp": _text(funding.get("timestamp") if funding else None),
        })

    market_summary = {
        "market_id": MARKET_IDS[symbol],
        "raw_candle_rows": len(candles),
        "raw_funding_rows": len(fundings),
        "unique_candle_timestamps": len(candle_groups),
        "unique_funding_timestamps": len(funding_groups),
        "union_rows": len(records),
        "candle_and_funding_rows": sum(row["record_type"] == "candle_and_funding" for row in records),
        "funding_only_rows": sum(row["record_type"] == "funding_only" for row in records),
        "candle_only_rows": sum(row["record_type"] == "candle_only" for row in records),
        "duplicate_candle_timestamps": sum(len(rows) > 1 for rows in candle_groups.values()),
        "duplicate_funding_timestamps": sum(len(rows) > 1 for rows in funding_groups.values()),
        "candle_missing_interval_rows": sum(flag[0] for flag in candle_intervals.values()),
        "funding_missing_interval_rows": sum(flag[0] for flag in funding_intervals.values()),
        "invalid_source_rows": invalid_source_rows,
        "close_jump_gt_5pct_rows": len(jump_timestamps),
        "close_jump_timestamps_utc": jump_timestamps,
        "timestamp_range_candles_utc": [iso_ms(min(candle_ms)), iso_ms(max(candle_ms))],
        "timestamp_range_fundings_utc": [iso_ms(min(funding_ms)), iso_ms(max(funding_ms))],
        "price_eligible_rows": sum(row["price_stats_eligible"] == "true" for row in records),
        "funding_eligible_rows": sum(row["funding_stats_eligible"] == "true" for row in records),
        "combined_eligible_rows": sum(row["combined_pair_eligible"] == "true" for row in records),
    }
    source_summary = {
        "candle_file": candle_path.relative_to(ROOT).as_posix(),
        "funding_file": funding_path.relative_to(ROOT).as_posix(),
        "candle_sha256": sha256_file(candle_path),
        "funding_sha256": sha256_file(funding_path),
    }
    return records, market_summary, source_summary, set(timestamps)


def build_records() -> tuple[list[dict[str, str]], dict[str, Any]]:
    all_records: list[dict[str, str]] = []
    source: dict[str, dict[str, str]] = {}
    per_market: dict[str, dict[str, Any]] = {}
    all_timestamps: set[int] = set()
    for symbol in MARKET_IDS:
        records, market_summary, source_summary, timestamps = _build_market_records(symbol)
        all_records.extend(records)
        per_market[symbol] = market_summary
        source[symbol] = source_summary
        all_timestamps.update(timestamps)

    split_map, split_summary = split_timestamps(all_timestamps)
    for record in all_records:
        record["split"] = split_map[int(record["timestamp_ms"])]
    all_records.sort(key=lambda row: (row["timestamp_ms"], row["symbol"]))

    summary = {
        "schema": "day7-cleaning-summary-v1",
        "cleaning_version": VERSION,
        "generated_at_utc": "derived-from-source-snapshot",
        "rules": {
            "timestamp": "parse candle milliseconds and funding seconds into UTC; preserve raw timestamp fields",
            "duplicates": "retain raw JSON; flag duplicate timestamps and exclude from statistics pending explicit review",
            "missing_intervals": "flag gaps; never interpolate",
            "invalid_values": "flag non-numeric/non-finite and non-positive prices; keep raw row",
            "jumps": f"flag abs close-to-close return > {JUMP_THRESHOLD:.0%}; do not delete automatically",
            "split": "chronological unique timestamps, 60% train / 20% validation / 20% test",
            "raw_preservation": "raw source files are read-only and never overwritten",
        },
        "source": source,
        "per_market": per_market,
        "output": {
            "rows": len(all_records),
            "unique_timestamps": len(all_timestamps),
            "candle_and_funding_rows": sum(row["record_type"] == "candle_and_funding" for row in all_records),
            "funding_only_rows": sum(row["record_type"] == "funding_only" for row in all_records),
            "candle_only_rows": sum(row["record_type"] == "candle_only" for row in all_records),
            "price_eligible_rows": sum(row["price_stats_eligible"] == "true" for row in all_records),
            "funding_eligible_rows": sum(row["funding_stats_eligible"] == "true" for row in all_records),
            "combined_eligible_rows": sum(row["combined_pair_eligible"] == "true" for row in all_records),
            "eligible_with_jump_flag_rows": sum(row["admission_status"] == "eligible_with_jump_flag" for row in all_records),
            "not_eligible_rows": sum(row["admission_status"] == "not_eligible" for row in all_records),
        },
        "split": split_summary,
        "roll_coverage": {
            "observed_candle_range_utc": [min(row["timestamp_utc"] for row in all_records if row["candle_present"] == "true"), max(row["timestamp_utc"] for row in all_records if row["candle_present"] == "true")],
            "official_example_window_utc": ["2026-08-07T00:00:00+00:00", "2026-08-13T23:00:00+00:00"],
            "coverage_status": "pre_roll_only; no candle reaches the official 2026-08-07..13 example window",
        },
        "unknowns": [
            "candle timestamp boundary semantics (start or end of interval) remain unknown",
            "API candle zero omission means a missing field needs source-level interpretation",
            "funding API value/direction are not verified against an account funding ledger",
            "one 500-candle response is capped; this is not a long-history sample",
        ],
    }
    return all_records, summary


def render_report(summary: dict[str, Any]) -> str:
    per_market = summary["per_market"]
    output = summary["output"]
    split = summary["split"]
    lines = [
        "# Day 7 数据质量报告 / 可复现清洗结果", "",
        f"> 清洗版本：`{summary['cleaning_version']}`；生成方式：`{summary['generated_at_utc']}`。原始 JSON 只读，未被覆盖。", "",
        "## 唯一问题", "",
        "哪些样本可以进入描述性统计，哪些必须保留为异常证据？答案不是删除异常，而是给每一行可复查的状态。", "",
        "## 输入与覆盖", "",
        "| 市场 | candles 原始行 | fundings 原始行 | candle 时间范围 | funding 时间范围 | funding-only 行 | 组合可用行 |", "|---|---:|---:|---|---|---:|---:|",
    ]
    for symbol in MARKET_IDS:
        item = per_market[symbol]
        lines.append(f"| {symbol} | {item['raw_candle_rows']} | {item['raw_funding_rows']} | {item['timestamp_range_candles_utc'][0]} → {item['timestamp_range_candles_utc'][1]} | {item['timestamp_range_fundings_utc'][0]} → {item['timestamp_range_fundings_utc'][1]} | {item['funding_only_rows']} | {item['combined_eligible_rows']} |")
    lines += [
        "", "API candles 文档说明单次最多返回 500 根 candle，且零值字段可能省略；因此当前 500 行不是完整历史，缺字段也不能自动补零。", "",
        "## 清洗规则", "",
        "1. candle 的毫秒 timestamp、funding 的秒 timestamp 统一转换为 UTC，同时保留 `raw_*_timestamp`。",
        "2. 重复 timestamp 不静默覆盖：原始 JSON 保留，输出写入重复计数，并排除出统计直到明确复核。",
        "3. 缺失小时只标记 `missing_interval`，不插值。",
        "4. 非数字、非有限值和非正价格保留原行并标记 `invalid_numeric` / `non_positive_price`。",
        "5. 相邻 close 的绝对跳幅超过 5% 只标记 `close_jump_gt_5pct`，不自动删除。",
        "6. 按唯一 UTC timestamp 做 60%/20%/20% 的 train/validation/test 时间切分，禁止随机打乱。", "",
        "## 输出计数", "",
        f"- 长表行数：`{output['rows']}`；唯一 timestamp：`{output['unique_timestamps']}`。",
        f"- candle + funding：`{output['candle_and_funding_rows']}`；funding-only：`{output['funding_only_rows']}`；candle-only：`{output['candle_only_rows']}`。",
        f"- price 可用：`{output['price_eligible_rows']}`；funding 可用：`{output['funding_eligible_rows']}`；两者同时可用：`{output['combined_eligible_rows']}`。",
        f"- 带跳点标记但仍保留的组合行：`{output['eligible_with_jump_flag_rows']}`；完全不准入行：`{output['not_eligible_rows']}`。", "",
        "## 市场级异常证据", "",
    ]
    for symbol in MARKET_IDS:
        item = per_market[symbol]
        lines.append(f"- **{symbol}**：重复 candle `{item['duplicate_candle_timestamps']}`，重复 funding `{item['duplicate_funding_timestamps']}`；candle 缺口 `{item['candle_missing_interval_rows']}`，funding 缺口 `{item['funding_missing_interval_rows']}`；>5% close 跳点 `{item['close_jump_gt_5pct_rows']}`。")
        if item["close_jump_timestamps_utc"]:
            lines.append(f"  - 跳点时间：`{', '.join(item['close_jump_timestamps_utc'])}`。")
    lines += ["", "## 时间切分", "", "| split | 唯一 timestamp 数 | 范围 |", "|---|---:|---|"]
    for name in ("train", "validation", "test"):
        item = split["ranges"][name]
        lines.append(f"| {name} | {item['timestamps']} | {item['range_utc'][0]} → {item['range_utc'][-1]} |" if item["range_utc"] else f"| {name} | 0 | — |")
    lines += [
        "", "## 展期覆盖与未知", "",
        f"- 当前 candle 覆盖：`{summary['roll_coverage']['observed_candle_range_utc'][0]}` → `{summary['roll_coverage']['observed_candle_range_utc'][1]}`。",
        "- 官方示例展期窗口从 2026-08-07 开始；当前 candle 只到 2026-08-06，因此本数据集是 `pre_roll_only`，不能用来证明展期期间的反应。",
        "- candle timestamp 是区间开始还是结束仍 unknown。",
        "- funding `value` / `direction` 仍未与账户 funding ledger 核验；清洗完成不等于 funding PnL 已验证。",
        "- 当前输出适合教学和可复现审计，不足以证明 WTI–BRENTOIL 策略成立或可交易。", "",
        "## 证据路径", "",
        "- 原始输入：`lab/data/lighter_rwa_raw/`", "- 清洗脚本：`lab/day7_data_cleaning.py`", "- 清洗输出：`lab/data/lighter_rwa_clean_1h.csv`", "- 脱敏汇总：`lab/data/day7_cleaning_summary.json`", "- 测试：`lab/test_day7_data_cleaning.py`", "- 课程：`lessons/0006-day7-data-cleaning.html`", "",
        "## Primary source", "", "- [Lighter API candles](https://apidocs.lighter.xyz/reference/candles)", "- [Lighter API fundings](https://apidocs.lighter.xyz/reference/fundings)", "",
    ]
    return "\n".join(lines)


def write_outputs(records: list[dict[str, str]], summary: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with CLEAN_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    REPORT_MD.write_text(render_report(summary))


def main() -> int:
    records, summary = build_records()
    write_outputs(records, summary)
    print(json.dumps({"csv": str(CLEAN_CSV), "summary": str(SUMMARY_JSON), "report": str(REPORT_MD), "rows": len(records)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
