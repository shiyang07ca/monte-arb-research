# Day 1 / 2026-08-05 — 研究方向重构与 Lighter RWA 数据审计

## 结论

- 研究主线已由“泛化的链上套利/跨场所对冲”收窄为：**Lighter 内部 WTI–BRENTOIL 同场所跨品种相对价值研究**。
- 这不是严格的跨场所套利；不默认两腿 1:1 对冲。
- 当前策略状态：`Blocked`；真实执行状态：`No-Go`。
- 研究期资金：`$0`；本次只读、无私钥、无真实订单。

## 用户确认

用户明确选择：

> Lighter 内部 WTI–BRENTOIL：同场所跨品种统计套利；可以研究，但它不属于严格的跨场所对冲。

用户随后确认第一阶段先不选固定美元价差、价格比率或动态 beta，先建立并清洗足够长的原始数据，确认价格源、交易时段和缺失模式。

## 一手资料

- Lighter RWA 市场规格：<https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications>
- Lighter RWA 定价机制：<https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism>
- Lighter 期货合约展期机制：<https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism>
- Lighter Funding：<https://docs.lighter.xyz/trading/funding>
- Lighter candles API 文档：<https://apidocs.lighter.xyz/reference/candles>
- Lighter fundings API 文档：<https://apidocs.lighter.xyz/reference/fundings>

关键事实：

- WTI 追踪 1 桶 West Texas Intermediate Light Sweet Crude Oil；BRENTOIL 追踪 1 桶 Brent Crude Oil；两者属于 commodity RWA，oracle 为 Pyth Lazer。[45]
- 两者使用期货价格滚动，但滚动时间不同：WTI 在美国东部时间 17:30 开始，BRENTOIL 在 19:00 开始；每天将 20% 从当前月切换到下一月。[44]
- RWA 价格会在外部 oracle 与内部订单簿 impact price 的 EMA 之间切换，因此 index/mark/oracle 状态需要单独记录。[43]
- candles 每次最多返回 500 根；fundings 每次最多返回 750 条，funding 支持 `1h`/`1d`。[47][48]

## 实际动作

- 新建 `MISSION.md`，将真实目标、成功标准、约束和明确不做的方向固定下来。
- 新建 `RESOURCES.md`，只收录本阶段 Lighter 官方资料和动态 API 证据。
- 重写 `resource/plan.md` 为 v4，计划四周：RWA 合约模型 → 数据审计 → 样本外价差定义 → 可执行性与净现金回放。
- 重写 `notes/research-charter.md`，不预设价差公式。
- 新建 `lab/capture_lighter_rwa.py`，只读抓取两市场 1h/1d candles、1h fundings、orderBookDetails；保存 URL、参数、HTTP 状态、请求/接收时间、延迟、原始文件和 SHA-256。
- 新建 `lab/audit_lighter_rwa.py`，从原始响应生成审计报告和共同小时序列；不拟合策略、不发单。
- 运行两个脚本并用 `python3 -m json.tool` 校验 JSON。

## 证据文件

- `lab/data/lighter_rwa_capture_manifest.json`
- `lab/data/lighter_rwa_raw/WTI_candles_1h.json`
- `lab/data/lighter_rwa_raw/BRENTOIL_candles_1h.json`
- `lab/data/lighter_rwa_raw/WTI_candles_1d.json`
- `lab/data/lighter_rwa_raw/BRENTOIL_candles_1d.json`
- `lab/data/lighter_rwa_raw/WTI_fundings_1h.json`
- `lab/data/lighter_rwa_raw/BRENTOIL_fundings_1h.json`
- `lab/data/lighter_rwa_raw/145_orderBookDetails.json`
- `lab/data/lighter_rwa_raw/159_orderBookDetails.json`
- `lab/data/lighter_rwa_data_audit.json`
- `lab/data/lighter_rwa_aligned_1h.jsonl`
- `lab/data/lighter_rwa_instrument_matrix.json`

## 实际结果

- 两腿 1h candles：各 500 行；共同时间范围为 `2026-07-15T19:00:00Z` 至 `2026-08-05T14:00:00Z`，共同样本 500 小时。[49][50]
- 两腿 1h fundings：各 750 行；共同时间范围为 `2026-07-05T09:00:00Z` 至 `2026-08-05T14:00:00Z`。[53][54]
- 1h 收盘对数收益相关性：`0.9707121232645127`。这只是短样本描述性统计，不是协整或盈利证明。
- 固定收盘价差 `WTI - BRENTOIL` 在共同样本中的范围约为 `-4.845` 至 `-1.832`；价格比率范围约为 `0.9430` 至 `0.9805`。这不足以决定价差公式。
- funding `value` 的 WTI 减 BRENTOIL 平均约 `-0.0003131362`，但尚未证明该字段如何映射到个人账户实际现金流，不能直接当收益。[46][53][54]
- 本次 Daily 原始响应未发现重复 timestamp；仍需处理边界、缺失和零值规则。

## 阻断项

- `HISTORY_DEPTH_INSUFFICIENT`：小时历史当前只有约 21 天，共同样本不足以证明长期协整。
- `ROLL_SEMANTICS_MUST_BE_MODELED`：两腿滚动日/时间不同，可能制造结构性价差变化。
- `FUNDING_LEDGER_UNKNOWN`：API 的 `value`/`rate`/`direction` 尚未与账户账本核对。
- `DEPTH_AND_EXIT_UNKNOWN`：尚未完成目标数量盘口、部分成交和退出滑点回放。
- `PERMISSION_UNKNOWN`：账户、地区和真实交易权限未核验。

## 明日唯一动作

> 只完成一个动作：为 WTI/BRENTOIL 写出 RWA 合约模型和时间状态表，包含经济对象、价格源、展期窗口、市场关闭窗口、funding 字段、保证金字段和未知项。不要拟合 beta，不要扩大到第三个场所，不要写下单逻辑。

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
