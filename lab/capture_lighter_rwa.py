#!/usr/bin/env python3
"""Read-only capture of Lighter WTI/BRENTOIL market data.

The script deliberately stores raw JSON responses and request metadata. It does
not authenticate, create orders, or submit transactions.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = "https://mainnet.zklighter.elliot.ai"
OUT = Path(__file__).resolve().parent / "data" / "lighter_rwa_raw"
MANIFEST = Path(__file__).resolve().parent / "data" / "lighter_rwa_capture_manifest.json"
MARKETS = {145: "WTI", 159: "BRENTOIL"}


def iso_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def fetch(path: str, params: dict[str, object], filename: str) -> dict[str, object]:
    query = urlencode(params)
    url = f"{BASE}{path}?{query}"
    started_ms = int(time.time() * 1000)
    status: int | None = None
    error: str | None = None
    payload = b""
    try:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "monte-rwa-research/1.0",
            },
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

    target = OUT / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    record: dict[str, object] = {
        "endpoint": url,
        "path": path,
        "params": params,
        "http_status": status,
        "request_started_at": iso_ms(started_ms),
        "received_at": iso_ms(received_ms),
        "request_latency_ms": received_ms - started_ms,
        "raw_file": str(target.relative_to(Path(__file__).resolve().parent.parent)),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "error": error,
    }
    return record


def main() -> int:
    now_ms = int(time.time() * 1000)
    records: list[dict[str, object]] = []
    for market_id, symbol in MARKETS.items():
        for resolution, count in (("1h", 500), ("1d", 500)):
            records.append(
                fetch(
                    "/api/v1/candles",
                    {
                        "market_id": market_id,
                        "resolution": resolution,
                        "start_timestamp": 1,
                        "end_timestamp": now_ms,
                        "count_back": count,
                        "set_timestamp_to_end": False,
                    },
                    f"{symbol}_candles_{resolution}.json",
                )
            )
        records.append(
            fetch(
                "/api/v1/fundings",
                {
                    "market_id": market_id,
                    "resolution": "1h",
                    "start_timestamp": 1,
                    "end_timestamp": now_ms,
                    "count_back": 750,
                },
                f"{symbol}_fundings_1h.json",
            )
        )
        records.append(
            fetch(
                "/api/v1/orderBookDetails",
                {"market_id": market_id},
                f"{market_id}_orderBookDetails.json",
            )
        )

    manifest = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "source": "Lighter public API",
        "records": records,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"manifest": str(MANIFEST), "records": records}, ensure_ascii=False, indent=2))
    return 0 if all(r["http_status"] == 200 for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
