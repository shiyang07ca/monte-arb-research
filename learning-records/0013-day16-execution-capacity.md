# 0013 · Day16 可执行性与容量

> 日期：2026-08-21
> 状态：已记录（工作台能力完成；用户研究动作待完成）
> 里程碑：Day16（工作台能力 + 用户研究动作）

## 背景

Day14 的候选只有 top-of-book 屏幕价差，无法回答"按我的预算真的能成交吗、成本多少"。Day16 把候选榜升级为按目标规模 × 方向的双腿可成交结果：逐档走真实 L2、VWAP、滑点、已知费率、未成交数量与容量曲线，并把结果接入工作台执行视图（支持自动/手动刷新与自定义规模重算）。

## 非显眼教训（需要以后修订的知识）

1. **$10 预算档 ≠ 可下单档**：名义向下取整到 size_decimals 后常低于 `min_quote_amount`（$10），引擎返回 MIN_QUOTE 而不是把订单"近似"到最小单。用户预算 $5–200 的档位设计必须对照最小名义，否则预算档全是无效档。
2. **容量曲线必须跳过低于最小单的档位，而不是在首档中断**：最初实现"遇到未全额成交就 break"，导致 $10 不可下单时容量恒为 0——那是"下单失败"不是"容量为 0"，语义错误。
3. **未知费率是结论杀手**：HL HIP-3 meta 无费率字段，`total_cost_bps` 保持 null。BRENTOIL 全档净价差 ≤0.44 bps，任何 ≥0.5 bps 的假设费率都会翻负——"屏幕价差为正"在未知费率面前没有任何结论价值。
4. **屏幕价差、捕获、净价差、总成本必须分开**：同一快照下 AAPL 屏幕价差方向与目标规模净结果可以完全相反（买左 -6.00 vs 买右 +4.80@$100），合并成一个数会掩盖机制。
5. **翻转点是最有教学价值的证据**：BRENTOIL 买左卖右 +0.44（$25–250）→ +0.15（$500）→ −0.03（$1000），把"规模如何改变结论"变成可读曲线，而不是一个正负号。
6. **冻结盘口重算是廉价敏感性实验**：自定义规模走 `POST /workbench/api/execution/compute` 即时重算，不重新请求交易所；费率 what-if 同理。研究循环可以围绕同一快照反复进行。

## 已发生事实（证据可复查）

- `src/monte_arb/day16_execution.py`：走档/下单量/双腿/容量纯函数 + 快照构建 + CLI 扫描（Lighter 限流 1.1s 间隔，`orderBookDetails` 批量参数）。
- `research/runs/day16-execution-scan.json`：60 对、120 盘口、0 错误、`observed_at=2026-08-21T00:14:22Z`。
- `src/monte_arb/workbench_server.py`：`/workbench/execution`（深色 UI）、`GET /workbench/api/execution`、`POST /workbench/api/refresh`、`POST /workbench/api/execution/compute`；Day14 路由保持兼容。
- `tests/test_day16_execution.py`：23 项新测试（含容量跳过最小档回归测试）；全仓 134 项通过。
- `lessons/0012-day16-execution-capacity.html` + `reference/day16-execution-capacity.html` + `assets/day16-execution-capacity.js`（由 `day16_lesson_data.py` 从真实扫描生成）。
- 浏览器验证：执行视图数据/交互/自定义规模/刷新均通过（截图 `~/.hermes/cache/screenshots/browser_screenshot_fd7739f82a1247ebaf0c89958e8a916f.png`，OCR 复核）。

## 研究状态

**Blocked / No-Go**：BRENTOIL 净价差最大 +0.44 bps，HL 费率未知（`null`）且任何 ≥0.5 bps 假设都会翻负；AAPL 买右卖左 +4.80 bps 但 HL 费率 + 退出滑点未计。工作台证明的是"哪些规模/方向在价格冲击下仍有余量"，不是可交易机会。

## 下一步

- 用户研究动作：选择方向与规模，回答规模意义/最可能改变结论的成本/持有时间变化的影响；
- Day17 机制实验室：区分性实验（卖腿深度 vs tick 结构 vs 未知费率）；
- 或先追 HL `userFees` 只读证据，把 null 费率变成已知值。
