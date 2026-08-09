# Day 5 学习记录 / 展期与市场状态

## 学习目标

把 WTI 与 BRENTOIL 的官方展期时间、底层市场关闭窗口和 UTC candle 时间统一到一个可审计的状态模型中，避免把时间错位制造的价差误判成相对价值信号。

## 今天实际完成

- 读取并核验 Lighter 官方 Futures Contract Price Rolling Mechanism 页面。
- 确认 WTI 每日展期开始于美国东部时间 `17:30`，BRENTOIL 开始于 `19:00`；每日从当前月向下月迁移 `20%`。
- 确认底层市场关闭窗口：WTI `17:00–18:00 ET`，BRENTOIL `18:00–20:00 ET`。
- 使用 `America/New_York` 时区处理夏令时；在 2026 年 8 月示例中，WTI `17:30 ET = 21:30 UTC`，BRENTOIL `19:00 ET = 23:00 UTC`。
- 保存官方 2026 年 8 月展期阶段：8 月 7 日、10 日、11 日、12 日、13 日对应当前月 `80%/60%/40%/20%/0%`。
- 为每个样本设计 `wti_roll_window`、`brentoil_roll_window`、底层关闭状态、展期阶段和 `comparability_status` 标签；异常保留，不静默删除。
- 明确底层关闭窗口不等于已经证明 Lighter 不可下单；真实交易状态、candle 边界、盘口深度和成交行为仍是 `unknown`。
- 通过 Day 5 互动课程：`lessons/0004-day5-roll-session.html`。
- 运行 `python3 lab/day5_roll_session.py` 并通过 `python3 -m unittest lab.test_day5_roll_session -v`，3 个测试通过。

## 关键理解

### 1. 展期改变的是价格组成

展期不是“价格突然异常”，而是底层参考从当前月期货逐步切换到下月期货。展期权重不是 WTI/BRENTOIL 基础数量比例，也不是自动给出的对冲比率。

### 2. ET 与 UTC 不能混用

官方规则说 `17:30`/`19:00 ET`，本地 candles 使用 UTC timestamp。2026 年 8 月处于 EDT（UTC−4），所以对应 `21:30/23:00 UTC`。冬季偏移可能变化，代码不能写死一个固定小时差。

### 3. 两腿的状态可能不同

WTI 比 BRENTOIL 提前 90 分钟开始展期，且底层关闭窗口不同。一个 UTC 小时可能跨越一腿的关闭/展期状态，而另一腿仍处在不同阶段，因此该小时的价差必须先做可比性标记。

## 当前样本边界

现有共同 1h 样本覆盖 `2026-07-15T19:00:00Z` 至 `2026-08-05T14:00:00Z`，共 500 行；它在官方 2026-08-07 展期开始前结束。因此当前历史快照不能证明 2026 年 8 月展期期间的价格反应。

## 证据位置

- 课程：`lessons/0004-day5-roll-session.html`
- 参考卡：`reference/day5-roll-session.html`
- 交互脚本：`assets/day5-roll-session.js`
- 可审计练习：`lab/day5_roll_session.py`
- 测试：`lab/test_day5_roll_session.py`
- 脱敏规则快照：`lab/data/day5_roll_session_snapshot.json`
- 研究笔记：`notes/rwa-roll-and-session-model.md`

## 未完成 / 未知

- 现有 500 小时快照没有覆盖 2026-08-07 至 2026-08-13 展期窗口。
- 没有逐小时 Lighter 市场开放/关闭状态字段。
- 没有证明 candle timestamp 是区间开始还是结束。
- 没有连续盘口、oracle freshness、真实成交和退出证据。

## 研究结论

Day 5 完成了时间状态建模，但没有产生可交易信号。WTI–BRENTOIL 策略仍处于资料缺失/继续补证据状态。
