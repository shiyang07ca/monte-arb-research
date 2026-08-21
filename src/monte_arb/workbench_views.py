"""Light-only HTML views for the read-only research workbench."""

from __future__ import annotations

import json
from typing import Any, Optional

from .candidate_workbench import CandidateSnapshot

PAGE_TITLE = "研究工作台 · 候选雷达"
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
pre { overflow-x:auto; padding:16px; background:#f2eee6; color:var(--ink); border:1px solid var(--line); border-radius:10px; line-height:1.5; font-size:.88rem; }
code { font-family:var(--mono); background:#eeece5; padding:.12em .35em; border-radius:4px; }
a { color:var(--accent); } .pill { display:inline-block; border:1px solid var(--line); border-radius:999px; padding:4px 10px; background:var(--panel); font-size:.82rem; margin:2px 4px 2px 0; }
.boundary { border-left:4px solid var(--warn); background:var(--warn-soft); padding:14px 16px; border-radius:0 8px 8px 0; }
"""


def _fmt(value: Optional[Any], suffix: str = "") -> str:
    if value is None:
        return "not_computed"
    return f"{value}{suffix}"


def render_candidate_html(snapshot: CandidateSnapshot) -> str:
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
<h1>{PAGE_TITLE}</h1><p class="lede">扫描 Lighter–Hyperliquid 全部可映射永续，只保留当前快照可计算的证据。最多展示 3 个候选；不足时不凑数。执行视图：<a href="/workbench/execution">执行成本与容量</a>。</p></header>
<main>
<div class="card"><span class="pill">read_only</span><span class="pill">execution_client_present=false</span>
<span class="pill">schema={snapshot.schema}</span><span class="pill">observed_at={snapshot.observed_at}</span>
<div class="metric">{len(snapshot.candidates)} 候选 / {len(snapshot.markets)} 市场</div></div>
{boundary}
<h2>交易吸引力榜（当前快照）</h2><div class="card">{table}</div>
<h2>原始候选 JSON</h2><div class="card"><pre>{json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2)}</pre></div>
</main></body></html>"""


EXEC_PAGE_TITLE = "研究工作台 · 可执行性与容量"
EXEC_CSS = """\
:root { color-scheme: light; --bg:#f6f3ed; --panel:#fffdf8; --panel2:#f2eee6; --line:#d8d2c7; --text:#172126; --muted:#5e6a70; --accent:#006d77; --accent2:#167f8a; --pos:#24734a; --neg:#b23a3a; --warn:#9b5d00; --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; --sans:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
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
.btn.on { background:var(--accent); color:#fff; border-color:var(--accent); font-weight:700; }
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
td { padding:8px; text-align:right; border-bottom:1px solid #e8e2d8; font-family:var(--mono); }
tr:hover td { background:#f8f4ec; }
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


def render_execution_html() -> str:
    return f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{EXEC_PAGE_TITLE}</title><style>{EXEC_CSS}</style></head>
<body><div class="wrap">
<div class="eyebrow">MonteLab · Read-only Workbench · Execution</div>
<h1>可执行性与容量 · 执行成本视图</h1>
<p class="lede">每个候选、每个方向、每个目标规模：两腿使用共同合法经济敞口，分别逐档走真实 L2，输出 VWAP、可成交价差、盘口冲击分解、费率证据、未成交数量、四次主动成交基线和容量下界。页面默认只读当前快照；“市场重扫”或自动重扫会重新请求交易所（全市场约 2 分钟），自定义规模则在冻结盘口上即时重算。</p>
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
    <div class="field"><label>&nbsp;</label><button class="btn refresh" id="refresh">↻ 市场重扫</button></div>
    <div class="field"><label>自动重扫</label>
      <button class="btn" id="auto_refresh">每 30s · 关</button>
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
<thead><tr><th>规模</th><th>共同敞口</th><th>买腿 vwap</th><th>买滑点</th><th>卖腿 vwap</th><th>卖滑点</th>
<th>入场 bps</th><th>入场 USD</th><th>同盘口往返 bps</th><th>同盘口往返 USD</th><th>费后结果</th><th>成交率</th><th>残余敞口</th></tr></thead><tbody></tbody></table></div></div>
<h2>研究边界</h2>
<div class="card boundary" id="boundaries"></div>
</div>
<script>
const autoRefreshMs = 30000;
let state = {{ pairs: [], sizes: [], direction: 'buy_left_sell_right', customSize: null, auto: false, timer: null, customRows: null, refreshing: false }};
const $ = id => document.getElementById(id);
const fmt = (v, d=2) => v === null || v === undefined ? '<span class="na">—</span>' : Number(v).toFixed(d);
const money = v => v === null || v === undefined ? '—' : '$' + Number(v).toLocaleString('en-US', {{maximumFractionDigits: 0}});
const money2 = v => v === null || v === undefined ? '—' : (Number(v) < 0 ? '-$' : '$') + Math.abs(Number(v)).toFixed(4);
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
    <div class="row"><span>费用 (USD)</span><span>${{leg.fee_cost_usd === null ? '<span class="warn">未知</span>' : money2(leg.fee_cost_usd)}}</span></div>
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
  const roundTrip = size ? size[state.direction + '_round_trip'] : (d && d.round_trip);
  $('legs').innerHTML = `<div class="leg-grid">
    ${{legRow(d.buy, '买腿（主动吃单）')}}${{legRow(d.sell, '卖腿（主动吃单）')}}</div>
    <div class="meta">方向 ${{state.direction}} · 规模 ${{money(state.customSize)}} · 共同敞口 ${{fmt(d.common_exposure_units, 4)}} ·
    入场 <span class="${{cls(d.price_pnl_bps)}}">${{fmt(d.price_pnl_bps)}} bps / ${{money2(d.price_pnl_usd)}}</span> ·
    盘口冲击分解 ${{fmt(d.slippage_cost_bps)}} bps（仅诊断，不重复扣减） ·
    同盘口往返 <span class="${{cls(roundTrip && roundTrip.round_trip_price_pnl_bps)}}">${{fmt(roundTrip && roundTrip.round_trip_price_pnl_bps)}} bps / ${{money2(roundTrip && roundTrip.round_trip_price_pnl_usd)}}</span> ·
    残余敞口 ${{fmt(d.residual_base_qty, 4)}} ·
    费后结果 ${{d.net_price_pnl_bps === null ? '<span class="warn">未知（费率证据缺失）</span>' : fmt(d.net_price_pnl_bps) + ' bps / ' + money2(d.net_price_pnl_usd)}}</div>`;
}}
function renderTable(payload, customRows) {{
  const pair = payload.pairs.find(p => p.pair_name === state.pair);
  if (!pair) return;
  const rows = pair.per_size.map(r => {{
    const d = r[state.direction];
    const rt = r[state.direction + '_round_trip'];
    return `<tr>
      <td>${{money(r.size_usd)}}</td><td>${{fmt(d.common_exposure_units, 4)}}</td>
      <td>${{fmt(d.buy.vwap, 4)}}</td><td class="${{cls(d.buy.slippage_bps)}}">${{fmt(d.buy.slippage_bps, 2)}}</td>
      <td>${{fmt(d.sell.vwap, 4)}}</td><td class="${{cls(d.sell.slippage_bps)}}">${{fmt(d.sell.slippage_bps, 2)}}</td>
      <td class="${{cls(d.price_pnl_bps)}}">${{fmt(d.price_pnl_bps, 2)}}</td><td class="${{cls(d.price_pnl_usd)}}">${{money2(d.price_pnl_usd)}}</td>
      <td class="${{cls(rt && rt.round_trip_price_pnl_bps)}}">${{fmt(rt && rt.round_trip_price_pnl_bps, 2)}}</td><td class="${{cls(rt && rt.round_trip_price_pnl_usd)}}">${{money2(rt && rt.round_trip_price_pnl_usd)}}</td>
      <td>${{d.net_price_pnl_bps === null ? '<span class="warn">未知</span>' : fmt(d.net_price_pnl_bps, 2) + ' / ' + money2(d.net_price_pnl_usd)}}</td>
      <td>${{(d.fill_pct * 100).toFixed(1)}}%</td><td>${{fmt(d.residual_base_qty, 4)}}</td></tr>`;
  }});
  if (customRows && customRows.pairs && customRows.pairs[state.pair]) {{
    const d = customRows.pairs[state.pair][state.direction];
    if (d) {{
      const rt = d.round_trip;
      rows.push(`<tr style="background:#f2eee6">
      <td>${{money(state.customSize)}} <span class="warn">自定义</span></td><td>${{fmt(d.common_exposure_units, 4)}}</td>
      <td>${{fmt(d.buy.vwap, 4)}}</td><td class="${{cls(d.buy.slippage_bps)}}">${{fmt(d.buy.slippage_bps, 2)}}</td>
      <td>${{fmt(d.sell.vwap, 4)}}</td><td class="${{cls(d.sell.slippage_bps)}}">${{fmt(d.sell.slippage_bps, 2)}}</td>
      <td class="${{cls(d.price_pnl_bps)}}">${{fmt(d.price_pnl_bps, 2)}}</td><td class="${{cls(d.price_pnl_usd)}}">${{money2(d.price_pnl_usd)}}</td>
      <td class="${{cls(rt && rt.round_trip_price_pnl_bps)}}">${{fmt(rt && rt.round_trip_price_pnl_bps, 2)}}</td><td class="${{cls(rt && rt.round_trip_price_pnl_usd)}}">${{money2(rt && rt.round_trip_price_pnl_usd)}}</td>
      <td>${{d.net_price_pnl_bps === null ? '<span class="warn">未知</span>' : fmt(d.net_price_pnl_bps, 2) + ' / ' + money2(d.net_price_pnl_usd)}}</td>
      <td>${{(d.fill_pct * 100).toFixed(1)}}%</td><td>${{fmt(d.residual_base_qty, 4)}}</td></tr>`);
    }}
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
    const detail = pair.capacity && pair.capacity[d];
    const labelValue = detail && detail.lower_bound_only ? '≥ ' + money(cap) : money(cap);
    const pct = Math.min(100, (cap / max) * 100);
    return `<div class="bar-wrap"><div class="bar-label">${{label}}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${{pct}}%"></div></div>
      <div class="bar-val">${{labelValue}}</div></div>`;
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
  $('meta').innerHTML = `schema=${{payload.schema}} · observed_at=${{payload.observed_at}} · scanned_at=${{payload.scanned_at}} · capture_span=${{payload.capture_span_ms == null ? 'unknown' : (payload.capture_span_ms / 1000).toFixed(1) + 's'}} · refresh_mode=${{payload.refresh_mode}} · read_only=${{payload.read_only}} · execution_client_present=${{payload.execution_client_present}}`;
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
async function loadData() {{
  const r = await fetch('/workbench/api/execution', {{cache: 'no-store'}});
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}}
async function refreshData(live=false) {{
  if (state.refreshing) return;
  state.refreshing = true;
  try {{
    let payload;
    if (live) {{
      const r = await fetch('/workbench/api/refresh', {{method: 'POST', cache: 'no-store'}});
      if (!r.ok) throw new Error('HTTP ' + r.status);
      payload = await r.json();
    }} else {{
      payload = await loadData();
    }}
    if (state.customSize && !payload.sizes_usd.includes(state.customSize)) {{
      const cr = await fetch('/workbench/api/execution/compute', {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{size_usd: state.customSize}})}});
      state.customRows = await cr.json();
    }} else state.customRows = null;
    render(payload);
  }} catch (e) {{
    $('error').style.display = 'block';
    $('error').textContent = '加载失败: ' + e.message;
  }} finally {{
    state.refreshing = false;
  }}
}}
async function manualRefresh() {{
  const btn = $('refresh');
  btn.innerHTML = '<span class="spin">↻</span> 重扫中';
  await refreshData(true);
  btn.innerHTML = '↻ 市场重扫';
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
    state.timer = setInterval(() => refreshData(true), autoRefreshMs);
  }}
  refreshData();
}}
setup();
</script>
</div></body></html>"""
