"""Day14 workbench v0 HTTP surface: read-only JSON and HTML.

Public seam: WorkbenchApp over an in-memory snapshot. No execution client.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from typing import Any, Optional, Sequence

from .workbench import CandidateSnapshot, SnapshotItem

PAGE_TITLE = "研究工作台 · Day14 v0"
PAGE_CSS = """
:root { color-scheme: light; --ink:#172126; --muted:#5e6a70; --paper:#f6f3ed; --panel:#fffdf8; --line:#d8d2c7; --accent:#006d77; --accent-soft:#dff3f1; --warn:#9b5d00; --warn-soft:#fff1d6; --danger:#a33232; --ok:#2c7047; --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; --sans:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
* { box-sizing: border-box; } body { margin:0; color:var(--ink); background:var(--paper); font-family:var(--sans); line-height:1.65; }
header, main { width:min(1080px, calc(100% - 32px)); margin-inline:auto; } header { padding:48px 0 18px; }
h1 { margin:6px 0 10px; font:700 clamp(1.8rem,4vw,3rem)/1.08 Georgia,serif; letter-spacing:-.03em; }
h2 { margin:26px 0 10px; font:700 clamp(1.2rem,2.5vw,1.7rem)/1.2 Georgia,serif; }
.eyebrow { color:var(--accent); font-weight:800; letter-spacing:.12em; text-transform:uppercase; font-size:.76rem; }
.lede { max-width:820px; color:var(--muted); }
.card { padding:22px; margin:16px 0; border:1px solid var(--line); border-radius:14px; background:var(--panel); }
.metric { font:700 1.8rem/1 var(--mono); margin-top:8px; } .muted { color:var(--muted); } .ok { color:var(--ok); } .warn { color:var(--warn); } .danger { color:var(--danger); }
table { width:100%; border-collapse:collapse; font-size:.92rem; } th,td { padding:9px 8px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
th { color:var(--muted); font-size:.76rem; text-transform:uppercase; letter-spacing:.05em; }
pre { overflow-x:auto; padding:16px; background:#152126; color:#eaf5f2; border-radius:10px; line-height:1.5; font-size:.88rem; }
code { font-family:var(--mono); background:#eeece5; padding:.12em .35em; border-radius:4px; }
a { color:var(--accent); } .pill { display:inline-block; border:1px solid var(--line); border-radius:999px; padding:4px 10px; background:var(--panel); font-size:.82rem; margin:2px 4px 2px 0; }
.boundary { border-left:4px solid var(--warn); background:var(--warn-soft); padding:14px 16px; border-radius:0 8px 8px 0; }
"""


def _fmt(value: Optional[Any], suffix: str = "") -> str:
    if value is None:
        return "not_computed"
    return f"{value}{suffix}"


def render_html(snapshot: CandidateSnapshot) -> str:
    candidates = snapshot.candidates[:3]
    rows = []
    for candidate in candidates:
        left = candidate.left.quote
        right = candidate.right.quote
        issues = ", ".join(candidate.data_quality_issues) or "none"
        rows.append(
            f"<tr>"
            f"<td><code>{candidate.pair_name}</code></td>"
            f"<td>{_fmt(candidate.executable_spread_bps, ' bps')}</td>"
            f"<td>{_fmt(left.best_bid if left else None)} / {_fmt(left.best_ask if left else None)}</td>"
            f"<td>{_fmt(right.best_bid if right else None)} / {_fmt(right.best_ask if right else None)}</td>"
            f"<td>{candidate.direction}</td>"
            f"<td>{issues}</td>"
            f"</tr>"
        )
    table = (
        "<table><thead><tr><th>pair</th><th>executable spread</th><th>Lighter bid/ask</th>"
        "<th>Hyperliquid bid/ask</th><th>direction</th><th>data quality</th></tr></thead>"
        f"<tbody>{''.join(rows) if rows else '<tr><td colspan=6>No candidates this scan.</td></tr>'}</tbody></table>"
    )
    boundary = (
        "<div class='boundary'><strong>研究边界：</strong>"
        "当前快照只证明可成交的 top-of-book 观察，不证明合约权重或 oracle 来源状态；"
        "不计算费用、资金费现金流、滑点或价差盈亏；交易榜与研究榜只是研究优先级，不是交易信号。</div>"
    )
    return f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{PAGE_TITLE}</title><style>{PAGE_CSS}</style></head>
<body><header><div class="eyebrow">MonteLab · Read-only Workbench</div>
<h1>{PAGE_TITLE}</h1><p class="lede">扫描 Lighter–Hyperliquid 全部可映射永续，只保留当前快照可计算的证据。最多展示 3 个候选；不足时不凑数。</p></header>
<main>
<div class="card"><span class="pill">read_only</span><span class="pill">execution_client_present=false</span>
<span class="pill">schema={snapshot.schema}</span><span class="pill">observed_at={snapshot.observed_at}</span>
<div class="metric">{len(snapshot.candidates)} 候选 / {len(snapshot.markets)} 市场</div></div>
{boundary}
<h2>交易吸引力榜（当前快照）</h2><div class="card">{table}</div>
<h2>原始候选 JSON</h2><div class="card"><pre>{json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2)}</pre></div>
</main></body></html>"""


class WorkbenchHandler(BaseHTTPRequestHandler):
    app: "WorkbenchApp"

    def do_GET(self) -> None:
        if self.path in ("/", "/workbench", "/workbench/"):
            body = render_html(self.app.snapshot).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path in ("/workbench/api/candidates", "/api/candidates"):
            body = json.dumps(self.app.snapshot.to_dict(), ensure_ascii=False).encode(
                "utf-8"
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


class WorkbenchApp:
    """In-memory workbench holding one immutable snapshot."""

    def __init__(self, snapshot: CandidateSnapshot) -> None:
        self.snapshot = snapshot

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
        prog="python3 -m monte_arb.workbench_server",
        description="Serve the Day14 read-only workbench.",
    )
    parser.add_argument("--snapshot", type=Path, default=None)
    parser.add_argument("--port", type=int, default=18768)
    args = parser.parse_args(argv)
    if args.snapshot is None:
        raise SystemExit("--snapshot <day14-workbench-scan.json> is required")
    import json as _json

    payload = _json.loads(args.snapshot.read_text())
    from .workbench import CandidateSnapshot as _CS

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
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port), WorkbenchApp(snapshot).make_handler()
    )
    print(f"workbench http://127.0.0.1:{args.port}/workbench")
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
    from .workbench import BookQuote

    return BookQuote(
        identity=identity,
        best_bid=payload["best_bid"],
        best_ask=payload["best_ask"],
        bid_size=payload["bid_size"],
        ask_size=payload["ask_size"],
        source_time_ms=payload.get("source_time_ms"),
    )


def _candidate_from_dict(payload: dict) -> Any:
    from .workbench import Candidate

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
