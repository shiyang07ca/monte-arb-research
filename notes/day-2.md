# Day 2 / 2026-08-06 — Lighter 原始数据审计教学

## 今日唯一问题

拿到 WTI/BRENTOIL 的真实 API 快照时，能否在谈相关性或价差之前，独立判断数据身份、时间范围、重复/缺失、数值质量和两腿可比性？

## 教学产出

- `lessons/0001-day2-audit-lighter-rwa.html`：短 HTML lesson；
- `reference/day2-lighter-rwa-audit-cheatsheet.html`：reference cheat sheet；
- `lessons/day2-real-data-exercise.md`：绑定真实仓库数据的练习；
- `assets/course.css`：课程共用样式；
- `lessons/README.md`：教学工作区入口。

## 真实输入

- `lab/data/lighter_rwa_raw/WTI_candles_1h.json`；
- `lab/data/lighter_rwa_raw/BRENTOIL_candles_1h.json`；
- 两腿 funding、orderBookDetails；
- `lab/data/lighter_rwa_capture_manifest.json`；
- `lab/data/lighter_rwa_data_audit.json`；
- `lab/data/lighter_rwa_aligned_1h.jsonl`。

## 复现结果

```text
common_rows: 500
log_return_correlation: 0.970903148909904
daily_duplicate_rows: WTI=0, BRENTOIL=0
decision: BLOCKED_FOR_STRATEGY_CONCLUSION
```

共同窗口为 `2026-07-16T05:00:00+00:00` 至 `2026-08-06T00:00:00+00:00`，约 21 天。funding 两腿各 750 条 1h 记录，但仍不能替代账户 funding 现金账本。

## 教学边界

本课只读、不认证、不发单、不连接私钥。`common_rows=500` 是共同观察数，不是充分历史；收益相关性是描述性统计，不是协整、均值回归、净 PnL 或执行能力证明。

## 学习验收

等待用户完成 `lessons/day2-real-data-exercise.md` 的四个场景回答后，再按“具体场景 → 用户解释 → 只纠正关键错误 → 新场景迁移”反馈；不能把课程材料阅读完成写成学习通过。

## 状态

- 学习：待用户完成练习后验收；
- 策略研究：`Blocked`；
- 真实执行：`No-Go`。

## Sources

- `RESOURCES.md` 中的 Lighter Candles、Fundings、Order Book Details、RWA 定价和展期官方链接。
