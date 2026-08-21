"""Turn a market-event analysis report into a lesson data file.

Reads a ``day15-analysis-*.json`` report and writes
``assets/day15-continuous-data.js`` exposing a single ``DAY15`` global.
Candidate selection is honest: it uses whatever the real capture produced and
falls back to the saved 500-hour history when the bounded capture is too quiet
to produce a window of that class.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Optional


def _pick(rows: list[dict[str, Any]], classification: str) -> Optional[dict[str, Any]]:
    matches = [row for row in rows if row.get("classification") == classification]
    if not matches:
        return None
    matches.sort(key=lambda row: row["duration_s"])
    return matches[0]


MARKET_LABELS = {
    "145": "WTI (Lighter)",
    "159": "BRENTOIL (Lighter)",
    "xyz:CL": "xyz:CL (Hyperliquid)",
    "xyz:BRENTOIL": "xyz:BRENTOIL (Hyperliquid)",
}


def _label(market: str) -> str:
    return MARKET_LABELS.get(market, market)


def _fmt_bps(value: float) -> str:
    return f"{value:.2f} bps"


def build_candidates(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    windows = report.get("anomaly_windows") or []
    baselines = {row["market"]: row for row in report.get("baselines") or []}
    history = report.get("hour_history") or []
    candidates: list[dict[str, Any]] = []

    # A: transient from the live capture, or the largest single-spike event.
    transient = _pick(windows, "transient")
    connects = {
        h["venue"]: h.get("at_utc")
        for h in report.get("health_events") or []
        if h.get("kind") == "CONNECTED"
    }
    if transient is not None:
        diagnosis = (
            "窗口内事件数与前后基线一致，无健康事件重叠，可排除断连假象；"
            "但单次出现，无法从这一次判断可复现性。"
        )
        start_iso = transient["start_utc"]
        connect_iso = connects.get(transient["venue"])
        if connect_iso:
            from datetime import datetime

            try:
                start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                conn_dt = datetime.fromisoformat(connect_iso.replace("Z", "+00:00"))
                since_connect_s = (start_dt - conn_dt).total_seconds()
                if 0 <= since_connect_s < 30:
                    diagnosis += (
                        f" 注意：异常发生在连接后仅 {since_connect_s:.0f} 秒，"
                        "初始快照可能包含连接前的盘口状态，需先排除快照假象。"
                    )
            except ValueError:
                pass
        candidates.append(
            {
                "kind": "transient",
                "title": "一次越过自身基线 3–20 秒后恢复的价差尖峰",
                "description": (
                    f"真实采集期间，{_label(transient['market'])} 价差在 "
                    f"{transient['start_utc']} 越过阈值，峰值 "
                    f"{_fmt_bps(transient['peak'])}（阈值 {_fmt_bps(transient['threshold'])}，"
                    f"为阈值的 {transient['ratio']:.1f} 倍），持续 "
                    f"{transient['duration_s']:.1f} 秒后回到自身基线。"
                ),
                "evidence": {
                    "市场": _label(transient["market"]),
                    "开始": transient["start_utc"],
                    "结束": transient["end_utc"],
                    "持续时间": f"{transient['duration_s']:.1f} s",
                    "峰值价差": _fmt_bps(transient["peak"]),
                    "基线中位价差": _fmt_bps(
                        baselines.get(transient["market"], {}).get("spread_median_bps", 0.0)
                    ),
                    "峰值/阈值": f"{transient['ratio']:.2f}×",
                },
                "diagnosis": diagnosis,
            }
        )
    else:
        candidates.append(
            {
                "kind": "transient",
                "title": "本次采集没有出现达到窗口标准的瞬时异常",
                "description": (
                    "有界采集期内所有越界都不足 3 秒窗口或未越过阈值。这本身就是证据："
                    "在安静时段，单次快照看到的'价差'大多不是异常。"
                ),
                "evidence": {
                    "异常窗口数": str(len(windows)),
                    "采集覆盖": f"{report['session_meta'].get('duration_s', 0):.0f} s",
                },
                "diagnosis": "负结果同样进入工作台：候选榜不应为凑数制造异常。",
            }
        )

    # B: repeating from capture, else the widest-baseline market as a persistent feature.
    repeating = [w for w in windows if w.get("classification") in ("repeating", "persistent")]
    if repeating:
        chosen = max(repeating, key=lambda w: w["ratio"])
        candidates.append(
            {
                "kind": "repeating" if chosen["classification"] == "repeating" else "persistent",
                "title": (
                    "同特征反复越界（repeating）"
                    if chosen["classification"] == "repeating"
                    else "长时间不回落的持续越界（persistent）"
                ),
                "description": (
                    f"{_label(chosen['market'])} 在本次采集中出现 {chosen['repeats']} 个越界窗口，"
                    f"峰值 {_fmt_bps(chosen['peak'])}（阈值 {_fmt_bps(chosen['threshold'])}），"
                    f"最长窗口 {chosen['duration_s']:.1f} 秒。"
                ),
                "evidence": {
                    "市场": _label(chosen["market"]),
                    "窗口数": str(chosen["repeats"]),
                    "峰值/阈值": f"{chosen['ratio']:.2f}×",
                    "最长窗口": f"{chosen['duration_s']:.1f} s",
                },
                "diagnosis": (
                    "先对照健康事件排除管道假象，再进入事件研究：什么触发、持续多久、"
                    "什么条件恢复。"
                ),
            }
        )
    else:
        wide = sorted(
            baselines.values(), key=lambda b: b.get("spread_median_bps", 0.0), reverse=True
        )
        if wide:
            widest = wide[0]
            other_medians = [
                f"{_label(b['market'])}={b['spread_median_bps']:.2f}"
                for b in wide[1:3]
            ]
            candidates.append(
                {
                    "kind": "persistent",
                    "title": "一个市场自身基线的价差就系统性高于其他市场",
                    "description": (
                        f"{_label(widest['market'])} 的价差中位数 {_fmt_bps(widest['spread_median_bps'])}"
                        f" 显著宽于同场其他市场（{'、'.join(other_medians)}）。"
                        "这是连续数据暴露的持续特征，不是单次快照偶然。"
                    ),
                    "evidence": {
                        "市场": _label(widest["market"]),
                        "价差中位": _fmt_bps(widest["spread_median_bps"]),
                        "价差 p95": _fmt_bps(widest["spread_p95_bps"]),
                        "更新间隔中位": f"{widest['interarrival_median_s']:.2f} s",
                        "静默缺口": str(widest["silent_gap_count"]),
                    },
                    "diagnosis": (
                        "持续宽价差 + 稀疏更新 + 浅深度三者要一起看：宽价差可能是流动性"
                        "结构（真实），也可能是数据管道只收到部分更新（假象）。"
                    ),
                }
            )

    # C: hour-of-day structure from the saved 500-hour history.
    structural_hours = [h for h in history if h.get("structural")]
    if structural_hours:
        peak = max(structural_hours, key=lambda h: h["volume_median_base"])
        quiet = min(history, key=lambda h: h["volume_median_base"]) if history else None
        candidates.append(
            {
                "kind": "structural",
                "title": "成交活跃时段与 Brent−WTI 基差一起变化（500 小时真实历史）",
                "description": (
                    f"按 UTC 时段统计：成交量峰值在 {peak['hour_utc']}:00"
                    f"（中位 {peak['volume_median_base']:.0f} base），"
                    + (
                        f"谷值在 {quiet['hour_utc']}:00（{quiet['volume_median_base']:.0f} base）。"
                        if quiet
                        else ""
                    )
                    + " 基差在活跃时段收窄："
                    + "; ".join(
                        f"{h['hour_utc']}:00={h['spread_median_usd']:.2f}$"
                        for h in (peak, quiet)
                        if h
                    )
                ),
                "evidence": {
                    "样本": f"{sum(h['n_rows'] for h in history)} 小时",
                    "活跃时段": ", ".join(f"{h['hour_utc']}:00" for h in structural_hours),
                    "峰值成交量": f"{peak['volume_median_base']:.0f} base",
                    "活跃基差": f"{peak['spread_median_usd']:.3f} $",
                    "安静基差": f"{quiet['spread_median_usd']:.3f} $" if quiet else "—",
                },
                "diagnosis": (
                    "时段相关不等于因果：先对齐外部事件日历（NY 开盘、EIA 发布、维护），"
                    "再检查该时段的逐秒数据健康与盘口深度。"
                ),
            }
        )
    return candidates


def build_js(report: Mapping[str, Any]) -> str:
    baselines = []
    for row in report.get("baselines") or []:
        enriched = dict(row)
        enriched["label"] = _label(str(row.get("market", "?")))
        baselines.append(enriched)
    payload = {
        "schema": report.get("schema"),
        "session_id": report.get("session_id"),
        "baselines": baselines,
        "anomaly_windows": report.get("anomaly_windows") or [],
        "health_events": report.get("health_events") or [],
        "hour_history": report.get("hour_history") or [],
        "candidates": build_candidates(report),
    }
    return (
        "/* Generated by monte_arb.market_event_lesson_data — do not edit by hand. */\n"
        "window.DAY15 = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Day15 lesson data generator")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("assets/day15-continuous-data.js"),
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = json.loads(args.report.read_text(encoding="utf-8"))
    args.output.write_text(build_js(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "baselines": len(report.get("baselines") or []),
                "anomalies": len(report.get("anomaly_windows") or []),
                "candidates": len(build_candidates(report)),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
