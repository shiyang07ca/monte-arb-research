# Day 2 / 2026-08-06 — 前十天计划与合约模型起草

## 今日唯一问题

在 Day 1 的只读采集和审计基础上，先把 Lighter WTI/BRENTOIL 的 RWA 合约语义和时间状态写清楚，再决定后续课程如何压缩；不拟合 beta，不写下单逻辑。

## 实际动作

- 重新读取仓库规则、MISSION、现有计划、课程原文和动态数据审计；
- 通过浏览器访问并阅读 Lighter 官方 RWA、定价、展期、funding、费用、订单、清算、Fair Price、PnL、保证金和 API 文档；
- 使用 `agent-reach` 检查和网页检索流程；
- 扩充 citation ledger，登记本轮新增官方来源；
- 创建 `notes/rwa-contract-model.md`；
- 创建 `notes/rwa-roll-and-session-model.md`；
- 将 `resource/plan.md` 从四周泛化计划改为 Day 1–10 详细计划、Day 11–20 条件式分支、Day 21 复盘；
- 更新 `notes/icl-course-outline.md` 和 `RESOURCES.md`。

## 已确认的官方规则摘要

- WTI 与 BRENTOIL 是不同商品 RWA 永续，不能默认 1:1 对冲。[45]
- 两者使用外部 oracle 和内部 EMA/impact-price 机制，价格语义必须分开记录。[43]
- WTI 和 BRENTOIL 的期货展期窗口不同：美国东部时间 17:30 与 19:00，且每日迁移 20%。[44]
- Funding、mark/index、手续费、订单类型、清算和 API 返回限制都必须进入研究闸门，而不是被抽象成“价格差”。[28][46][47][48][61][62][75][76][77]

## 证据路径

- `notes/rwa-contract-model.md`
- `notes/rwa-roll-and-session-model.md`
- `resource/plan.md`
- `notes/icl-course-outline.md`
- `RESOURCES.md`
- `lab/data/lighter_rwa_data_audit.json`
- `lab/data/lighter_rwa_instrument_matrix.json`
- `lab/data/lighter_rwa_raw/`

## 学习与策略状态

- 学习计划重构：已完成本轮文档写入，待运行校验；
- 合约模型：已起草，仍需通过学习者口头回忆和代码复现验收；
- 策略研究：`Blocked`；
- 真实执行：`No-Go`。

## 未知项

- 历史深度仍不足以证明长期协整；
- funding 字段到个人账户现金账本的映射未验证；
- 目标数量连续盘口、部分成交和退出滑点未完成；
- 账户/地区/产品权限未核验；
- 展期和底层市场关闭/恢复的完整历史状态仍需补充。

## 明日唯一动作

运行并审查 Day 2 文档和数据的可复现性，随后只补充价格字段、UTC/美国东部时间状态和数据质量规则；不扩大研究标的，不写真实下单代码。

## Sources

[28] https://docs.lighter.xyz/trading/trading-fees — Lighter: Trading Fees
[43] https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism — Lighter Docs: RWA Pricing Mechanism
[44] https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism — Lighter Docs: Futures Contract Price Rolling Mechanism
[45] https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications — Lighter Docs: RWA Market Specifications
[46] https://docs.lighter.xyz/trading/funding — Lighter Docs: Funding
[47] https://apidocs.lighter.xyz/reference/candles — Lighter API: Candles
[48] https://apidocs.lighter.xyz/reference/fundings — Lighter API: Fundings
[61] https://docs.lighter.xyz/trading/liquidations-llp-insurance-fund — Lighter Docs: Liquidations and LLP Insurance Fund
[62] https://docs.lighter.xyz/trading/order-types-matching — Lighter Docs: Order Types & Matching
[75] https://docs.lighter.xyz/trading/fair-price-marking — Lighter Docs: Fair Price Marking
[76] https://docs.lighter.xyz/trading/pnl-and-total-account-value — Lighter Docs: PnL and Total Account Value
[77] https://docs.lighter.xyz/trading/multi-asset-margin — Lighter Docs: Multi-Asset Margin
