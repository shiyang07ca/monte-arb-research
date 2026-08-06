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
research_conclusion: 当前资料不足以判断策略是否成立
```

共同窗口为 `2026-07-16T05:00:00+00:00` 至 `2026-08-06T00:00:00+00:00`，约 21 天。funding 两腿各 750 条 1h 记录，但仍不能替代账户 funding 现金账本。

## 教学边界

本课只读、不认证、不发单、不连接私钥。`common_rows=500` 是共同观察数，不是充分历史；收益相关性是描述性统计，不是协整、均值回归、净 PnL 或执行能力证明。

## 学习验收

本次已通过 Telegram 完成关键场景口述复习：timestamp 匹配、500/499、重复与缺失、相关性边界和 funding 账本边界。尚未在电脑上运行 `lessons/day2-real-data-exercise.md` 的完整命令练习；这不影响今天的概念学习总结。

## 学习总结

- 已掌握：按 `timestamp` 匹配两腿，而不是按数组下标；知道时间戳不一致时不能把价格当作同一时刻比较。
- 已掌握：`500` 根 candle 只能产生 `499` 个相邻收益变化；第一根价格没有前一根价格可比较。
- 已掌握：重复记录为 `0` 只说明没有发现重复 timestamp，不能说明没有缺失或数据完整。
- 已掌握：`common_rows=500` 只表示当前快照的共同小时数量；`0.970903148909904` 只表示短样本收益相关性，不能证明价差收敛、协整或盈利。
- 已掌握：funding API 的 `value/rate/direction` 不能直接等同于个人账户现金流；还需要仓位方向、数量、结算语义、持仓时间和账户账本。

## 研究结论

当前资料仍不足以判断策略是否成立；本课只读，不认证、不发单、不连接私钥。

## 共学打卡

- ICL 课程：`链上套利残酷共学`；课程状态为 ongoing，报名状态为 approved。
- 今天更新了已有 Day 2 打卡记录，没有重复创建当天记录。
- API 更新返回 HTTP `200`，随后按同一记录 ID 回读 HTTP `200`，正文哈希一致；证据见 `lab/data/icl_day2_checkin_write_response.json`。

## Sources

- `RESOURCES.md` 中的 Lighter Candles、Fundings、Order Book Details、RWA 定价和展期官方链接。
