"""Workbench HTTP surface: Day14 candidate view + Day16 execution view.

Public seam: WorkbenchApp over in-memory snapshots with an optional scanner
callable. All data is read-only; no execution client and no orders.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler
from typing import Any, Callable, Optional, Sequence

from .workbench import CandidateSnapshot, SnapshotItem

PAGE_TITLE = "研究工作台 · Day14 v0"
PAGE_CSS = """\
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

EXEC_PAGE_TITLE = "研究工作台 · 可执行性与容量（Day16）"
EXEC_CSS = """\
:root { color-scheme: dark; --bg:#0b1117; --panel:#121a23; --panel2:#0e151d; --line:#243140; --text:#e8eef4; --muted:#8fa0b0; --accent:#3ecf8e; --accent2:#5aa9ff; --pos:#3ecf8e; --neg:#ff7a6e; --warn:#f5b759; --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; --sans:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
* { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--text); font-family:var(--sans); line-height:1.55; font-size:14px; }
.wrap { max-width:1180px; margin:0 auto; padding:28px 22px 80px; }
h1 { font-size:24px; margin:4px 0 4px; letter-spacing:-.01em; }
h2 { font-size:15px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); margin:26px 0 10px; }
.eyebrow { color:var(--accent); font-weight:700; letter-spacing:.14em; text-transform:uppercase; font-size:11px; }
.lede { color:var(--muted); max-width:860px; margin:6px 0 16px; }
.controls { display:flex; flex-wrap:wrap; gap:10px; align-items:flex-end; margin:14px 0; }
.field { display:flex; flex-direction:column; gap:4px; }
.field label { font-size:10px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
select, input, button { font:inherit; color:var(--text); background:var(--panel); border:1px solid var(--line); border-radius:6px; padding:7px 10px; }
select:focus, input:focus { outline:1px solid var(--accent2); }
button { cursor:pointer; }
button:hover { border-color:var(--accent2); }
.btn { background:var(--panel2); }
.btn.on { background:var(--accent); color:#07130d; border-color:var(--accent); font-weight:700; }
.btn-pair { min-width:150px; text-align:left; font-family:var(--mono); }
.refresh { min-width:86px; }
.spin { display:inline-block; animation:rot 0.8s linear infinite; }
@keyframes rot { to { transform:rotate(360deg); } }
.meta { color:var(--muted); font-size:12px; margin:8px 0 14px; font-family:var(--mono); }
.bar-wrap { display:flex; align-items:center; gap:8px; margin:4px 0; }
.bar-label { width:120px; color:var(--muted); font-size:12px; font-family:var(--mono); }
.bar-track { flex:1; height:14px; background:var(--panel2); border:1px solid var(--line); border-radius:4px; overflow:hidden; }
.bar-fill { height:100%; background:linear-gradient(90deg,var(--accent2),var(--accent)); }
.bar-val { width:110px; text-align:right; font-family:var(--mono); font-size:12px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { color:var(--muted); font-size:10px; text-transform:uppercase; letter-spacing:.05em; text-align:right; padding:8px 8px; border-bottom:1px solid var(--line); }
th:first-child, td:first-child { text-align:left; }
td { padding:8px; text-align:right; border-bottom:1px solid #1a2532; font-family:var(--mono); }
tr:hover td { background:#101a24; }
.pos { color:var(--pos); } .neg { color:var(--neg); } .warn { color:var(--warn); } .muted { color:var(--muted); }
.na { color:#54616e; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px; margin:12px 0; }
.boundary { border-left:3px solid var(--warn); padding:10px 14px; background:var(--panel2); border-radius:0 8px 8px 0; font-size:12px; color:var(--muted); }
.leg-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:8px 0; }
.leg { background:var(--panel2); border:1px solid var(--line); border-radius:8px; padding:10px 12px; }
.leg h3 { margin:0 0 6px; font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }
.leg .row { display:flex; justify-content:space-between; font-family:var(--mono); font-size:13px; padding:2px 0; }
.pill { display:inline-block; border:1px solid var(--line); border-radius:999px; padding:2px 10px; font-size:11px; color:var(--muted); margin-right:6px; }
.pill.big { color:var(--accent); border-color:var(--accent); }
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
<h1>{PAGE_TITLE}</h1><p class="lede">扫描 Lighter–Hyperliquid 全部可映射永续，只保留当前快照可计算的证据。最多展示 3 个候选；不足时不凑数。Day16 执行视图：<a href="/workbench/execution">执行成本与容量</a>。</p></header>
<main>
<div class="card"><span class="pill">read_only</span><span class="pill">execution_client_present=false</span>
<span class="pill">schema={snapshot.schema}</span><span class="pill">observed_at={snapshot.observed_at}</span>
<div class="metric">{len(snapshot.candidates)} 候选 / {len(snapshot.markets)} 市场</div></div>
{boundary}
<h2>交易吸引力榜（当前快照）</h2><div class="card">{table}</div>
<h2>原始候选 JSON</h2><div class="card"><pre>{json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2)}</pre></div>
</main></body></html>"""


def render_execution_html() -> str:
    return f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{EXEC_PAGE_TITLE}</title><style>{EXEC_CSS}</style></head>
<body><div class="wrap">
<div class="eyebrow">MonteLab · Read-only Workbench · Day16</div>
<h1>可执行性与容量 · 执行成本视图</h1>
<p class="lede">每个候选、每个方向、每个目标规模：双腿分别逐档走真实 L2，输出可成交 VWAP、滑点、已知费率、未成交数量和容量边界。页面每 30 秒自动刷新，也可手动刷新；自定义规模由冻结盘口即时重算，不重新请求交易所。</p>
<div class="card">
  <div class="controls">
    <div class="field"><label>Pair</label><select id="pair"></select></div>
    <div class="field"><label>Direction</label>
      <div style="display:flex;gap:6px">
        <button class="btn dir on" data-dir="buy_left_sell_right" title="买 Lighter ask / 卖 Hyperliquid bid">买左卖右</button>
        <button class="btn dir" data-dir="buy_right_sell_left" title="买 Hyperliquid ask / 卖 Lighter bid">买右卖左</button>
      </div>
    </div>
    <div class="field"><label>规模 (USD)</label>
      <div style="display:flex;gap:6px;flex-wrap:wrap" id="sizes"></div>
    </div>
    <div class="field"><label>自定义规模</label>
      <div style="display:flex;gap:6px">
        <input id="custom-size" inputmode="numeric" placeholder="如 300" style="width:110px">
        <button class="btn" id="apply-custom">✓ 应用</button>
      </div>
    </div>
    <div class="field"><label>&nbsp;</label><button class="btn refresh" id="refresh">↻ 刷新</button></div>
    <div class="field"><label>自动刷新</label>
      <button class="btn" id="auto_refresh">每 30s · 开</button>
    </div>
  </div>
  <div class="meta" id="meta">加载中…</div>
</div>
<div id="error" class="boundary" style="display:none"></div>
<div id="legs"></div>
<h2>容量曲线（两腿均全额成交的最大规模）</h2>
<div class="card" id="capacity"></div>
<h2>逐规模执行结果</h2>
<div class="card"><div style="overflow-x:auto"><table id="table">
<thead><tr><th>规模</th><th>买腿 vwap</th><th>买滑点</th><th>买费率</th><th>卖腿 vwap</th><th>卖滑点</th><th>卖费率</th>
<th>价差捕获</th><th>滑点成本</th><th>费率成本</th><th>净价差</th><th>总成本</th><th>成交率</th></tr></thead><tbody></tbody></table></div></div>
<h2>研究边界</h2>
<div class="card boundary" id="boundaries"></div>
</div>
<script>
const autoRefreshMs = 30000;
let state = {{ pairs: [], sizes: [], direction: 'buy_left_sell_right', customSize: null, auto: true, timer: null, customRows: null }};
const $ = id => document.getElementById(id);
const fmt = (v, d=2) => v === null || v === undefined ? '<span class="na">—</span>' : Number(v).toFixed(d);
const money = v => v === null || v === undefined ? '—' : '$' + Number(v).toLocaleString('en-US', {{maximumFractionDigits: 0}});
const cls = v => v > 0.004 ? 'pos' : (v < -0.004 ? 'neg' : '');
function legRow(leg, title) {{
  if (!leg) return '';
  const reason = leg.orderable ? '' : ` · <span class="warn">${{leg.orderable_reason}}</span>`;
  return `<div class="leg"><h3>${{title}} · ${{leg.venue}}</h3>
    <div class="row"><span>目标数量</span><span>${{fmt(leg.target_qty, 4)}}</span></div>
    <div class="row"><span>成交 / 未成交</span><span>${{fmt(leg.filled_qty, 4)}} / ${{fmt(leg.unfilled_qty, 4)}}</span></div>
    <div class="row"><span>VWAP</span><span>${{fmt(leg.vwap, 4)}}</span></div>
    <div class="row"><span>滑点 (bps)</span><span class="${{cls(leg.slippage_bps)}}">${{fmt(leg.slippage_bps, 2)}}</span></div>
    <div class="row"><span>费率 (bps)</span><span>${{leg.fee_bps === null ? '<span class="warn">未知</span>' : fmt(leg.fee_bps, 2)}}</span></div>
    <div class="row"><span>单腿成本 (bps)</span><span>${{leg.total_bps === null ? '<span class="warn">未知</span>' : fmt(leg.total_bps, 2)}}</span></div>
    <div class="row"><span>档位使用</span><span>${{leg.levels_used}}</span></div>${{reason}}</div>`;
}}
function customDir(payload) {{
  if (!state.customRows || !state.customRows.pairs) return null;
  const row = state.customRows.pairs[state.pair];
  return row ? row[state.direction] : null;
}}
function renderLegs(payload) {{
  const pair = payload.pairs.find(p => p.pair_name === state.pair);
  if (!pair) return;
  const rows = pair.per_size.filter(r => r.size_usd === state.customSize);
  const size = rows[0];
  const d = size ? size[state.direction] : customDir(payload);
  if (!d) {{
    $('legs').innerHTML = '<div class="muted">选择规模后显示双腿细节。</div>';
    return;
  }}
  $('legs').innerHTML = `<div class="leg-grid">
    ${{legRow(d.buy, '买腿（主动吃单）')}}${{legRow(d.sell, '卖腿（主动吃单）')}}</div>
    <div class="meta">方向 ${{state.direction}} · 规模 ${{money(state.customSize)}} · 价差捕获 ${{fmt(d.capture_bps)}} bps ·
    净价差（不含未知费用）<span class="${{cls(d.net_spread_bps)}}">${{fmt(d.net_spread_bps)}}</span> bps ·
    总成本 ${{d.total_cost_bps === null ? '<span class="warn">未知（HL 费率未公开）</span>' : fmt(d.total_cost_bps) + ' bps'}}</div>`;
}}
function renderTable(payload, customRows) {{
  const pair = payload.pairs.find(p => p.pair_name === state.pair);
  if (!pair) return;
  const rows = pair.per_size.map(r => {{
    const d = r[state.direction];
    return `<tr>
      <td>${{money(r.size_usd)}}</td>
      <td>${{fmt(d.buy.vwap, 4)}}</td><td class="${{cls(d.buy.slippage_bps)}}">${{fmt(d.buy.slippage_bps, 2)}}</td>
      <td>${{d.buy.fee_bps === null ? '<span class="warn">未知</span>' : fmt(d.buy.fee_bps, 2)}}</td>
      <td>${{fmt(d.sell.vwap, 4)}}</td><td class="${{cls(d.sell.slippage_bps)}}">${{fmt(d.sell.slippage_bps, 2)}}</td>
      <td>${{d.sell.fee_bps === null ? '<span class="warn">未知</span>' : fmt(d.sell.fee_bps, 2)}}</td>
      <td class="${{cls(d.capture_bps)}}">${{fmt(d.capture_bps, 2)}}</td>
      <td>${{fmt(d.slippage_cost_bps, 2)}}</td>
      <td>${{d.fee_cost_bps === null ? '<span class="warn">未知</span>' : fmt(d.fee_cost_bps, 2)}}</td>
      <td class="${{cls(d.net_spread_bps)}}">${{fmt(d.net_spread_bps, 2)}}</td>
      <td>${{d.total_cost_bps === null ? '<span class="warn">未知</span>' : fmt(d.total_cost_bps, 2)}}</td>
      <td>${{(d.fill_pct * 100).toFixed(1)}}%</td></tr>`;
  }});
  if (customRows && customRows.pairs && customRows.pairs[state.pair]) {{
    const d = customRows.pairs[state.pair][state.direction];
    if (d) rows.push(`<tr style="background:#16222e">
      <td>${{money(state.customSize)}} <span class="warn">自定义</span></td>
      <td>${{fmt(d.buy.vwap, 4)}}</td><td class="${{cls(d.buy.slippage_bps)}}">${{fmt(d.buy.slippage_bps, 2)}}</td>
      <td>${{d.buy.fee_bps === null ? '<span class="warn">未知</span>' : fmt(d.buy.fee_bps, 2)}}</td>
      <td>${{fmt(d.sell.vwap, 4)}}</td><td class="${{cls(d.sell.slippage_bps)}}">${{fmt(d.sell.slippage_bps, 2)}}</td>
      <td>${{d.sell.fee_bps === null ? '<span class="warn">未知</span>' : fmt(d.sell.fee_bps, 2)}}</td>
      <td class="${{cls(d.capture_bps)}}">${{fmt(d.capture_bps, 2)}}</td>
      <td>${{fmt(d.slippage_cost_bps, 2)}}</td>
      <td>${{d.fee_cost_bps === null ? '<span class="warn">未知</span>' : fmt(d.fee_cost_bps, 2)}}</td>
      <td class="${{cls(d.net_spread_bps)}}">${{fmt(d.net_spread_bps, 2)}}</td>
      <td>${{d.total_cost_bps === null ? '<span class="warn">未知</span>' : fmt(d.total_cost_bps, 2)}}</td>
      <td>${{(d.fill_pct * 100).toFixed(1)}}%</td></tr>`);
  }}
  $('table').querySelector('tbody').innerHTML = rows.join('');
}}
function renderCapacity(payload) {{
  const pair = payload.pairs.find(p => p.pair_name === state.pair);
  if (!pair) return;
  const max = Math.max(...payload.sizes_usd);
  const dirs = [['buy_left_sell_right', '买左卖右'], ['buy_right_sell_left', '买右卖左']];
  $('capacity').innerHTML = dirs.map(([d, label]) => {{
    const cap = pair.capacity_usd[d] || 0;
    const pct = Math.min(100, (cap / max) * 100);
    return `<div class="bar-wrap"><div class="bar-label">${{label}}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${{pct}}%"></div></div>
      <div class="bar-val">${{money(cap)}}</div></div>`;
  }}).join('');
}}
function render(payload) {{
  if (!payload.pairs.length) {{
    $('error').style.display = 'block';
    $('error').textContent = '本次扫描没有可计算的双腿候选。';
    return;
  }}
  $('error').style.display = 'none';
  if (!state.pair || !payload.pairs.some(p => p.pair_name === state.pair)) {{
    state.pair = payload.pairs[0].pair_name;
  }}
  const sel = $('pair');
  if (sel.options.length !== payload.pairs.length) {{
    sel.innerHTML = payload.pairs.map(p => `<option value="${{p.pair_name}}">${{p.pair_name}}</option>`).join('');
  }}
  sel.value = state.pair;
  state.sizes = payload.sizes_usd;
  if (state.customSize === null) state.customSize = payload.sizes_usd[0];
  $('custom-size').value = state.customSize;
  $('meta').innerHTML = `schema=${{payload.schema}} · observed_at=${{payload.observed_at}} · scanned_at=${{payload.scanned_at}} · read_only=${{payload.read_only}} · execution_client_present=${{payload.execution_client_present}}`;
  renderTable(payload, state.customRows);
  renderCapacity(payload);
  renderLegs(payload);
  $('boundaries').innerHTML = '<ul>' + payload.boundaries.map(b => `<li>${{b}}</li>`).join('') + '</ul>';
  const sizesEl = $('sizes');
  if (!sizesEl.dataset.built) {{
    sizesEl.dataset.built = '1';
    state.sizes.forEach(s => {{
      const b = document.createElement('button');
      b.className = 'btn size';
      b.textContent = '$' + s;
      b.onclick = () => {{ state.customSize = s; $('custom-size').value = s; refreshData(); }};
      sizesEl.appendChild(b);
    }});
  }}
}}
async function refreshData() {{
  try {{
    const r = await fetch('/workbench/api/refresh', {{method: 'POST', cache: 'no-store'}});
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const payload = await r.json();
    if (state.customSize && !payload.sizes_usd.includes(state.customSize)) {{
      const cr = await fetch('/workbench/api/execution/compute', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{size_usd: state.customSize}})}});
      state.customRows = await cr.json();
    }} else state.customRows = null;
    render(payload);
  }} catch (e) {{
    $('error').style.display = 'block';
    $('error').textContent = '加载失败: ' + e.message;
  }}
}}
async function manualRefresh() {{
  const btn = $('refresh');
  btn.innerHTML = '<span class="spin">↻</span> 刷新中';
  await refreshData();
  btn.innerHTML = '↻ 刷新';
}}
function setup() {{
  $('pair').onchange = e => {{ state.pair = e.target.value; state.customRows = null; refreshData(); }};
  document.querySelectorAll('.dir').forEach(b => b.onclick = () => {{
    document.querySelectorAll('.dir').forEach(x => x.classList.remove('on'));
    b.classList.add('on');
    state.direction = b.dataset.dir;
    refreshData();
  }});
  $('apply-custom').onclick = () => {{
    const v = parseFloat($('custom-size').value.replace(/[^0-9.]/g, ''));
    if (v > 0) {{ state.customSize = v; refreshData(); }}
  }};
  $('refresh').onclick = manualRefresh;
  $('auto_refresh').onclick = () => {{
    state.auto = !state.auto;
    $('auto_refresh').textContent = state.auto ? '每 30s · 开' : '每 30s · 关';
    if (state.auto) startAuto(); else clearInterval(state.timer);
  }};
  function startAuto() {{
    clearInterval(state.timer);
    state.timer = setInterval(refreshData, autoRefreshMs);
  }}
  startAuto();
  refreshData();
}}
setup();
</script>
</div></body></html>"""


class WorkbenchHandler(BaseHTTPRequestHandler):
    app: "WorkbenchApp"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/workbench", "/workbench/"):
            if self.app.snapshot is not None:
                self._send(200, render_html(self.app.snapshot).encode("utf-8"), "text/html; charset=utf-8")
            else:
                self._send(200, render_execution_html().encode("utf-8"), "text/html; charset=utf-8")
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
                self._send(409, b"no scanner configured", "text/plain; charset=utf-8")
                return
            try:
                self.app.refresh(force=True)
            except Exception as exc:  # noqa: BLE001 - surface scanner failure to the page
                self._send(500, str(exc).encode("utf-8", errors="replace"), "text/plain; charset=utf-8")
                return
            self._send(
                200,
                json.dumps(self.app.execution.to_dict(), ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8",
            )
            return
        if path == "/workbench/api/execution/compute":
            if self.app.execution is None:
                self._send(404, b"execution snapshot not loaded", "text/plain; charset=utf-8")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                size = float(json.loads(raw or b"{}").get("size_usd", 0))
            except (ValueError, json.JSONDecodeError):
                self._send(400, b"bad size_usd", "text/plain; charset=utf-8")
                return
            if size <= 0:
                self._send(400, b"size_usd must be positive", "text/plain; charset=utf-8")
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

    snapshot: Day14 CandidateSnapshot (candidate mode).
    execution: Day16 ExecutionSnapshot (execution mode; also detected when
        snapshot carries a `pairs` attribute).
    scanner: optional callable returning a fresh ExecutionSnapshot; used by
        GET /workbench/api/execution (mtime-based reload) and POST refresh.
    """

    def __init__(
        self,
        snapshot: Optional[Any] = None,
        *,
        execution: Optional[Any] = None,
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
        self.scanner = scanner
        self._lock = threading.Lock()
        self.last_scan_error: Optional[str] = None

    def refresh(self, *, force: bool = False) -> None:
        if self.scanner is None:
            return
        with self._lock:
            try:
                fresh = self.scanner()
                if fresh is not None:
                    self.execution = fresh
                    self.last_scan_error = None
            except Exception as exc:  # noqa: BLE001 - keep old snapshot on scanner failure
                self.last_scan_error = str(exc)

    def compute_custom_size(self, size_usd: float) -> dict[str, Any]:
        from decimal import Decimal

        from .day16_execution import pair_execution

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
                per_direction[direction] = result.to_dict()
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
        prog="python3 -m monte_arb.workbench_server",
        description="Serve the read-only research workbench (Day14 candidates + Day16 execution).",
    )
    parser.add_argument("--snapshot", type=Path, default=None)
    parser.add_argument("--execution", type=Path, default=None)
    parser.add_argument("--port", type=int, default=18768)
    parser.add_argument("--rescan-seconds", type=float, default=0.0)
    args = parser.parse_args(argv)
    if args.snapshot is None and args.execution is None:
        raise SystemExit("--snapshot <day14-scan.json> or --execution <day16-scan.json> is required")

    snapshot = None
    execution = None
    scanner: Optional[Callable[[], Any]] = None
    if args.snapshot is not None:
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
    if args.execution is not None:
        from .day16_execution import load_snapshot

        execution = load_snapshot(args.execution)

        def _scanner() -> Any:
            return load_snapshot(args.execution)

        scanner = _scanner

    app = WorkbenchApp(snapshot, execution=execution, scanner=scanner)
    if args.rescan_seconds > 0:
        import time as _time

        def _rescan_loop() -> None:
            while True:
                _time.sleep(args.rescan_seconds)
                app.refresh(force=True)

        threading.Thread(target=_rescan_loop, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), app.make_handler())
    print(f"workbench http://127.0.0.1:{args.port}/workbench")
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
