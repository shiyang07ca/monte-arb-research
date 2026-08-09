# Day 5｜展期与市场状态模型

## 研究问题

价差变化来自相对价值，还是来自两个期货合约的不同展期和不同底层市场状态？

## 官方规则（需带来源时间）

来源：Lighter [Futures Contract Price Rolling Mechanism](https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism)。本地教学快照保存于 `lab/data/day5_roll_session_snapshot.json`。

- WTI、BRENTOIL 等 RWA 使用期货合约作为底层价格。
- 在第 5 至第 10 个工作日之间，当前月到下月逐步切换。
- 每天切换 20%。
- WTI 每日 17:30 ET 开始；BRENTOIL 每日 19:00 ET 开始。
- WTI 底层市场关闭 17:00–18:00 ET；BRENTOIL 关闭 18:00–20:00 ET。

## 时区模型

官方日程使用 `America/New_York`，原始 candles 的时间统一按 UTC 处理。2026 年 8 月为 EDT（UTC−4）：

```text
WTI       17:30 ET → 21:30 UTC
BRENTOIL  19:00 ET → 23:00 UTC
```

不能固定写 UTC−4 或 UTC−5；必须让时区库处理夏令时。

## 状态字段

每个共同小时保留原始价格，并增加：

```text
timestamp_utc
wti_roll_window
brentoil_roll_window
wti_underlying_closed
brentoil_underlying_closed
wti_roll_stage
brentoil_roll_stage
comparability_status
exclusion_reason
```

### 处理政策

1. **全样本**：保留全部样本和状态标签，报告异常。
2. **排除展期/关闭窗口**：只做敏感性分析，不覆盖全样本结果。
3. **按展期阶段分层**：比较不同阶段的价差和收益，但不把分层差异自动解释为套利。
4. **缺字段**：写 `unknown`；不使用上一小时价格填充，不静默删除。

## 关键边界

- 底层关闭窗口不自动证明 Lighter 市场不可交易。
- 逐小时 candle timestamp 的区间边界尚未核实。
- 现有共同样本为 `2026-07-15T19:00:00Z`–`2026-08-05T14:00:00Z`，500 行，在 2026-08-07 展期开始前结束。
- 因此现有快照不能证明 2026 年 8 月展期期间的真实价格反应。
- 真实市场状态、oracle freshness、连续深度、成交与退出仍未知。

## 后续

补采覆盖完整展期窗口后，先生成状态表，再分别比较全样本、剔除窗口和按阶段分层结果；禁止先看结果再调整标签规则。
