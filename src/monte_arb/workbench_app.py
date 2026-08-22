"""Read-only workbench HTTP application for candidates and execution costs.

Public seam: WorkbenchApp over in-memory snapshots with an optional live scanner.
All data is read-only; no execution client and no orders.
"""

from __future__ import annotations

import json
import math
import threading
from http.server import BaseHTTPRequestHandler
from typing import Any, Callable, Mapping, Optional, Sequence
from urllib.parse import parse_qs, urlsplit

from .candidate_workbench import CandidateSnapshot, SnapshotItem
from .oil_relative_value import export_source_csv
from .research_console_views import (
    render_dashboard_html,
    render_data_html,
    render_oil_html,
    render_placeholder_html,
)
from .workbench_views import render_candidate_html, render_execution_html



class WorkbenchHandler(BaseHTTPRequestHandler):
    app: "WorkbenchApp"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        request_url = urlsplit(self.path)
        path = request_url.path
        if path in ("/", "/workbench", "/workbench/"):
            if self.app.oil is not None:
                self._send(
                    200,
                    render_dashboard_html(self.app.oil).encode("utf-8"),
                    "text/html; charset=utf-8",
                )
            elif self.app.snapshot is not None:
                self._send(200, render_candidate_html(self.app.snapshot).encode("utf-8"), "text/html; charset=utf-8")
            else:
                self._send(200, render_execution_html().encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/workbench/candidates":
            if self.app.snapshot is None:
                self._send(404, b"candidate snapshot not loaded", "text/plain; charset=utf-8")
                return
            self._send(
                200,
                render_candidate_html(self.app.snapshot).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return
        if path in ("/workbench/api/candidates", "/api/candidates"):
            if self.app.snapshot is None:
                self._send(404, b"candidate snapshot not loaded", "text/plain; charset=utf-8")
                return
            self._send(
                200,
                json.dumps(self.app.snapshot.to_dict(), ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8",
            )
            return
        if path == "/workbench/execution":
            self._send(200, render_execution_html().encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/workbench/oil":
            if self.app.oil is None:
                self._send(404, b"oil projection not loaded", "text/plain; charset=utf-8")
                return
            self._send(
                200,
                render_oil_html().encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return
        if path == "/workbench/data":
            if self.app.oil is None:
                self._send(404, b"oil projection not loaded", "text/plain; charset=utf-8")
                return
            self._send(
                200,
                render_data_html(self.app.oil).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return
        placeholders = {
            "/workbench/markets": (
                "markets",
                "全市场 Screener",
                "按同标的跨场所、跨标的相对价值和 funding 三种研究视图浏览市场。",
            ),
            "/workbench/funding": (
                "funding",
                "Funding",
                "保留原生结算间隔，比较跨场所 funding，并累计真实历史现金流。",
            ),
            "/workbench/tools/spread": (
                "tools",
                "Spread Grapher",
                "从 Brent–WTI 模块抽出成熟的同步、权重和图表接口后，再开放任意两腿配置。",
            ),
        }
        if path in placeholders:
            active, title, description = placeholders[path]
            self._send(
                200,
                render_placeholder_html(active, title, description).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return
        if path in ("/workbench/api/oil", "/api/oil"):
            if self.app.oil is None:
                self._send(404, b"oil projection not loaded", "text/plain; charset=utf-8")
                return
            self._send(
                200,
                json.dumps(self.app.oil, ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8",
            )
            return
        if path == "/workbench/api/oil.csv":
            if self.app.oil is None:
                self._send(404, b"oil projection not loaded", "text/plain; charset=utf-8")
                return
            source = parse_qs(request_url.query).get("source", [""])[0]
            try:
                body = export_source_csv(self.app.oil, source).encode("utf-8")
            except KeyError:
                self._send(404, b"unknown oil source", "text/plain; charset=utf-8")
                return
            self._send(200, body, "text/csv; charset=utf-8")
            return
        if path == "/workbench/api/execution":
            if self.app.execution is None:
                self._send(404, b"execution snapshot not loaded", "text/plain; charset=utf-8")
                return
            execution = self.app.execution
            self._send(
                200,
                json.dumps(execution.to_dict(), ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8",
            )
            return
        if path == "/workbench/api/execution/compute":
            self._send(405, b"use POST", "text/plain; charset=utf-8")
            return
        self._send(404, b"", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/workbench/api/refresh":
            if self.app.scanner is None:
                self._send(409, b"no live scanner configured", "text/plain; charset=utf-8")
                return
            try:
                self.app.refresh()
            except Exception as exc:  # noqa: BLE001 - surface scanner failure to the page
                self._send(500, str(exc).encode("utf-8", errors="replace"), "text/plain; charset=utf-8")
                return
            execution = self.app.execution
            if execution is None:
                self._send(500, b"scanner produced no snapshot", "text/plain; charset=utf-8")
                return
            self._send(
                200,
                json.dumps(execution.to_dict(), ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8",
            )
            return
        if path == "/workbench/api/execution/compute":
            if self.app.execution is None:
                self._send(404, b"execution snapshot not loaded", "text/plain; charset=utf-8")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send(400, b"bad Content-Length", "text/plain; charset=utf-8")
                return
            if length < 0 or length > 4096:
                self._send(413, b"request body too large", "text/plain; charset=utf-8")
                return
            try:
                raw = self.rfile.read(length) if length else b"{}"
                size = float(json.loads(raw or b"{}").get("size_usd", 0))
            except (TypeError, ValueError, json.JSONDecodeError):
                self._send(400, b"bad size_usd", "text/plain; charset=utf-8")
                return
            if not math.isfinite(size) or size <= 0 or size > 10_000_000:
                self._send(400, b"size_usd must be finite and in (0, 10000000]", "text/plain; charset=utf-8")
                return
            body = self.app.compute_custom_size(size)
            self._send(
                200,
                json.dumps(body, ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8",
            )
            return
        self._send(404, b"", "text/plain; charset=utf-8")

    def log_message(self, format: str, *args: object) -> None:
        return


class WorkbenchApp:
    """In-memory workbench holding candidate and/or execution snapshots.

    snapshot: CandidateSnapshot (candidate mode).
    execution: ExecutionSnapshot (execution mode; also detected when
        snapshot carries a `pairs` attribute).
    scanner: optional callable returning a fresh ExecutionSnapshot; used by
        GET /workbench/api/execution (mtime-based reload) and POST refresh.
    """

    def __init__(
        self,
        snapshot: Optional[Any] = None,
        *,
        execution: Optional[Any] = None,
        oil: Optional[Mapping[str, Any]] = None,
        scanner: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.snapshot: Optional[CandidateSnapshot] = None
        self.execution: Optional[Any] = None
        if snapshot is not None and hasattr(snapshot, "pairs"):
            self.execution = snapshot
        elif snapshot is not None:
            self.snapshot = snapshot
        if execution is not None:
            self.execution = execution
        self.oil = dict(oil) if oil is not None else None
        self.scanner = scanner
        self._lock = threading.Lock()
        self.last_scan_error: Optional[str] = None

    def refresh(self) -> None:
        if self.scanner is None:
            raise RuntimeError("live scanner is not configured")
        with self._lock:
            try:
                fresh = self.scanner()
            except Exception as exc:  # noqa: BLE001 - preserve prior snapshot, surface failure
                self.last_scan_error = str(exc)
                raise
            if fresh is None:
                self.last_scan_error = "scanner returned no snapshot"
                raise RuntimeError(self.last_scan_error)
            self.execution = fresh
            self.last_scan_error = None

    def compute_custom_size(self, size_usd: float) -> dict[str, Any]:
        from decimal import Decimal

        from .execution_engine import pair_execution, round_trip_execution

        if self.execution is None:
            raise RuntimeError("execution snapshot not loaded")
        rows: dict[str, Any] = {}
        for pair in self.execution.pairs:
            per_direction: dict[str, Any] = {}
            for direction in ("buy_left_sell_right", "buy_right_sell_left"):
                result = pair_execution(
                    pair.left_spec,
                    pair.left_book,
                    pair.right_spec,
                    pair.right_book,
                    direction=direction,
                    target_notional_usd=Decimal(str(size_usd)),
                )
                round_trip = round_trip_execution(
                    pair.left_spec,
                    pair.left_book,
                    pair.right_spec,
                    pair.right_book,
                    direction=direction,
                    target_notional_usd=Decimal(str(size_usd)),
                )
                row = result.to_dict()
                row["round_trip"] = round_trip.to_dict()
                per_direction[direction] = row
            rows[pair.pair_name] = per_direction
        return {"size_usd": size_usd, "pairs": rows}

    def make_handler(self) -> type[BaseHTTPRequestHandler]:
        app_ref = self

        class BoundHandler(WorkbenchHandler):
            app = app_ref

        return BoundHandler


def main(argv: Optional[Sequence[str]] = None) -> None:
    import argparse
    from http.server import ThreadingHTTPServer
    from pathlib import Path

    parser = argparse.ArgumentParser(
        prog="python3 -m monte_arb.workbench_app",
        description="Serve candidate and execution views for the read-only research workbench.",
    )
    parser.add_argument("--snapshot", type=Path, default=None)
    parser.add_argument("--execution", type=Path, default=None)
    parser.add_argument(
        "--oil",
        type=Path,
        default=None,
        help="oil-relative-value-v1 research projection JSON",
    )
    parser.add_argument("--port", type=int, default=18768)
    parser.add_argument("--live-refresh", action="store_true")
    parser.add_argument("--rescan-seconds", type=float, default=0.0)
    args = parser.parse_args(argv)
    if args.snapshot is None and args.execution is None and args.oil is None:
        raise SystemExit(
            "--oil <oil-relative-value.json>, --snapshot <day14-scan.json>, "
            "or --execution <day16-scan.json> is required"
        )

    snapshot = None
    execution = None
    oil = None
    scanner: Optional[Callable[[], Any]] = None
    if args.snapshot is not None:
        import json as _json

        payload = _json.loads(args.snapshot.read_text())
        from .candidate_workbench import CandidateSnapshot as _CS

        snapshot = _CS(
            schema=payload["schema"],
            observed_at=payload["observed_at"],
            scanned_at=payload["scanned_at"],
            read_only=payload["read_only"],
            execution_client_present=payload["execution_client_present"],
            markets=tuple(_market_from_dict(m) for m in payload["markets"]),
            candidates=tuple(_candidate_from_dict(c) for c in payload["candidates"]),
            request_errors=tuple(
                (row["selector"], row["reason_code"]) for row in payload["request_errors"]
            ),
            boundaries=tuple(payload["boundaries"]),
        )
    if args.execution is not None:
        from .execution_engine import load_snapshot

        execution = load_snapshot(args.execution)

        if args.live_refresh:
            from .execution_engine import build_parser as _build_execution_parser
            from .execution_engine import run_execution_scan

            def _scanner() -> Any:
                scan_args = _build_execution_parser().parse_args([])
                scan_args.output = str(args.execution)
                scan_args.sizes = execution.sizes_usd
                exit_code = run_execution_scan(scan_args)
                if exit_code != 0:
                    raise RuntimeError(
                        f"live scan incomplete (exit code {exit_code}); last good snapshot preserved"
                    )
                return load_snapshot(args.execution)

            scanner = _scanner

    if args.oil is not None:
        loaded_oil = json.loads(args.oil.read_text(encoding="utf-8"))
        if not isinstance(loaded_oil, Mapping) or loaded_oil.get("schema") != "oil-relative-value-v1":
            raise SystemExit("--oil must contain schema=oil-relative-value-v1")
        oil = loaded_oil

    app = WorkbenchApp(snapshot, execution=execution, oil=oil, scanner=scanner)
    if args.rescan_seconds > 0:
        if scanner is None:
            raise SystemExit("--rescan-seconds requires --live-refresh")
        import time as _time

        def _rescan_loop() -> None:
            while True:
                _time.sleep(args.rescan_seconds)
                try:
                    app.refresh()
                except Exception as exc:  # noqa: BLE001 - keep scheduler alive
                    print(f"background market rescan failed: {exc}")

        threading.Thread(target=_rescan_loop, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), app.make_handler())
    print(f"workbench http://127.0.0.1:{args.port}/workbench")
    if args.oil is not None:
        print(f"oil view http://127.0.0.1:{args.port}/workbench/oil")
    if args.execution is not None:
        print(f"execution view http://127.0.0.1:{args.port}/workbench/execution")
    server.serve_forever()


def _market_from_dict(payload: dict) -> Any:
    from .market import MarketIdentity

    identity = MarketIdentity(**payload["identity"])
    quote = payload.get("quote")
    return SnapshotItem(
        identity=identity,
        catalog_status=payload["catalog_status"],
        book_status=payload["book_status"],
        quote=_quote_from_dict(identity, quote) if quote else None,
        funding=None,
        source_time_ms=payload.get("source_time_ms"),
        receive_skew_ms=payload.get("receive_skew_ms", 0.0),
        reason_codes=tuple(payload.get("reason_codes", [])),
    )


def _quote_from_dict(identity: Any, payload: dict) -> Any:
    from .candidate_workbench import BookQuote

    return BookQuote(
        identity=identity,
        best_bid=payload["best_bid"],
        best_ask=payload["best_ask"],
        bid_size=payload["bid_size"],
        ask_size=payload["ask_size"],
        source_time_ms=payload.get("source_time_ms"),
    )


def _candidate_from_dict(payload: dict) -> Any:
    from .candidate_workbench import Candidate

    return Candidate(
        pair_name=payload["pair_name"],
        left=_market_from_dict(payload["left"]),
        right=_market_from_dict(payload["right"]),
        executable_spread_bps=payload["executable_spread_bps"],
        depth_mismatch=payload["depth_mismatch"],
        funding_diff_bps=payload["funding_diff_bps"],
        funding_divergent=payload["funding_divergent"],
        liquidity_asymmetry=payload["liquidity_asymmetry"],
        reference_dislocation=payload["reference_dislocation"],
        data_quality_issues=tuple(payload["data_quality_issues"]),
        reasons=tuple(payload["reasons"]),
        trade_rank=payload["trade_rank"],
        research_rank=payload["research_rank"],
        direction=payload["direction"],
        evidence=tuple(payload["evidence"]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
