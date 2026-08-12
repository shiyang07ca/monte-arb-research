#!/usr/bin/env python3
"""Day 9: re-capture Lighter WTI/BRENTOIL parameters and diff against the old snapshot.

The old instrument matrix (2026-08-05) is a snapshot, not a fact sheet. This
script re-fetches the public read-only endpoints, saves the raw responses with
metadata, and diffs every field against the previous snapshot so the student
can see exactly what changed and what stayed stable.

Read-only: no authentication, no order placement, no private keys.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://mainnet.zklighter.elliot.ai"
ROOT = Path(__file__).resolve().parent.parent
RAW_OUT = ROOT / "lab" / "data" / "day9_raw"
DIFF_OUT = ROOT / "lab" / "data" / "day9_parameter_diff.json"
OLD_DETAILS = {
    145: ROOT / "lab" / "data" / "lighter_rwa_raw" / "145_orderBookDetails.json",
    159: ROOT / "lab" / "data" / "lighter_rwa_raw" / "159_orderBookDetails.json",
}
OLD_MATRIX = ROOT / "lab" / "data" / "lighter_rwa_instrument_matrix.json"
MARKETS = {145: "WTI", 159: "BRENTOIL"}
# Fields that define whether an order can be placed at all (contract-level).
CONTRACT_FIELDS = {
    "market_type", "status", "multiplier", "min_base_amount", "min_quote_amount",
    "order_quote_limit", "supported_size_decimals", "supported_price_decimals",
    "supported_quote_decimals", "maker_fee", "taker_fee", "liquidation_fee",
    "default_initial_margin_fraction", "min_initial_margin_fraction",
    "maintenance_margin_fraction", "closeout_margin_fraction",
    "base_interest_rate", "funding_premium_multiplier",
    "funding_clamp_small", "funding_clamp_big",
}
# Fields that describe live market state (opportunity-level).
STATE_FIELDS = {
    "mark_price", "index_price", "last_trade_price", "daily_base_token_volume",
    "daily_quote_token_volume", "daily_trades_count", "daily_price_low",
    "daily_price_high", "daily_price_change", "open_interest",
}


def iso_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def fetch(path: str, params: dict[str, object], name: str) -> dict[str, object]:
    url = f"{BASE}{path}?{urlencode(params)}"
    started_ms = int(time.time() * 1000)
    status: int | None = None
    error: str | None = None
    payload = b""
    try:
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "monte-rwa-research/1.0"},
        )
        with urlopen(request, timeout=90) as response:
            status = int(response.status)
            payload = response.read()
    except HTTPError as exc:
        status = int(exc.code)
        payload = exc.read()
        error = f"HTTPError: {exc.reason}"
    except (URLError, TimeoutError, OSError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    received_ms = int(time.time() * 1000)

    target = RAW_OUT / f"{name}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return {
        "name": name,
        "endpoint": url,
        "path": path,
        "params": params,
        "http_status": status,
        "error": error,
        "request_started_at": iso_ms(started_ms),
        "received_at": iso_ms(received_ms),
        "latency_ms": received_ms - started_ms,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "raw_file": target.relative_to(ROOT).as_posix(),
    }


def capture() -> list[dict[str, object]]:
    records = []
    records.append(fetch("/api/v1/orderBooks", {}, "orderBooks"))
    records.append(fetch("/api/v1/orderBookDetails", {"market_id": 145}, "orderBookDetails_145"))
    records.append(fetch("/api/v1/orderBookDetails", {"market_id": 159}, "orderBookDetails_159"))
    manifest = {
        "schema": "day9-parameter-capture-v1",
        "captured_at": iso_ms(int(time.time() * 1000)),
        "read_only": True,
        "records": records,
    }
    (RAW_OUT / "day9_capture_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    )
    return records


def load_details(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "order_book_details" in data:
        return data["order_book_details"][0]
    return data


def diff_parameters() -> dict[str, Any]:
    diff: dict[str, Any] = {}
    for market_id, old_path in OLD_DETAILS.items():
        symbol = MARKETS[market_id]
        new_data = load_details(RAW_OUT / f"orderBookDetails_{market_id}.json")
        old_data = load_details(old_path)
        rows: list[dict[str, Any]] = []
        for key in sorted(set(old_data) | set(new_data)):
            old_val = old_data.get(key)
            new_val = new_data.get(key)
            if key in ("daily_chart", "market_config"):
                continue
            if old_val == new_val:
                continue
            category = "contract" if key in CONTRACT_FIELDS else "state" if key in STATE_FIELDS else "other"
            rows.append({
                "field": key,
                "category": category,
                "old_value": old_val,
                "new_value": new_val,
            })
        diff[symbol] = {
            "market_id": market_id,
            "changed_fields": rows,
            "contract_changed": [r for r in rows if r["category"] == "contract"],
            "state_changed": [r for r in rows if r["category"] == "state"],
            "old_snapshot_file": old_path.relative_to(ROOT).as_posix(),
            "new_snapshot_file": f"lab/data/day9_raw/orderBookDetails_{market_id}.json",
        }
    summary: dict[str, Any] = {
        "schema": "day9-parameter-diff-v1",
        "generated_at": iso_ms(int(time.time() * 1000)),
        "markets": diff,
    }
    DIFF_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary


def main() -> int:
    records = capture()
    summary = diff_parameters()
    markets: dict[str, Any] = summary["markets"]
    print(json.dumps({
        "captures": [{r["name"]: r["http_status"]} for r in records],
        "diff": {
            s: {
                "contract_changed": len(m["contract_changed"]),
                "state_changed": len(m["state_changed"]),
                "other_changed": len(m["changed_fields"]) - len(m["contract_changed"]) - len(m["state_changed"]),
            }
            for s, m in markets.items()
        },
        "diff_file": str(DIFF_OUT.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
