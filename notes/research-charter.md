# 研究章程：Lighter WTI–BRENTOIL 相对价值

## 已确认的研究对象

用户确认第一阶段研究：

- Lighter `WTI`，market_id `145`；
- Lighter `BRENTOIL`，market_id `159`；
- 同一场所、跨品种的 RWA 永续相对价值/统计套利；
- 这不是严格的跨场所套利，也不默认两腿 1:1 对冲。

## 今日唯一假设

> **在正确处理 RWA 价格源、期货展期、交易时段、资金费、保证金、开平仓滑点和单腿风险后，WTI–BRENTOIL 的关系是否存在可在样本外复现的、扣除成本后仍为正的相对价值机会？**

暂不指定固定美元价差、价格比率或动态 beta。先完成数据覆盖、清洗和合约语义核验。

## 已完成的只读证据

- `lab/capture_lighter_rwa.py` 已从 Lighter 官方 API 采集两市场的 1h/1d candles、1h fundings 和 orderBookDetails。
- 原始响应：`lab/data/lighter_rwa_raw/`。
- 请求元数据、HTTP 状态、接收时间、延迟、SHA-256：`lab/data/lighter_rwa_capture_manifest.json`。
- 数据审计：`lab/data/lighter_rwa_data_audit.json`。
- 共同小时序列：`lab/data/lighter_rwa_aligned_1h.jsonl`。

截至本次抓取，两个市场的 1h candles 各返回 500 根，共同覆盖约 21 天；1h fundings 各返回 750 条，共同覆盖约 31 天。短样本收盘收益相关性约 `0.971`，仅是描述性统计，不代表协整、回归或盈利。[47][48][49][50][53][54]

## 关键官方语义

- WTI 追踪 1 桶 West Texas Intermediate Light Sweet Crude Oil；BRENTOIL 追踪 1 桶 Brent Crude Oil，两者都是 commodity RWA 并使用 Pyth Lazer oracle。[45]
- WTI/NATGAS/WHEAT/COPPER 与 BRENTOIL 使用期货价格滚动；WTI 的滚动窗口在美国东部时间 17:30、BRENTOIL 在 19:00 开始，每天完成 20% 的当前月到下一月转换。[44]
- 外部 oracle 是主要价格源；oracle stale 时逐步转向内部订单簿 impact price 的时间加权 EMA，外部价格恢复时回到外部价格。[43]
- Lighter funding 文档需要与 API 的 `value`、`rate`、`direction` 一起解释，不能把两个字符串字段直接相减。[46]

## 风险边界

- 研究期资金：`$0`。
- 今天及数据研究阶段不发送订单、不连接私钥、不充值、不提现。
- 任何未知字段写成 `unknown`，不默认为零成本或无风险。
- 若未来讨论监督实验，先限制 `$5–20` 单次、总暴露 `$50` 以内、单笔最大可接受亏损 `$20`；必须另行确认。

## 判断规则

- `Go`：价格语义、展期、资金费账本、目标数量成交与退出、权限和风险路径均有证据，且保守样本外回放为正。
- `No-Go`：关键字段已知，但成本、结构断点或样本外表现否定策略。
- `Blocked`：历史深度、funding 账本、目标数量退出、权限或结算字段仍未知。

## 本阶段下一步

1. 检查 daily 重复 timestamp，并写清边界、缺失和零值处理规则；当前审计未发现重复，不删除原始证据。
2. 统一 UTC 小时数据，加入滚动窗口、市场关闭窗口和 oracle 状态字段。
3. 连续补采，确认官方历史窗口是否能扩展；不足则明确 `HISTORY_DEPTH_INSUFFICIENT`。
4. 只用训练窗口决定价差定义和 beta，再做样本外测试。
5. 完成目标数量盘口与退出回放前，不讨论真实下单。

## Sources

[43] https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism — Lighter Docs: RWA Pricing Mechanism
[44] https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism — Lighter Docs: Futures Contract Price Rolling Mechanism
[45] https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications — Lighter Docs: RWA Market Specifications
[46] https://docs.lighter.xyz/trading/funding — Lighter Docs: Funding
[47] https://apidocs.lighter.xyz/reference/candles — Lighter API: Candles
[48] https://apidocs.lighter.xyz/reference/fundings — Lighter API: Fundings
[49] https://mainnet.zklighter.elliot.ai/api/v1/candles?market_id=145&resolution=1h&count_back=500 — Lighter API snapshot: WTI 1h candles
[50] https://mainnet.zklighter.elliot.ai/api/v1/candles?market_id=159&resolution=1h&count_back=500 — Lighter API snapshot: BRENTOIL 1h candles
[53] https://mainnet.zklighter.elliot.ai/api/v1/fundings?market_id=145&resolution=1h&count_back=750 — Lighter API snapshot: WTI 1h funding
[54] https://mainnet.zklighter.elliot.ai/api/v1/fundings?market_id=159&resolution=1h&count_back=750 — Lighter API snapshot: BRENTOIL 1h funding
