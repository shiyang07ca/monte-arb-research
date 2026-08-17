#!/usr/bin/env python3
"""Day 8: normalize public order-book snapshots into one research schema.

Reads the read-only raw captures under lab/data/day8_raw/, builds one common
row structure, and attaches explicit semantic flags.  It does NOT claim that
same-named fields are equivalent across venues, and it never invents a
source_timestamp where the venue does not provide one.

Public input is read-only; this script only writes the derived snapshot and
mapping outputs.  No authentication, no order placement.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "lab" / "data" / "day8_raw"
DATA = ROOT / "lab" / "data"

SCHEMA_FIELDS = [
    "venue", "market", "observation_type", "source_timestamp", "received_at",
    "side", "level_index", "price", "size", "size_units", "timestamp_semantics",
    "size_semantics", "precision", "quality_flags", "raw_ref",
]
SNAPSHOT_CSV = DATA / "day8_venue_snapshots.csv"
MAPPING_JSON = DATA / "day8_venue_field_mapping.json"
SUMMARY_JSON = DATA / "day8_venue_schema_summary.json"


def _load_meta(name: str) -> dict[str, Any]:
    path = RAW / f"{name}.meta.json"
    return json.loads(path.read_text()) if path.exists() else {}


def _iso(epoch_ms: int | None) -> str | None:
    if epoch_ms is None:
        return None
    return datetime.fromtimestamp(epoch_ms / 1000, timezone.utc).isoformat()


def _norm(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _flag(existing: list[str], flag: str) -> list[str]:
    if flag not in existing:
        existing.append(flag)
    return existing


def _row(venue: str, market: str, source_ts: int | None, received_at: str | None,
         side: str, index: int, price: float | None, size: float | None,
         size_units: str, ts_semantics: str, size_semantics: str,
         precision: str, flags: list[str], raw_ref: str) -> dict[str, str]:
    return {
        "venue": venue,
        "market": market,
        "observation_type": "order_book_level",
        "source_timestamp": "" if source_ts is None else _iso(source_ts) or "",
        "received_at": received_at or "",
        "side": side,
        "level_index": str(index),
        "price": "" if price is None else f"{price:.12g}",
        "size": "" if size is None else f"{size:.12g}",
        "size_units": size_units,
        "timestamp_semantics": ts_semantics,
        "size_semantics": size_semantics,
        "precision": precision,
        "quality_flags": "|".join(flags),
        "raw_ref": raw_ref,
    }


def lighter_rows(meta: dict[str, Any], name: str) -> list[dict[str, str]]:
    detail = json.loads((RAW / f"{name}.json").read_text())
    market = meta.get("params", {}).get("market_id", "")
    received = meta.get("received_at")
    ref = f"lab/data/day8_raw/{name}.json"
    rows: list[dict[str, str]] = []
    for side_key, side in (("bids", "bid"), ("asks", "ask")):
        for index, level in enumerate(detail.get(side_key, [])):
            price = _norm(level.get("price"))
            size = _norm(level.get("remaining_base_amount"))
            flags: list[str] = []
            if price is None or size is None:
                _flag(flags, "invalid_numeric")
            rows.append(_row(
                "lighter", f"market_id={market}", None, received, side, index,
                price, size, "base", "missing_source_timestamp",
                "order_level_remaining", "supported_price_decimals/supported_size_decimals",
                flags, ref))
    return rows


def binance_rows(meta: dict[str, Any], name: str) -> list[dict[str, str]]:
    detail = json.loads((RAW / f"{name}.json").read_text())
    received = meta.get("received_at")
    ref = f"lab/data/day8_raw/{name}.json"
    e_ms = detail.get("E")
    rows: list[dict[str, str]] = []
    for side_key, side in (("bids", "bid"), ("asks", "ask")):
        for index, level in enumerate(detail.get(side_key, [])):
            price = _norm(level[0])
            size = _norm(level[1])
            flags: list[str] = []
            if price is None or size is None:
                _flag(flags, "invalid_numeric")
            rows.append(_row(
                "binance", "BTCUSDT", e_ms, received, side, index,
                price, size, "base", "event_time_E", "aggregated",
                "pricePrecision/quantityPrecision", flags, ref))
    return rows


def hyperliquid_rows(meta: dict[str, Any], name: str) -> list[dict[str, str]]:
    detail = json.loads((RAW / f"{name}.json").read_text())
    received = meta.get("received_at")
    ref = f"lab/data/day8_raw/{name}.json"
    rows: list[dict[str, str]] = []
    for side_idx, side in ((0, "bid"), (1, "ask")):
        for index, level in enumerate(detail.get("levels", [])[side_idx]):
            price = _norm(level.get("px"))
            size = _norm(level.get("sz"))
            flags: list[str] = []
            if price is None or size is None:
                _flag(flags, "invalid_numeric")
            size_sem = f"aggregated_n={level.get('n')}" if level.get("n") is not None else "aggregated"
            rows.append(_row(
                "hyperliquid", detail.get("coin", "BTC"), detail.get("time"),
                received, side, index, price, size, "base",
                "book_time", size_sem, "szDecimals", flags, ref))
    return rows


def funding_rows(meta: dict[str, Any], name: str, venue: str, market: str) -> list[dict[str, str]]:
    detail = json.loads((RAW / f"{name}.json").read_text())
    received = meta.get("received_at")
    ref = f"lab/data/day8_raw/{name}.json"
    rows: list[dict[str, str]] = []
    for row in detail if isinstance(detail, list) else []:
        source_ts = row.get("fundingTime") if venue == "binance" else row.get("time")
        rate = _norm(row.get("fundingRate"))
        flags: list[str] = []
        if rate is None:
            _flag(flags, "invalid_numeric")
        rows.append(_row(
            venue, market, source_ts, received, "funding", 0, None, rate,
            "rate_per_period", "funding_time_ms", "rate_value", "N/A", flags, ref))
    return rows


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    rows.extend(lighter_rows(_load_meta("lighter_wti_book_ok"), "lighter_wti_book_ok"))
    rows.extend(lighter_rows(_load_meta("lighter_brent_book_ok"), "lighter_brent_book_ok"))
    rows.extend(binance_rows(_load_meta("binance_book"), "binance_book"))
    rows.extend(hyperliquid_rows(_load_meta("hyperliquid_l2book"), "hyperliquid_l2book"))
    rows.extend(funding_rows(_load_meta("binance_funding"), "binance_funding", "binance", "BTCUSDT"))
    rows.extend(funding_rows(_load_meta("hyperliquid_funding_recent"), "hyperliquid_funding_recent", "hyperliquid", "BTC"))
    return rows


def build_mapping() -> list[dict[str, str]]:
    return [
        {"concept": "price", "lighter": "asks/bids[].price", "binance": "asks/bids[i][0]", "hyperliquid": "levels[side][i].px", "equivalent": "yes_after_parse", "note": "string to float; decimal places differ"},
        {"concept": "size", "lighter": "asks/bids[].remaining_base_amount", "binance": "asks/bids[i][1]", "hyperliquid": "levels[side][i].sz", "equivalent": "not_equivalent", "note": "lighter order-level partial fills; binance/hl aggregated levels"},
        {"concept": "side", "lighter": "bids/asks arrays", "binance": "bids/asks arrays", "hyperliquid": "levels[0]=bid levels[1]=ask", "equivalent": "yes", "note": "ordering by best price"},
        {"concept": "source_timestamp", "lighter": "none public", "binance": "E or T", "hyperliquid": "time", "equivalent": "not_equivalent", "note": "lighter snapshot has no public timestamp; must mark missing"},
        {"concept": "limit", "lighter": "1-250 required", "binance": "5-1000 default 500", "hyperliquid": "max 20 per side", "equivalent": "not_equivalent", "note": "different max and required semantics"},
        {"concept": "price_precision", "lighter": "supported_price_decimals", "binance": "pricePrecision", "hyperliquid": "szDecimals only (size)", "equivalent": "not_equivalent", "note": "field names and availability differ"},
        {"concept": "size_precision", "lighter": "supported_size_decimals", "binance": "quantityPrecision", "hyperliquid": "szDecimals", "equivalent": "not_equivalent", "note": "different sources"},
        {"concept": "min_order", "lighter": "min_base_amount/min_quote_amount", "binance": "LOT_SIZE.minQty + MIN_NOTIONAL", "hyperliquid": "not in meta", "equivalent": "not_equivalent", "note": "hyperliquid has no public min order field"},
        {"concept": "funding_timestamp", "lighter": "timestamp seconds", "binance": "fundingTime ms", "hyperliquid": "time ms", "equivalent": "not_equivalent", "note": "unit differs between venues"},
        {"concept": "funding_rate", "lighter": "rate decimal", "binance": "fundingRate decimal", "hyperliquid": "fundingRate decimal", "equivalent": "yes_after_parse", "note": "account ledger semantics not verified"},
    ]


def write_outputs(
    rows: list[dict[str, str]],
    mapping: list[dict[str, str]],
    *,
    snapshot_csv: Path = SNAPSHOT_CSV,
    mapping_json: Path = MAPPING_JSON,
    summary_json: Path = SUMMARY_JSON,
) -> dict[str, Any]:
    snapshot_csv.parent.mkdir(parents=True, exist_ok=True)
    mapping_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    with snapshot_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCHEMA_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    mapping_json.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n")
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = counts.setdefault(row["venue"], {})
        bucket[row["side"]] = bucket.get(row["side"], 0) + 1
        bucket["total"] = bucket.get("total", 0) + 1
    summary = {
        "schema": "day8-venue-snapshot-v1",
        "rows": len(rows),
        "venues": counts,
        "mapping_entries": len(mapping),
        "not_equivalent_fields": [item["concept"] for item in mapping if item["equivalent"] == "not_equivalent"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "unknowns": [
            "lighter orderBookOrders snapshot has no public timestamp field",
            "funding rate semantics not verified against account cash ledger",
            "hyperliquid min order size not exposed in meta",
        ],
    }
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary


def main() -> int:
    rows = build_rows()
    mapping = build_mapping()
    summary = write_outputs(rows, mapping)
    print(json.dumps({"snapshot_csv": str(SNAPSHOT_CSV), "mapping": str(MAPPING_JSON), "summary": str(SUMMARY_JSON), **summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
