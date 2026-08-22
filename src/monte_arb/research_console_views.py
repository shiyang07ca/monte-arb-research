"""Light-only product views for the read-only research console."""

from __future__ import annotations

import html
from typing import Any, Mapping


SHELL_CSS = """\
:root {
  color-scheme: light;
  --ink:#17211f; --muted:#66706b; --soft:#8a938e; --paper:#f3f0e8;
  --panel:#fffdf8; --panel-2:#f8f5ee; --line:#d9d4c9; --line-strong:#bdb7aa;
  --teal:#08776f; --teal-2:#0d9186; --teal-soft:#dcefeb;
  --blue:#2b5f8a; --blue-soft:#e3edf5; --amber:#9a6500; --amber-soft:#fff1ce;
  --red:#ad413f; --red-soft:#f8e3df; --green:#28704a; --green-soft:#dff0e6;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --sans:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --serif:Georgia,"Times New Roman",serif;
}
* { box-sizing:border-box; }
html { background:var(--paper); }
body { margin:0; color:var(--ink); background:var(--paper); font:14px/1.55 var(--sans); }
a { color:inherit; }
.shell { width:min(1440px, calc(100% - 32px)); margin:0 auto; }
.topbar { position:sticky; top:0; z-index:50; border-bottom:1px solid var(--line); background:rgba(243,240,232,.94); backdrop-filter:blur(14px); }
.topbar-inner { height:58px; display:flex; align-items:center; justify-content:space-between; gap:20px; }
.brand { display:flex; align-items:center; gap:10px; text-decoration:none; font-weight:850; letter-spacing:-.02em; }
.brand-mark { width:28px; height:28px; display:grid; place-items:center; border-radius:8px; background:var(--ink); color:white; font:800 12px var(--mono); }
.nav { display:flex; align-items:center; gap:4px; overflow-x:auto; }
.nav a { min-height:44px; display:inline-flex; align-items:center; padding:8px 11px; border-radius:8px; text-decoration:none; color:var(--muted); white-space:nowrap; font-size:13px; flex:0 0 auto; }
.nav a:hover,.nav a.on { color:white; background:var(--ink); box-shadow:0 0 0 1px var(--ink); }
.status { display:flex; align-items:center; gap:7px; color:var(--muted); white-space:nowrap; font-size:12px; }
.status-dot { width:8px; height:8px; border-radius:99px; background:var(--green); box-shadow:0 0 0 4px var(--green-soft); }
.hero { padding:34px 0 22px; display:grid; grid-template-columns:minmax(0,1fr) auto; gap:28px; align-items:end; }
.eyebrow { color:var(--teal); font-weight:800; text-transform:uppercase; letter-spacing:.13em; font-size:11px; }
h1 { margin:8px 0 8px; font:700 clamp(30px,3.5vw,48px)/1.06 var(--serif); letter-spacing:-.04em; }
h2 { margin:0; font:700 clamp(20px,2.5vw,30px)/1.12 var(--serif); letter-spacing:-.025em; }
h3 { margin:0; font-size:14px; }
.lede { margin:0; max-width:820px; color:var(--muted); font-size:15px; }
.hero-meta { display:flex; flex-direction:column; align-items:flex-end; gap:7px; color:var(--muted); font:12px var(--mono); }
.pill { display:inline-flex; align-items:center; gap:6px; padding:4px 9px; border:1px solid var(--line); border-radius:999px; background:var(--panel); color:var(--muted); font-size:11px; }
.pill.ok { color:var(--green); border-color:#b8d5c4; background:var(--green-soft); }
.pill.warn { color:var(--amber); border-color:#ead49e; background:var(--amber-soft); }
.pill.blocked { color:var(--red); border-color:#e5bbb4; background:var(--red-soft); }
.section { margin:20px 0 34px; }
.section-head { display:flex; justify-content:space-between; align-items:end; gap:20px; margin-bottom:12px; }
.section-kicker { margin-top:5px; color:var(--muted); }
.card { border:1px solid var(--line); border-radius:14px; background:var(--panel); box-shadow:0 12px 36px rgba(36,39,34,.035); }
.card-pad { padding:20px; }
.grid { display:grid; gap:12px; }
.grid-2 { grid-template-columns:repeat(2,minmax(0,1fr)); }
.grid-3 { grid-template-columns:repeat(3,minmax(0,1fr)); }
.grid-4 { grid-template-columns:repeat(4,minmax(0,1fr)); }
.metric-label { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }
.metric-value { margin:5px 0 3px; font:750 clamp(22px,2.4vw,34px)/1 var(--mono); letter-spacing:-.045em; }
.metric-note { color:var(--muted); font-size:12px; }
.mono { font-family:var(--mono); }
.pos { color:var(--green); } .neg { color:var(--red); } .muted { color:var(--muted); }
.button,.seg button,select,input { border:1px solid var(--line); background:var(--panel); color:var(--ink); border-radius:8px; font:inherit; }
.button { display:inline-flex; align-items:center; justify-content:center; gap:7px; min-height:34px; padding:7px 11px; text-decoration:none; cursor:pointer; }
.button:hover,button:hover { border-color:var(--teal); }
.button.primary { background:var(--ink); border-color:var(--ink); color:white; }
.button.secondary { background:var(--panel-2); }
.seg { display:inline-flex; padding:3px; gap:2px; border:1px solid var(--line); border-radius:10px; background:var(--panel-2); }
.seg button { padding:6px 9px; border-color:transparent; background:transparent; cursor:pointer; color:var(--muted); font-size:12px; }
.seg button.on { color:white; background:var(--ink); border-color:var(--ink); }
.module { position:relative; padding:18px; min-height:170px; overflow:hidden; text-decoration:none; transition:transform .15s ease,border-color .15s ease; }
.module:hover { transform:translateY(-2px); border-color:var(--line-strong); }
.module-number { position:absolute; right:15px; top:10px; color:#e9e4da; font:700 38px var(--serif); }
.module-title { position:relative; display:flex; align-items:center; gap:8px; margin-bottom:9px; font-weight:800; }
.module p { position:relative; margin:0; color:var(--muted); max-width:90%; }
.module-foot { position:absolute; bottom:15px; left:18px; right:18px; display:flex; justify-content:flex-end; align-items:center; color:var(--teal); font-size:12px; }
.table-wrap { width:100%; max-width:100%; min-width:0; overflow:auto; }
table { width:100%; border-collapse:collapse; font-size:12px; }
th { padding:10px 12px; text-align:left; color:var(--muted); background:var(--panel-2); text-transform:uppercase; letter-spacing:.06em; font-size:10px; white-space:nowrap; position:sticky; top:0; }
td { padding:10px 12px; border-top:1px solid #e8e3d9; vertical-align:top; }
tr:hover td { background:#fbf8f2; }
.health-row { display:grid; grid-template-columns:minmax(210px,1.4fr) minmax(190px,1fr) 180px 100px; gap:12px; align-items:center; padding:11px 14px; border-top:1px solid #e8e3d9; }
.health-row:first-child { border-top:0; }
.health-detail { color:var(--muted); font-size:12px; }
.health-last { white-space:nowrap; font-size:11px; }
.footer { margin-top:46px; border-top:1px solid var(--line); padding:22px 0 50px; color:var(--muted); display:flex; justify-content:space-between; gap:18px; font-size:12px; }
@media(max-width:900px){
  .hero { grid-template-columns:1fr; padding-top:34px; }
  .hero-meta { align-items:flex-start; }
  .grid-4,.grid-3 { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .topbar-inner { height:auto; padding:10px 0; flex-wrap:wrap; }
  .status { display:none; }
}
@media(max-width:620px){
  .shell { width:min(100% - 20px, 1440px); }
  .grid-4,.grid-3,.grid-2 { grid-template-columns:1fr; }
  .nav { order:3; width:100%; }
  .health-row { grid-template-columns:1fr auto; }
  .health-row .health-bar,.health-row .health-last { display:none; }
  .section-head { align-items:flex-start; flex-direction:column; }
  h1 { font-size:35px; }
}
"""


def _nav(active: str) -> str:
    items = (
        ("dashboard", "/workbench", "Dashboard"),
        ("markets", "/workbench/markets", "Markets"),
        ("oil", "/workbench/oil", "Brent–WTI"),
        ("funding", "/workbench/funding", "Funding"),
        ("execution", "/workbench/execution", "Execution"),
        ("data", "/workbench/data", "Data"),
    )
    links = "".join(
        f'<a class="{"on" if key == active else ""}" href="{href}">{label}</a>'
        for key, href, label in items
    )
    return f"""<div class="topbar"><div class="shell topbar-inner">
<a class="brand" href="/workbench"><span class="brand-mark">M</span><span>MonteLab</span></a>
<nav class="nav">{links}</nav>
<div class="status"><span class="status-dot"></span>只读研究 · 不连接交易执行</div>
</div></div>"""


def _shell_start(title: str, active: str) -> str:
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{SHELL_CSS}</style></head><body>{_nav(active)}"""


def _shell_end() -> str:
    return """<footer class="shell footer"><span>MonteLab · 可复现市场研究</span>
<span>公开市场数据与明确授权的只读导入 · 不发送订单</span></footer></body></html>"""


def _fmt(value: Any, digits: int = 2, signed: bool = False) -> str:
    if not isinstance(value, (int, float)):
        return "—"
    prefix = "+" if signed and value > 0 else ""
    return f"{prefix}{value:,.{digits}f}"


def render_dashboard_html(projection: Mapping[str, Any]) -> str:
    dashboard = projection.get("dashboard") if isinstance(projection, Mapping) else {}
    dashboard = dashboard if isinstance(dashboard, Mapping) else {}
    dashboard_summary = dashboard.get("summary")
    summary: Mapping[str, Any] = (
        dashboard_summary if isinstance(dashboard_summary, Mapping) else {}
    )
    generated = html.escape(str(projection.get("generated_at", "unknown")))
    spread = summary.get("spread_usd")
    ratio = summary.get("ratio")
    z_value = summary.get("residual_z")
    healthy = int(dashboard.get("healthy_source_count", 0) or 0)
    source_count = int(dashboard.get("source_count", 0) or 0)
    provider_labels = {
        "lighter": "Lighter",
        "hyperliquid": "Hyperliquid xyz",
        "yahoo_chart": "外部连续期货参考",
        "variational": "Variational Omni",
    }
    interval_labels = {"1h": "1 小时", "1d": "日线", "observation": "市场观察"}
    source_rows = []
    for source in projection.get("sources", []):
        if not isinstance(source, Mapping):
            continue
        source_health = source.get("health")
        health: Mapping[str, Any] = (
            source_health if isinstance(source_health, Mapping) else {}
        )
        status = str(source.get("status", "unavailable"))
        sample_count = int(source.get("sample_count", 0) or 0)
        last_at = str(health.get("last_at") or "—")
        last_display = last_at.replace("T", " ").replace("Z", " UTC")
        if len(last_display) > 20:
            last_display = last_display[:16] + " UTC"
        if status == "ok":
            status_label = "可用"
            detail = f"{sample_count:,} 个同步样本"
        else:
            status_label = "不可用"
            reason = str(source.get("reason") or health.get("reason") or "原因未知")
            detail = "等待只读数据导入" if reason == "NO_LOCAL_RECORDINGS" else reason
        provider = provider_labels.get(
            str(source.get("venue", "")), str(source.get("venue", ""))
        )
        interval = interval_labels.get(
            str(source.get("interval", "")), str(source.get("interval", ""))
        )
        source_rows.append(
            f"""<div class="health-row">
<div><strong>{html.escape(str(source.get('label', source.get('key', '?'))))}</strong><br><span class="muted">{html.escape(provider)} · {html.escape(interval)}</span></div>
<div class="health-detail">{html.escape(detail)}</div>
<div class="health-last mono">{html.escape(last_display)}</div>
<div><span class="pill {'ok' if status == 'ok' else 'blocked'}">{status_label}</span></div>
</div>"""
        )
    modules = (
        (
            "01",
            "/workbench/oil",
            "Brent–WTI 相对价值",
            "当前主模块",
            "比较多价格源的历史关系、冻结模型、机制诊断与指定规模执行摩擦。",
            "进入专题 →",
        ),
        (
            "02",
            "/workbench/markets",
            "全市场 Screener",
            "下一阶段",
            "按同标的跨场所、跨标的相对价值和 funding 三种视图发现研究对象。",
            "规划已固化",
        ),
        (
            "03",
            "/workbench/funding",
            "Funding",
            "规划中",
            "保留原生结算间隔，比较跨场所 funding，并累计真实历史现金流。",
            "等待历史采集",
        ),
        (
            "04",
            "/workbench/execution",
            "Execution & Depth",
            "已有计算能力",
            "按方向和规模比较 L2、RFQ 与场所公式；未知费用保持未知。",
            "打开旧执行视图 →",
        ),
        (
            "05",
            "/workbench/tools/spread",
            "Spread Grapher",
            "后续抽取",
            "从油专题抽出同步、权重和图表接口，再开放任意两腿研究工具。",
            "不先做空壳",
        ),
        (
            "06",
            "/workbench/data",
            "Datasets & Jobs",
            "持续建设",
            "查看数据覆盖、缺口、schema、重算命令和 JSON/CSV 下载。",
            "查看数据 →",
        ),
    )
    module_html = "".join(
        f"""<a class="card module" href="{href}"><span class="module-number">{number}</span>
<div class="module-title">{html.escape(title)} <span class="pill">{html.escape(state)}</span></div>
<p>{html.escape(description)}</p><div class="module-foot"><strong>{html.escape(foot)}</strong></div></a>"""
        for number, href, title, state, description, foot in modules
    )
    page = _shell_start("MonteLab · 研究操作台", "dashboard")
    page += f"""<main class="shell"><section class="hero"><div>
<div class="eyebrow">Market Research Console</div><h1>研究操作台</h1>
<p class="lede">从市场版图发现问题，在专题模块中验证历史、机制与执行摩擦。每天增加可以再次运行的数据集、脚本和分析能力，而不是堆叠 JSON 或课程表单。</p>
</div><div class="hero-meta"><span class="pill ok">{healthy}/{source_count} 研究数据源可用</span>
<span>最近更新<br>{generated.replace('T', ' ').replace('Z', ' UTC')[:22]}</span></div></section>
<section class="section"><div class="section-head"><div><h2>Brent–WTI · 当前摘要</h2><div class="section-kicker">来源：{html.escape(str(dashboard.get('primary_source') or 'none'))} · 每个价格源只与自己的历史比较</div></div>
<a class="button primary" href="/workbench/oil">打开完整专题 →</a></div>
<div class="grid grid-4">
<div class="card card-pad"><div class="metric-label">Brent − WTI</div><div class="metric-value">${_fmt(spread,2,True)}</div><div class="metric-note">美元价差，不是套利利润</div></div>
<div class="card card-pad"><div class="metric-label">Price ratio</div><div class="metric-value">{_fmt(ratio,4)}</div><div class="metric-note">降低绝对油价水平影响</div></div>
<div class="card card-pad"><div class="metric-label">Frozen residual z</div><div class="metric-value {'pos' if isinstance(z_value,(int,float)) and z_value>0 else 'neg'}">{_fmt(z_value,2,True)}</div><div class="metric-note">描述性偏离，不证明回归</div></div>
<div class="card card-pad"><div class="metric-label">运行模式</div><div class="metric-value" style="font-size:20px">只读研究</div><div class="metric-note">页面不会连接交易执行或发送订单</div></div>
</div></section>
<section class="section"><div class="section-head"><div><h2>模块地图</h2><div class="section-kicker">首页负责发现和导航；专题模块负责深入验证。</div></div></div>
<div class="grid grid-3">{module_html}</div></section>
<section class="section"><div class="section-head"><div><h2>数据健康</h2><div class="section-kicker">缺失、过期和错误不会被替换成零。</div></div><a class="button secondary" href="/workbench/data">数据目录</a></div>
<div class="card">{''.join(source_rows)}</div></section></main>"""
    return page + _shell_end()


OIL_CSS = """\
.oil-layout { display:grid; grid-template-columns:minmax(0,1fr) 330px; gap:14px; align-items:start; min-width:0; }
.oil-layout > * { min-width:0; }
.toolbar { display:flex; flex-wrap:wrap; justify-content:space-between; gap:10px; padding:12px; margin-bottom:12px; }
.toolbar-group { display:flex; flex-wrap:wrap; align-items:center; gap:8px; }
select,input { min-height:34px; padding:6px 9px; }
.chart-card { padding:14px; overflow:hidden; }
.chart-title { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; margin-bottom:8px; }
.chart-wrap { position:relative; min-height:360px; }
.chart-wrap svg { width:100%; height:360px; display:block; overflow:visible; }
.chart-grid { stroke:#e4dfd5; stroke-width:1; }
.chart-axis { fill:var(--muted); font:10px var(--mono); }
.chart-wti { stroke:#c98618; } .chart-brent { stroke:#2b6c9e; } .chart-metric { stroke:var(--teal); }
.chart-path { fill:none; stroke-width:1.8; vector-effect:non-scaling-stroke; }
.chart-zero { stroke:#a9a296; stroke-dasharray:4 4; }
.chart-crosshair { stroke:#887f72; stroke-dasharray:3 3; }
.chart-tooltip { position:absolute; pointer-events:none; display:none; z-index:4; min-width:210px; padding:10px; background:rgba(23,33,31,.94); color:white; border-radius:8px; font:11px/1.55 var(--mono); box-shadow:0 10px 30px rgba(0,0,0,.18); }
.legend { display:flex; flex-wrap:wrap; gap:14px; margin-top:4px; color:var(--muted); font-size:11px; }
.legend span:before { content:""; display:inline-block; width:16px; height:2px; margin-right:6px; vertical-align:middle; background:currentColor; }
.legend .wti { color:#c98618; } .legend .brent { color:#2b6c9e; } .legend .metric { color:var(--teal); }
.side-stack { display:grid; gap:12px; position:sticky; top:72px; }
.fact { display:flex; justify-content:space-between; gap:16px; padding:7px 0; border-top:1px solid #e9e4da; }
.fact:first-child { border-top:0; }
.fact span { color:var(--muted); }
.fact strong { text-align:right; font-family:var(--mono); }
.contribution { margin:12px 0; }
.contribution-bar { height:12px; display:flex; overflow:hidden; background:#eee9df; border-radius:99px; }
.contribution-bar i:first-child { background:#c98618; } .contribution-bar i:last-child { background:#2b6c9e; }
.diag { padding:15px; border-left:4px solid var(--teal); min-width:0; overflow-wrap:anywhere; }
.diag.watch { border-left-color:var(--amber); } .diag.blocked { border-left-color:var(--red); }
.diag ul { margin:7px 0 0; padding-left:18px; color:var(--muted); min-width:0; }
.diag li,.diag .metric-note { overflow-wrap:anywhere; word-break:break-word; }
.diag-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
.execution-controls { display:flex; flex-wrap:wrap; gap:10px; justify-content:space-between; margin-bottom:10px; }
.ex-status { font-weight:750; } .ex-status.full_fill { color:var(--green); } .ex-status.partial_or_blocked { color:var(--red); }
.method-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }
.method { padding:15px; }
.method code { display:block; margin:7px 0; color:var(--teal); font:12px var(--mono); }
.empty { padding:34px; text-align:center; color:var(--muted); }
.skeleton { background:linear-gradient(90deg,#ece8df,#f7f4ed,#ece8df); background-size:200% 100%; animation:shine 1.2s linear infinite; border-radius:8px; min-height:120px; }
@keyframes shine { to { background-position:-200% 0; } }
@media(max-width:1000px){ .oil-layout { grid-template-columns:1fr; } .side-stack { position:static; grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media(max-width:680px){ .side-stack,.method-grid { grid-template-columns:minmax(0,1fr); } .diag-grid { grid-template-columns:minmax(0,1fr); min-width:0; } .chart-wrap,.chart-wrap svg { min-height:300px; height:300px; } }
"""


OIL_JS = r"""
const state={data:null,source:null,range:'30d',metric:'residual_z',direction:'long_brent_short_wti',size:500};
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=(v,d=2,signed=false)=>v==null||!Number.isFinite(Number(v))?'—':(signed&&Number(v)>0?'+':'')+Number(v).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
const money=(v,d=2)=>v==null?'—':(Number(v)<0?'−$':'$')+Math.abs(Number(v)).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
const metricLabel={spread_usd:'美元价差',ratio:'价格比值',log_ratio:'对数比值',residual:'参考残差',residual_z:'残差 z'};
const rangeMs={"24h":864e5,"7d":7*864e5,"30d":30*864e5,"1y":365*864e5,all:Infinity};
function statusLabel(v){return v==='ok'?'可用':v==='unavailable'?'不可用':v==='full_fill'?'完整成交':v==='partial_or_blocked'?'部分成交或阻断':v;}
function reasonLabel(v){return ({NO_LOCAL_RECORDINGS:'等待 monte-fox 只读市场录制',FEE_UNKNOWN:'账户费率未知',ENTRY_DEPTH_INSUFFICIENT:'进场深度不足',EXIT_DEPTH_INSUFFICIENT:'退出深度不足',ONE_TO_ONE_QUANTITY_BASELINE_NOT_BETA_HEDGED:'当前按 1:1 数量比较，尚未按 beta 对冲',CONTRACT_WEIGHT_AND_HEDGE_RATIO_UNVERIFIED:'合约权重与执行对冲比率未核验',HOLDING_FUNDING_UNKNOWN:'持有期 Funding 未知',SAME_FROZEN_BOOK_EXIT_BASELINE:'同一冻结盘口往返基线',FUTURE_EXIT_STATE_UNKNOWN:'未来退出盘口未知'}[v]||v);}
function priceKindLabel(v){return ({perp_candle_close:'永续 1h 收盘',hip3_perp_candle_close:'HIP-3 永续 1h 收盘',continuous_futures_daily_close:'连续期货日线收盘',economic_reference_index:'经济参考指数',indicative_rfq_mid:'指定数量指示性 RFQ 中点'}[v]||v);}
function formatUtc(v){if(!v)return'—';return String(v).replace('T',' ').replace('Z',' UTC').slice(0,20)+' UTC';}
function source(){return state.data.sources.find(x=>x.key===state.source)||state.data.sources[0];}
function visiblePoints(){const s=source(); if(!s)return[]; const pts=s.points||[]; if(state.range==='all'||!pts.length)return pts; const cutoff=pts[pts.length-1].timestamp_ms-rangeMs[state.range]; return pts.filter(p=>p.timestamp_ms>=cutoff);}
function setButtons(selector,value){document.querySelectorAll(selector).forEach(b=>b.classList.toggle('on',b.dataset.value===String(value)));}
function initializeControls(){
 const sel=$('source'); sel.innerHTML=state.data.sources.map(s=>`<option value="${esc(s.key)}">${esc(s.label)} · ${statusLabel(s.status)}</option>`).join('');
 const preferred=state.data.dashboard.primary_source; state.source=state.data.sources.some(s=>s.key===preferred)?preferred:state.data.sources[0]?.key; sel.value=state.source;
 const sizes=state.data.execution?.sizes_usd||[100,500,1000]; state.size=sizes.includes(500)?500:sizes[0]; $('sizes').innerHTML=sizes.map(x=>`<button data-value="${x}">$${Number(x).toLocaleString()}</button>`).join('');
 sel.onchange=e=>{state.source=e.target.value;render();};
 document.querySelectorAll('#ranges button').forEach(b=>b.onclick=()=>{state.range=b.dataset.value;render();});
 document.querySelectorAll('#metrics button').forEach(b=>b.onclick=()=>{state.metric=b.dataset.value;render();});
 document.querySelectorAll('#directions button').forEach(b=>b.onclick=()=>{state.direction=b.dataset.value;renderExecution();});
 $('sizes').querySelectorAll('button').forEach(b=>b.onclick=()=>{state.size=Number(b.dataset.value);renderExecution();});
}
function render(){setButtons('#ranges button',state.range);setButtons('#metrics button',state.metric);const s=source();$('source-meta').textContent=`${priceKindLabel(s.price_kind)} · ${s.interval} · ${s.sample_count.toLocaleString()} 个同步点`;renderMetrics(s);renderChart(s);renderModel(s);renderHealth();renderDiagnostics();renderExecution();}
function renderMetrics(s){const x=s.summary||{};const z=x.residual_z;const items=[['Brent − WTI',money(x.spread_usd),'美元距离，不是利润'],['Price ratio',num(x.ratio,4),'Brent ÷ WTI'],['Log ratio',num(x.log_ratio,5),'ln(Brent) − ln(WTI)'],['Frozen residual z',num(z,2,true),z==null?'形成样本不足':Math.abs(z)>=2?'偏离形成样本中心':'位于形成样本常见范围']];$('summary-cards').innerHTML=items.map(([a,b,c])=>`<div class="card card-pad"><div class="metric-label">${a}</div><div class="metric-value">${b}</div><div class="metric-note">${c}</div></div>`).join('');}
function svgPath(points,x,y,key){let d='';points.forEach((p,i)=>{const v=p[key];if(v==null||!Number.isFinite(Number(v)))return;d+=(d?'L':'M')+x(p.timestamp_ms).toFixed(2)+','+y(Number(v)).toFixed(2);});return d;}
function ticks(min,max,n=5){if(!Number.isFinite(min)||!Number.isFinite(max))return[];if(min===max){min-=1;max+=1;}return Array.from({length:n},(_,i)=>min+(max-min)*i/(n-1));}
function renderChart(s){const pts=visiblePoints();const root=$('chart');if(!pts.length){root.innerHTML=`<div class="empty">${esc(s.reason||'该价格源没有可用同步观察')}</div>`;return;}const W=1040,H=350,pad={l:55,r:58,t:18,b:30},topH=205,gap=36,bottomTop=topH+gap,bottomH=H-bottomTop-pad.b;const ts=pts.map(p=>p.timestamp_ms),prices=pts.flatMap(p=>[p.wti,p.brent]).filter(Number.isFinite),metrics=pts.map(p=>p[state.metric]).filter(v=>v!=null&&Number.isFinite(Number(v))).map(Number);let pmin=Math.min(...prices),pmax=Math.max(...prices),mmin=Math.min(...metrics),mmax=Math.max(...metrics);let pm=(pmax-pmin||1)*.08,mm=(mmax-mmin||1)*.12;pmin-=pm;pmax+=pm;mmin-=mm;mmax+=mm;if(state.metric.includes('residual')){const a=Math.max(Math.abs(mmin),Math.abs(mmax));mmin=-a;mmax=a;}const x=v=>pad.l+(v-ts[0])/(ts[ts.length-1]-ts[0]||1)*(W-pad.l-pad.r),yp=v=>pad.t+(pmax-v)/(pmax-pmin)*(topH-pad.t),ym=v=>bottomTop+(mmax-v)/(mmax-mmin)*bottomH;const priceTicks=ticks(pmin,pmax),metricTicks=ticks(mmin,mmax);let grid=priceTicks.map(v=>`<line class="chart-grid" x1="${pad.l}" y1="${yp(v)}" x2="${W-pad.r}" y2="${yp(v)}"/><text class="chart-axis" x="${pad.l-8}" y="${yp(v)+3}" text-anchor="end">$${num(v,2)}</text>`).join('');grid+=metricTicks.map(v=>`<line class="chart-grid" x1="${pad.l}" y1="${ym(v)}" x2="${W-pad.r}" y2="${ym(v)}"/><text class="chart-axis" x="${W-pad.r+8}" y="${ym(v)+3}">${num(v,state.metric==='ratio'?4:2)}</text>`).join('');if(mmin<0&&mmax>0)grid+=`<line class="chart-zero" x1="${pad.l}" y1="${ym(0)}" x2="${W-pad.r}" y2="${ym(0)}"/>`;const dateTicks=ticks(ts[0],ts[ts.length-1],6);grid+=dateTicks.map(v=>`<text class="chart-axis" x="${x(v)}" y="${H-5}" text-anchor="middle">${new Date(v).toLocaleDateString('zh-CN',{month:'2-digit',day:'2-digit'})}</text>`).join('');root.innerHTML=`<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${grid}<path class="chart-path chart-wti" d="${svgPath(pts,x,yp,'wti')}"/><path class="chart-path chart-brent" d="${svgPath(pts,x,yp,'brent')}"/><path class="chart-path chart-metric" d="${svgPath(pts,x,ym,state.metric)}"/><line id="crosshair" class="chart-crosshair" style="display:none" y1="${pad.t}" y2="${H-pad.b}"/></svg><div id="tooltip" class="chart-tooltip"></div><div class="legend"><span class="wti">WTI</span><span class="brent">Brent</span><span class="metric">${metricLabel[state.metric]}</span></div>`;const svg=root.querySelector('svg'),tip=$('tooltip'),cross=$('crosshair');svg.onpointermove=e=>{const r=svg.getBoundingClientRect(),px=(e.clientX-r.left)/r.width*W;const target=ts[0]+(px-pad.l)/(W-pad.l-pad.r)*(ts[ts.length-1]-ts[0]);let best=pts.reduce((a,b)=>Math.abs(b.timestamp_ms-target)<Math.abs(a.timestamp_ms-target)?b:a);const cx=x(best.timestamp_ms);cross.setAttribute('x1',cx);cross.setAttribute('x2',cx);cross.style.display='block';tip.style.display='block';tip.style.left=Math.min(r.width-225,Math.max(5,e.clientX-r.left+12))+'px';tip.style.top=Math.max(5,e.clientY-r.top-75)+'px';tip.innerHTML=`${new Date(best.timestamp_ms).toLocaleString('zh-CN')}<br><span style="color:#e8ad4c">WTI ${money(best.wti)}</span> · <span style="color:#75b5e5">Brent ${money(best.brent)}</span><br>${metricLabel[state.metric]} <b>${num(best[state.metric],state.metric==='ratio'?4:2,true)}</b>`;};svg.onpointerleave=()=>{cross.style.display='none';tip.style.display='none';};}
function renderModel(s){const m=s.model,c=s.leg_contribution;if(!m){$('model').innerHTML='<div class="empty">样本不足，不能冻结模型。</div>';return;}let bars='';if(c){const a=Math.abs(c.wti_log_change_bps),b=Math.abs(c.brent_log_change_bps),total=a+b||1;bars=`<div class="contribution"><div class="contribution-bar"><i style="width:${a/total*100}%"></i><i style="width:${b/total*100}%"></i></div><div class="fact"><span>${num(c.elapsed_ms/36e5,1)} 小时变化主导</span><strong>${esc(c.dominant_leg)}</strong></div><div class="fact"><span>WTI / Brent</span><strong>${num(c.wti_log_change_bps,1,true)} / ${num(c.brent_log_change_bps,1,true)} bps</strong></div></div>`;}$('model').innerHTML=`<div class="fact"><span>Formation / validation</span><strong>${m.formation_count} / ${m.validation_count}</strong></div><div class="fact"><span>Formation UTC</span><strong>${esc(formatUtc(m.formation_start_utc))}<br>${esc(formatUtc(m.formation_end_utc))}</strong></div><div class="fact"><span>参数来源</span><strong>${m.model_origin==='reused'?'复用既有冻结模型':'本次形成期拟合'}</strong></div><div class="fact"><span>alpha</span><strong>${num(m.alpha,6,true)}</strong></div><div class="fact"><span>beta</span><strong>${num(m.beta,4)}</strong></div><div class="fact"><span>residual center</span><strong>${num(m.center,6,true)}</strong></div><div class="fact"><span>robust scale</span><strong>${num(m.scale,6)}</strong></div>${bars}`;}
function renderHealth(){$('health').innerHTML=state.data.sources.map(s=>{const h=s.health||{};const gap=h.gap_evaluation==='requires_exchange_calendar'?'需交易所日历':h.gap_count??'—';return `<tr><td><strong>${esc(s.label)}</strong><br><span class="muted">${esc(priceKindLabel(s.price_kind))}</span></td><td><span class="pill ${s.status==='ok'?'ok':'blocked'}">${statusLabel(s.status)}</span></td><td class="mono">${s.sample_count.toLocaleString()}</td><td class="mono">${esc(formatUtc(h.first_at))}<br>${esc(formatUtc(h.last_at))}</td><td>${esc(gap)}</td><td>${esc(s.reason?reasonLabel(s.reason):'—')}</td><td><a class="button secondary" href="/workbench/api/oil.csv?source=${encodeURIComponent(s.key)}">CSV</a></td></tr>`;}).join('');}
function renderDiagnostics(){$('diagnostics').innerHTML=(state.data.diagnostics||[]).map(d=>`<article class="card diag ${esc(d.severity)}"><div style="display:flex;justify-content:space-between;gap:8px"><h3>${esc(d.title)}</h3><span class="pill ${d.severity==='blocked'?'blocked':d.severity==='watch'?'warn':'ok'}">${esc(d.severity)}</span></div><ul>${(d.evidence||[]).map(x=>`<li><strong>证据：</strong>${esc(x)}</li>`).join('')}${(d.counter_evidence||[]).map(x=>`<li><strong>相反/无关：</strong>${esc(x)}</li>`).join('')}${(d.limitations||[]).map(x=>`<li><strong>限制：</strong>${esc(x)}</li>`).join('')}</ul><div class="metric-note" style="margin-top:8px">下一项：${esc(d.next_check||'—')}</div></article>`).join('')||'<div class="empty">当前没有自动诊断。</div>';}
function renderExecution(){setButtons('#directions button',state.direction);setButtons('#sizes button',state.size);const venues=state.data.execution?.venues||[];const rows=[];venues.forEach(v=>{const r=(v.rows||[]).find(x=>x.direction===state.direction&&Number(x.size_usd)===Number(state.size));if(r)rows.push({...r,venue:v.venue,basis:v.basis});});$('execution-body').innerHTML=rows.map(r=>`<tr><td><strong>${esc(r.venue)}</strong><br><span class="pill">${r.basis==='l2_book'?'L2 盘口':esc(r.basis)}</span></td><td class="ex-status ${esc(r.status)}">${statusLabel(r.status)}</td><td class="mono">${num(r.quantity,4)}</td><td class="mono">${num(r.entry_fill_pct,1)}%</td><td class="mono">${num(r.entry_residual_qty,4)}</td><td class="mono">${num(r.exit_fill_pct,1)}%</td><td class="mono">${num(r.residual_open_qty,4)}</td><td class="mono">${num(r.entry_crossing_bps,2,true)} bps</td><td class="mono">${num(r.round_trip_friction_bps,2)} bps</td><td>${r.fees_known?'<span class="pill ok">已知</span>':'<span class="pill blocked">未知</span>'}</td><td>${(r.reason_codes||[]).map(x=>`<span class="pill">${esc(reasonLabel(x))}</span>`).join('')||'—'}</td></tr>`).join('')||'<tr><td colspan="11" class="empty">该方向/规模没有可用冻结盘口。</td></tr>';}
async function boot(){try{const r=await fetch('/workbench/api/oil',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);state.data=await r.json();initializeControls();render();$('loading').style.display='none';$('content').style.display='block';}catch(e){$('loading').className='card empty';$('loading').textContent='加载失败：'+e.message;}}
boot();
"""


def render_oil_html() -> str:
    page = _shell_start("Brent–WTI 相对价值 · MonteLab", "oil")
    page += f"""<style>{OIL_CSS}</style><main class="shell">
<section class="hero"><div><div class="eyebrow">Relative Value · Oil</div><h1>Brent–WTI 相对价值</h1>
<p class="lede">把“Brent 比 WTI 贵多少”拆成价格源、历史关系、冻结模型、机制诊断与指定规模执行摩擦。美元价差、比值、残差和可执行价格各自回答不同问题。</p></div>
<div class="hero-meta"><span class="pill ok">只读研究</span><a class="button secondary" href="/workbench/api/oil">下载 JSON</a></div></section>
<div id="loading" class="skeleton"></div><div id="content" style="display:none">
<section class="card toolbar"><div class="toolbar-group"><label class="metric-label" for="source">价格源</label><select id="source"></select><span id="source-meta" class="muted mono"></span></div>
<div class="toolbar-group"><div id="ranges" class="seg"><button data-value="24h">24h</button><button data-value="7d">7d</button><button data-value="30d" class="on">30d</button><button data-value="1y">1y</button><button data-value="all">ALL</button></div>
<div id="metrics" class="seg"><button data-value="spread_usd">$ spread</button><button data-value="ratio">ratio</button><button data-value="log_ratio">log ratio</button><button data-value="residual_z" class="on">residual z</button></div></div></section>
<section id="summary-cards" class="grid grid-4 section"></section>
<section class="oil-layout section"><div class="card chart-card"><div class="chart-title"><div><h2>同步价格与相对关系</h2><div class="section-kicker">先逐时间点计算，再显示所选范围；不把分别聚合的 OHLC 相除。</div></div></div><div id="chart" class="chart-wrap"></div></div>
<aside class="side-stack"><div class="card card-pad"><div class="eyebrow">Frozen model</div><h3 style="margin:6px 0 10px">形成窗口后冻结</h3><div id="model"></div></div>
<div class="card card-pad"><div class="eyebrow">Mental model</div><h3 style="margin:6px 0 9px">四个量，四个问题</h3><div class="fact"><span>美元价差</span><strong>价格距离</strong></div><div class="fact"><span>比值</span><strong>相对水平</strong></div><div class="fact"><span>残差</span><strong>模型偏离</strong></div><div class="fact"><span>执行区间</span><strong>可成交摩擦</strong></div></div></aside></section>
<section class="section"><div class="section-head"><div><h2>机制诊断</h2><div class="section-kicker">确定性证据摘要，同时显示相反证据与限制；不是标准答案。</div></div></div><div id="diagnostics" class="diag-grid"></div></section>
<section class="section"><div class="section-head"><div><h2>指定规模执行摩擦</h2><div class="section-kicker">L2 与 RFQ 分开建模；同一冻结盘口往返只是摩擦基线。</div></div></div>
<div class="card card-pad"><div class="execution-controls"><div id="directions" class="seg"><button data-value="long_brent_short_wti" class="on">Long Brent / Short WTI</button><button data-value="long_wti_short_brent">Long WTI / Short Brent</button></div><div id="sizes" class="seg"></div></div>
<div class="boundary" style="margin:8px 0 12px">当前执行表按两腿 <strong>1:1 场所数量</strong>给出 L2 摩擦基线；它不是冻结模型 beta 对冲，也不证明经济中性。合约权重与可执行对冲比率核验前，不计算策略 PnL。</div>
<div class="table-wrap"><table><thead><tr><th>Venue</th><th>Status</th><th>共同数量</th><th>进场成交率</th><th>进场残余</th><th>退出成交率</th><th>退出后未关闭</th><th>进场 crossing</th><th>冻结盘口往返摩擦</th><th>Fees</th><th>阻断项</th></tr></thead><tbody id="execution-body"></tbody></table></div></div></section>
<section class="section"><div class="section-head"><div><h2>数据健康与导出</h2><div class="section-kicker">原始响应保存在 Git 外；这里提供稳定研究投影与 CSV。</div></div><a class="button secondary" href="/workbench/data">数据目录</a></div>
<div class="card card-pad" style="margin-bottom:10px"><strong>Variational 只读导入</strong><p class="muted" style="margin:5px 0 0">先由 monte-fox 生成脱敏的 <code>market_observation</code> 录制，再运行：<code>PYTHONPATH=src python3 -m monte_arb.oil_relative_value --variational-runtime /path/to/recordings</code>。账户、订单与执行事件不会进入研究投影。</p></div>
<div class="card table-wrap"><table><thead><tr><th>价格源</th><th>状态</th><th>样本</th><th>覆盖</th><th>缺口</th><th>原因</th><th>导出</th></tr></thead><tbody id="health"></tbody></table></div></section>
<section class="section"><div class="section-head"><div><h2>方法与边界</h2><div class="section-kicker">这些概念将复用于 Funding、Screener 与任意两腿 Grapher。</div></div></div>
<div class="method-grid"><div class="card method"><h3>美元价差</h3><code>Brent − WTI</code><p class="muted">保留直观的美元距离，但油价水平变化会改变同样百分比关系对应的美元值。</p></div><div class="card method"><h3>对数比值</h3><code>ln(Brent) − ln(WTI)</code><p class="muted">把两腿百分比变化相减，仍不代表指定数量可以成交。</p></div><div class="card method"><h3>冻结参考残差</h3><code>ln(B) − α − β ln(W)</code><p class="muted">参数只从形成窗口估计；验证窗口不参与拟合，避免用未来信息重写历史。</p></div><div class="card method"><h3>执行摩擦</h3><code>direction × size × L2/RFQ</code><p class="muted">按真实方向和数量计算；费用、funding 或未来退出未知时保持未知。</p></div></div></section>
</div></main><script>{OIL_JS}</script>"""
    return page + _shell_end()


def render_data_html(projection: Mapping[str, Any]) -> str:
    rows = []
    for source in projection.get("sources", []):
        if not isinstance(source, Mapping):
            continue
        source_health = source.get("health")
        health: Mapping[str, Any] = (
            source_health if isinstance(source_health, Mapping) else {}
        )
        rows.append(
            f"""<tr><td><strong>{html.escape(str(source.get('label')))}</strong><br><span class="muted mono">{html.escape(str(source.get('key')))}</span></td>
<td>{html.escape(str(source.get('price_kind')))}</td><td>{source.get('sample_count',0)}</td><td class="mono">{html.escape(str(health.get('first_at') or '—'))}<br>{html.escape(str(health.get('last_at') or '—'))}</td>
<td>{health.get('gap_count','—')}</td><td>{html.escape(str(source.get('reason') or '—'))}</td><td><a class="button secondary" href="/workbench/api/oil.csv?source={html.escape(str(source.get('key')))}">CSV</a></td></tr>"""
        )
    page = _shell_start("数据目录 · MonteLab", "data")
    page += f"""<main class="shell"><section class="hero"><div><div class="eyebrow">Datasets & Jobs</div><h1>数据目录</h1><p class="lede">页面使用派生研究投影；原始场所响应按采集批次保存在 Git 外。下载接口面向 Python、Jupyter 和后续二次开发。</p></div><div class="hero-meta"><a class="button primary" href="/workbench/api/oil">下载油专题 JSON</a></div></section>
<section class="section"><div class="card table-wrap"><table><thead><tr><th>Source</th><th>Price kind</th><th>Samples</th><th>Coverage UTC</th><th>Gaps</th><th>Reason</th><th>Export</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
<section class="section"><div class="grid grid-2"><div class="card card-pad"><h2>重新生成</h2><p class="muted">公开数据：</p><p class="mono">PYTHONPATH=src python -m monte_arb.oil_relative_value</p><p class="muted">Variational 仅在明确提供 monte-fox runtime 目录时导入市场观察。</p></div><div class="card card-pad"><h2>数据规则</h2><p class="muted">同一价格源内精确同步；不使用未来值或隐式前值补缺。JSON 提供完整投影，CSV 提供单一价格源的可分析指标。</p></div></div></section></main>"""
    return page + _shell_end()


def render_placeholder_html(active: str, title: str, description: str) -> str:
    page = _shell_start(f"{title} · MonteLab", active)
    page += f"""<main class="shell"><section class="hero"><div><div class="eyebrow">Module Roadmap</div><h1>{html.escape(title)}</h1><p class="lede">{html.escape(description)}</p></div><div class="hero-meta"><span class="pill warn">planned</span></div></section>
<section class="section"><div class="card card-pad"><h2>为什么现在不做空壳</h2><p class="muted">该模块会在底层数据集、采集器和分析接口达到最低证据标准后实施。当前优先完成 Brent–WTI 纵向能力，再抽出可复用接口。</p><p><a class="button primary" href="/workbench">返回 Dashboard</a></p></div></section></main>"""
    return page + _shell_end()
