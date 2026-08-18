from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from .market import MarketIdentity
from .synchronized_quotes import (
    QuoteObservation,
    SnapshotAttempt,
    build_snapshot,
    classify_pair_sample,
    parse_hyperliquid_book,
    parse_lighter_book,
)

LIGHTER_URL = "https://mainnet.zklighter.elliot.ai/api/v1/orderBookOrders"
HYPERLIQUID_URL = "https://api.hyperliquid.xyz/info"

TARGETS = (
    MarketIdentity("lighter", "perp", "default", "WTI", "145"),
    MarketIdentity("lighter", "perp", "default", "BRENTOIL", "159"),
    MarketIdentity("hyperliquid", "perp", "xyz", "xyz:CL", "110029"),
    MarketIdentity("hyperliquid", "perp", "xyz", "xyz:BRENTOIL", "110049"),
)


@dataclass(frozen=True)
class RawResponse:
    identity: MarketIdentity
    request_started_ns: int
    response_received_ns: int
    http_status: int
    raw: bytes


class PublicCaptureError(RuntimeError):
    pass


def _request(identity: MarketIdentity, timeout: float) -> RawResponse:
    if identity.venue == "lighter":
        url = f"{LIGHTER_URL}?market_id={identity.local_id}&limit=20"
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "monte-arb-day14/1.0"},
            method="GET",
        )
    elif identity.venue == "hyperliquid":
        raw_body = json.dumps(
            {"type": "l2Book", "coin": identity.symbol}, separators=(",", ":")
        ).encode()
        request = urllib.request.Request(
            HYPERLIQUID_URL,
            data=raw_body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "monte-arb-day14/1.0",
            },
            method="POST",
        )
    else:
        raise PublicCaptureError(f"unsupported venue: {identity.venue}")

    started = time.monotonic_ns()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = int(response.status)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PublicCaptureError(str(exc)) from exc
    received = time.monotonic_ns()
    return RawResponse(identity, started, received, status, raw)


async def _capture_one(identity: MarketIdentity, timeout: float) -> RawResponse:
    return await asyncio.to_thread(_request, identity, timeout)


def _parse(response: RawResponse) -> QuoteObservation:
    try:
        payload = json.loads(response.raw)
    except json.JSONDecodeError as exc:
        raise PublicCaptureError("response is not JSON") from exc
    digest = hashlib.sha256(response.raw).hexdigest()
    kwargs = {
        "request_started_ns": response.request_started_ns,
        "response_received_ns": response.response_received_ns,
        "raw_sha256": digest,
    }
    if response.identity.venue == "lighter":
        return parse_lighter_book(response.identity, payload, **kwargs)
    return parse_hyperliquid_book(response.identity, payload, **kwargs)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _append_gzip_jsonl(path: Path, records: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "at", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            stream.write("\n")


async def capture_attempt(timeout: float) -> SnapshotAttempt:
    attempt_id = f"day14-{time.time_ns()}"
    started_at = datetime.now(timezone.utc)
    tasks = [_capture_one(identity, timeout) for identity in TARGETS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    observations = []
    errors = []
    for identity, result in zip(TARGETS, results):
        if isinstance(result, BaseException):
            errors.append((identity.selector, "REQUEST_FAILED"))
            continue
        try:
            observations.append(_parse(result))
        except (ValueError, PublicCaptureError):
            errors.append((identity.selector, "RESPONSE_INVALID"))
    return SnapshotAttempt(attempt_id, started_at, tuple(observations), tuple(errors))


def build_report(attempt: SnapshotAttempt) -> dict[str, Any]:
    snapshot = (
        build_snapshot(attempt.attempt_id, attempt.observations)
        if attempt.observations
        else None
    )
    by_symbol = {item.identity.symbol: item for item in attempt.observations}
    pair_specs = (
        ("WTI", "xyz:CL", "WTI_XYZ_CL"),
        ("BRENTOIL", "xyz:BRENTOIL", "BRENTOIL_XYZ_BRENTOIL"),
    )
    pairs = []
    for left_symbol, right_symbol, name in pair_specs:
        left = by_symbol.get(left_symbol)
        right = by_symbol.get(right_symbol)
        if left is None or right is None:
            pairs.append(
                {
                    "pair": name,
                    "status": "exclude",
                    "reason_codes": ["OBSERVATION_MISSING"],
                }
            )
            continue
        # Day13 established that live contract weights and oracle source states are not
        # exposed by these book snapshots. Keep both unknown rather than inferring them.
        decision = classify_pair_sample(
            left,
            right,
            economic_status="unknown",
            oracle_state_left="unknown",
            oracle_state_right="unknown",
            contract_weight_state="unknown",
            max_receive_skew_ms=1_000,
        )
        pairs.append({"pair": name, **decision.to_dict()})
    return {
        "schema": "day14-synchronized-quote-smoke-v1",
        "captured_at": _utc_now(),
        "read_only": True,
        "execution_client_present": False,
        "attempt": attempt.to_dict(),
        "snapshot": snapshot.to_dict() if snapshot else None,
        "pair_decisions": pairs,
        "boundary": (
            "Book snapshots prove current executable top-of-book observations only. "
            "They do not prove matching contract weights or oracle source state, and "
            "no spread PnL is calculated."
        ),
    }


def run_capture(args: argparse.Namespace) -> int:
    attempt = asyncio.run(capture_attempt(args.timeout))
    report = build_report(attempt)
    _write_json(args.output, report)
    _append_gzip_jsonl(args.raw_output, [attempt.to_dict()])
    print(
        json.dumps(
            {
                "output": str(args.output),
                "raw_output": str(args.raw_output),
                "observations": len(attempt.observations),
                "errors": len(attempt.errors),
                "capture_span_ms": (
                    report["snapshot"]["capture_span_ms"]
                    if report["snapshot"]
                    else None
                ),
                "pair_decisions": report["pair_decisions"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 2 if attempt.errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Day14 public synchronized quote capture"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/runs/day14-smoke-test.json"),
    )
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=Path("research/raw/day14/attempts.jsonl.gz"),
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    return run_capture(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
