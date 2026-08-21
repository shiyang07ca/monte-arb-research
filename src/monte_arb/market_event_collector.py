"""Append-only continuous WebSocket capture for Lighter and Hyperliquid.

Protocol facts verified against first-party sources (2026-08-20):

- Hyperliquid: ``wss://api.hyperliquid.xyz/ws``; subscribe envelope
  ``{"method":"subscribe","subscription":{...}}``; client sends ``{"method":"ping"}``
  and expects ``{"channel":"pong"}``. Channels used: ``l2Book``, ``trades``,
  ``activeAssetCtx`` (mark/oracle/funding context). Source: hyperliquid-python-sdk
  websocket_manager.py.

- Lighter: ``wss://mainnet.zklighter.elliot.ai/stream?encoding=json`` (JSON frames
  required); after ``{"type":"connected"}`` send
  ``{"type":"subscribe","channel":"order_book/{market_id}"}``; server pings with
  ``{"type":"ping"}`` (reply ``{"type":"pong"}``); initial snapshot arrives as
  ``subscribed/order_book``, subsequent updates as ``update/order_book``.
  Source: elliottech/lighter-python paper_client/live.py.

Storage: one gzip JSONL per venue under ``research/raw/day15/<session>/``; every run
creates a fresh session directory, so restart never overwrites earlier events.
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from .market import MarketIdentity

HL_WS_URL = "wss://api.hyperliquid.xyz/ws"
LIGHTER_WS_URL = "wss://mainnet.zklighter.elliot.ai/stream?encoding=json"

LIGHTER_TARGETS: tuple[MarketIdentity, ...] = (
    MarketIdentity("lighter", "perp", "default", "WTI", "145"),
    MarketIdentity("lighter", "perp", "default", "BRENTOIL", "159"),
)
HL_TARGETS: tuple[MarketIdentity, ...] = (
    MarketIdentity("hyperliquid", "perp", "xyz", "xyz:CL", "110029"),
    MarketIdentity("hyperliquid", "perp", "xyz", "xyz:BRENTOIL", "110049"),
)

SCHEMA = "day15-continuous-events-v1"


# ---------------------------------------------------------------------------
# Parsers (pure functions; unit-tested without network)
# ---------------------------------------------------------------------------

def _row_to_pair(row: Any) -> list[str]:
    if isinstance(row, Mapping):
        # Hyperliquid rows use px/sz; Lighter REST rows use price/remaining_base_amount.
        px = row.get("px", row.get("price"))
        sz = row.get("sz", row.get("remaining_base_amount", row.get("size")))
        if px is None or sz is None:
            raise ValueError("unrecognized book row shape")
        return [str(px), str(sz)]
    if isinstance(row, (list, tuple)) and len(row) >= 2:
        return [str(row[0]), str(row[1])]
    raise ValueError("unrecognized book row shape")


def _levels_to_pairs(rows: Any, field_name: str) -> list[list[str]]:
    if not isinstance(rows, list):
        raise ValueError(f"{field_name} must be a list")
    return [_row_to_pair(r) for r in rows]


def parse_hl_l2(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a Hyperliquid ``l2Book`` WS payload to a book event dict."""
    levels = payload.get("levels")
    if not isinstance(levels, list) or len(levels) != 2:
        raise ValueError("l2Book requires two side arrays")
    sides = payload.get("sides")
    if isinstance(sides, list) and len(sides) == 2 and sides[0] == "asks":
        asks, bids = levels
    else:
        bids, asks = levels  # legacy order: bids first
    source_time = payload.get("time")
    return {
        "ts_ms": source_time if isinstance(source_time, int) else None,
        "bids": _levels_to_pairs(bids, "bids"),
        "asks": _levels_to_pairs(asks, "asks"),
    }


def parse_hl_trades(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Normalize a Hyperliquid ``trades`` WS payload into trade event dicts."""
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ValueError("trades data must be a list")
    out = []
    for row in rows:
        if not isinstance(row, Mapping) or "px" not in row or "sz" not in row:
            raise ValueError("malformed trade row")
        out.append(
            {
                "ts_ms": row.get("time") if isinstance(row.get("time"), int) else None,
                "side": row.get("side"),
                "px": str(row["px"]),
                "sz": str(row["sz"]),
                "tid": row.get("tid"),
            }
        )
    return out


def parse_hl_ctx(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a Hyperliquid ``activeAssetCtx`` payload (mark/oracle/funding)."""
    data: Any = payload.get("data")
    ctx = data.get("ctx") if isinstance(data, Mapping) else None
    if not isinstance(ctx, Mapping):
        raise ValueError("activeAssetCtx requires data.ctx")
    keep = {
        "markPx": "mark_px",
        "oraclePx": "oracle_px",
        "funding": "funding",
        "premium": "premium",
        "openInterest": "open_interest",
        "dayNtlVlm": "day_ntl_vlm",
    }
    out: dict[str, Any] = {}
    if isinstance(data.get("time"), int):
        out["ts_ms"] = data["time"]
    for source_key, target_key in keep.items():
        if source_key in ctx:
            out[target_key] = str(ctx[source_key])
    return out


def parse_lighter_book(message: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a Lighter ``subscribed/order_book`` or ``update/order_book`` message.

    Verified live shape (2026-08-20): message-level ``timestamp`` (ms),
    ``order_book`` rows are ``{"price": ..., "size": ...}``, and the channel
    uses a colon separator (``order_book:145``).
    """
    book = message.get("order_book")
    if not isinstance(book, Mapping):
        raise ValueError("order_book message missing payload")
    bids = book.get("bids")
    asks = book.get("asks")
    if not isinstance(bids, list) or not isinstance(asks, list):
        raise ValueError("order_book requires bids and asks")
    source_time = message.get("timestamp")
    return {
        "ts_ms": source_time if isinstance(source_time, (int, float)) else None,
        "bids": _levels_to_pairs(bids, "bids"),
        "asks": _levels_to_pairs(asks, "asks"),
        "nonce": book.get("nonce"),
        "offset": book.get("offset"),
    }


# ---------------------------------------------------------------------------
# Append-only writers
# ---------------------------------------------------------------------------

class JsonlGzWriter:
    """Append-only gzip JSONL sink; never truncates an existing file."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = gzip.open(path, "at", encoding="utf-8")
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def write(self, record: Mapping[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        self._fh.write(line)
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


@dataclass
class CaptureSession:
    session_id: str
    out_dir: Path
    started_ns: int
    events: dict[str, JsonlGzWriter] = field(default_factory=dict)
    health: Optional[JsonlGzWriter] = None
    counters: dict[str, dict[str, dict[str, int]]] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def bump(self, venue: str, market: str, kind: str) -> None:
        by_market = self.counters.setdefault(venue, {})
        by_kind = by_market.setdefault(market, {})
        by_kind[kind] = by_kind.get(kind, 0) + 1

    def write_event(
        self, venue: str, market: str, kind: str, payload: Mapping[str, Any]
    ) -> None:
        writer = self.events.get(venue)
        if writer is None:
            return
        writer.write(
            {
                "schema": SCHEMA,
                "session": self.session_id,
                "recv_ns": time.time_ns(),
                "venue": venue,
                "kind": kind,
                "market": market,
                "payload": payload,
            }
        )
        self.bump(venue, market, kind)

    def write_health(self, venue: str, kind: str, detail: Mapping[str, Any]) -> None:
        if self.health is None:
            return
        self.health.write(
            {
                "schema": SCHEMA,
                "session": self.session_id,
                "at_ns": time.time_ns(),
                "venue": venue,
                "kind": kind,
                **detail,
            }
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_session(out_root: Path) -> CaptureSession:
    session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = out_root / session_id
    session = CaptureSession(session_id=session_id, out_dir=out_dir, started_ns=time.time_ns())
    session.events["hyperliquid"] = JsonlGzWriter(out_dir / "events_hyperliquid.jsonl.gz")
    session.events["lighter"] = JsonlGzWriter(out_dir / "events_lighter.jsonl.gz")
    session.health = JsonlGzWriter(out_dir / "health.jsonl.gz")
    return session


# ---------------------------------------------------------------------------
# Venue loops
# ---------------------------------------------------------------------------

async def _ping_loop(ws: Any, session: CaptureSession, interval_s: float) -> None:
    try:
        while True:
            await asyncio.sleep(interval_s)
            await ws.send(json.dumps({"method": "ping"}))
    except asyncio.CancelledError:
        raise
    except Exception:
        return


async def run_hyperliquid(
    session: CaptureSession,
    stop_event: asyncio.Event,
    silent_s: float,
    ping_s: float = 30.0,
) -> None:
    import websockets.asyncio.client

    subscriptions = []
    for identity in HL_TARGETS:
        subscriptions += [
            {"type": "l2Book", "coin": identity.symbol},
            {"type": "trades", "coin": identity.symbol},
            {"type": "activeAssetCtx", "coin": identity.symbol},
        ]
    backoff = 2.0
    while not stop_event.is_set():
        try:
            async with websockets.asyncio.client.connect(HL_WS_URL, max_size=None) as ws:
                session.write_health("hyperliquid", "CONNECTED", {"url": HL_WS_URL})
                for sub in subscriptions:
                    await ws.send(json.dumps({"method": "subscribe", "subscription": sub}))
                ping_task = asyncio.create_task(_ping_loop(ws, session, ping_s))
                silent_reported = False
                try:
                    while not stop_event.is_set():
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=silent_s)
                        except asyncio.TimeoutError:
                            if not silent_reported:
                                session.write_health(
                                    "hyperliquid",
                                    "SILENT_GAP",
                                    {"silent_s": silent_s},
                                )
                                silent_reported = True
                            continue
                        silent_reported = False
                        try:
                            message = json.loads(raw)
                        except json.JSONDecodeError:
                            session.write_health(
                                "hyperliquid", "PARSE_ERROR", {"detail": "invalid JSON frame"}
                            )
                            continue
                        channel = message.get("channel")
                        data = message.get("data")
                        if channel == "pong":
                            continue
                        if not isinstance(data, Mapping):
                            continue
                        coin = str(data.get("coin", "?"))
                        try:
                            if channel == "l2Book":
                                session.write_event(
                                    "hyperliquid", coin, "book", parse_hl_l2(data)
                                )
                            elif channel == "trades":
                                for trade in parse_hl_trades(message):
                                    session.write_event("hyperliquid", coin, "trade", trade)
                            elif channel == "activeAssetCtx":
                                session.write_event(
                                    "hyperliquid", coin, "ctx", parse_hl_ctx(message)
                                )
                        except ValueError as exc:
                            session.write_health(
                                "hyperliquid",
                                "PARSE_ERROR",
                                {"channel": channel, "coin": coin, "detail": str(exc)},
                            )
                finally:
                    ping_task.cancel()
                session.write_health("hyperliquid", "DISCONNECTED", {"clean": True})
        except Exception as exc:  # noqa: BLE001 - connection-level retry
            session.errors.append(
                {"venue": "hyperliquid", "kind": "CONN_ERROR", "detail": str(exc)}
            )
            session.write_health(
                "hyperliquid", "CONN_ERROR", {"detail": str(exc)[:300]}
            )
        if stop_event.is_set():
            break
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30.0)


async def run_lighter(
    session: CaptureSession,
    stop_event: asyncio.Event,
    silent_s: float,
) -> None:
    import websockets.asyncio.client

    backoff = 2.0
    while not stop_event.is_set():
        try:
            async with websockets.asyncio.client.connect(LIGHTER_WS_URL, max_size=None) as ws:
                session.write_health("lighter", "CONNECTED", {"url": LIGHTER_WS_URL})
                subscribed: set[str] = set()
                silent_reported = False
                while not stop_event.is_set():
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=silent_s)
                    except asyncio.TimeoutError:
                        if not silent_reported:
                            session.write_health(
                                "lighter", "SILENT_GAP", {"silent_s": silent_s}
                            )
                            silent_reported = True
                        continue
                    silent_reported = False
                    try:
                        message = json.loads(raw)
                    except json.JSONDecodeError:
                        session.write_health(
                            "lighter", "PARSE_ERROR", {"detail": "invalid JSON frame"}
                        )
                        continue
                    message_type = message.get("type")
                    if message_type == "connected":
                        for identity in LIGHTER_TARGETS:
                            channel = f"order_book/{identity.local_id}"
                            await ws.send(
                                json.dumps({"type": "subscribe", "channel": channel})
                            )
                            subscribed.add(channel)
                        continue
                    if message_type == "ping":
                        await ws.send(json.dumps({"type": "pong"}))
                        continue
                    if message_type not in ("subscribed/order_book", "update/order_book"):
                        continue
                    channel = str(message.get("channel", ""))
                    market_id = "?"
                    for separator in (":", "/"):
                        prefix = f"order_book{separator}"
                        if channel.startswith(prefix):
                            market_id = channel[len(prefix):]
                            break
                    try:
                        session.write_event(
                            "lighter",
                            market_id,
                            "book",
                            {
                                **parse_lighter_book(message),
                                "is_snapshot": message_type == "subscribed/order_book",
                            },
                        )
                    except ValueError as exc:
                        session.write_health(
                            "lighter",
                            "PARSE_ERROR",
                            {"channel": channel, "detail": str(exc)},
                        )
                session.write_health("lighter", "DISCONNECTED", {"clean": True})
        except Exception as exc:  # noqa: BLE001 - connection-level retry
            session.errors.append(
                {"venue": "lighter", "kind": "CONN_ERROR", "detail": str(exc)}
            )
            session.write_health("lighter", "CONN_ERROR", {"detail": str(exc)[:300]})
        if stop_event.is_set():
            break
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30.0)


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

def _write_session_json(session: CaptureSession, duration_s: float) -> None:
    payload = {
        "schema": SCHEMA,
        "session_id": session.session_id,
        "started_at_utc": _utc_now(),
        "duration_s": duration_s,
        "read_only": True,
        "execution_client_present": False,
        "targets": {
            "lighter": [identity.to_dict() for identity in LIGHTER_TARGETS],
            "hyperliquid": [identity.to_dict() for identity in HL_TARGETS],
        },
        "counters": session.counters,
        "errors": session.errors,
        "notes": [
            "Events are stored as received (JSON frames) with local recv_ns; "
            "exchange timestamps kept separately as ts_ms where the venue provides them.",
            "Lighter order_book rows are normalized to [px, sz] pairs; the venue does "
            "not provide a book snapshot source time in the WS stream.",
            "A fresh session directory is created per run; nothing is overwritten.",
        ],
        "boundary": (
            "Public market data capture only. No order submission, no signature, "
            "no PnL. Continuous L2/BBO does not by itself prove opportunity duration; "
            "baseline and anomaly windows are computed in market_event_analysis.py."
        ),
    }
    (session.out_dir / "session.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    )


async def _capture(duration_s: float, out_root: Path, silent_s: float) -> int:
    session = new_session(out_root)
    stop_event = asyncio.Event()
    tasks = [
        asyncio.create_task(run_hyperliquid(session, stop_event, silent_s)),
        asyncio.create_task(run_lighter(session, stop_event, silent_s)),
    ]
    try:
        await asyncio.sleep(duration_s)
    finally:
        stop_event.set()
        await asyncio.gather(*tasks, return_exceptions=True)
    for writer in session.events.values():
        writer.close()
    if session.health is not None:
        session.health.close()
    _write_session_json(session, duration_s)
    total = sum(
        count
        for by_market in session.counters.values()
        for by_kind in by_market.values()
        for count in by_kind.values()
    )
    print(
        json.dumps(
            {
                "session": session.session_id,
                "out_dir": str(session.out_dir),
                "total_events": total,
                "errors": len(session.errors),
                "counters": session.counters,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Day15 continuous WS capture (Lighter + Hyperliquid public feeds)"
    )
    parser.add_argument("--duration", type=float, default=600.0)
    parser.add_argument(
        "--out", type=Path, default=Path("research/raw/day15")
    )
    parser.add_argument("--silent-s", type=float, default=30.0)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return asyncio.run(_capture(args.duration, args.out, args.silent_s))


if __name__ == "__main__":
    raise SystemExit(main())
