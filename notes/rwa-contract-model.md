# RWA 永续合约模型：Lighter WTI 与 BRENTOIL

> 状态：研究材料；不构成交易建议。
>
> 研究对象：Lighter `WTI`（`market_id=145`）与 `BRENTOIL`（`market_id=159`）。所有动态字段必须以源时间和原始响应为准；本文件不把一次快照写成长期规则。

## 1. 研究边界

WTI 和 BRENTOIL 是同一场所的两个商品 RWA 永续，不是同一标的的跨场所价差。它们分别代表 WTI 和 Brent 原油桶价，因此不能默认 1:1 对冲、固定美元价差或固定价格比率。[45]

第一阶段只做只读采集、数据审计、纸上现金流和执行回放；不认证、不发单、不连接私钥。当前资料仍不足以判断策略是否成立。

## 2. 市场对象和可交易规格

| 字段 | WTI | BRENTOIL | 证据/注意事项 |
|---|---:|---:|---|
| `market_id` | `145` | `159` | 动态 API 快照 |
| 产品 | `perp` | `perp` | 动态 API 快照 |
| 经济对象 | 1 桶 WTI | 1 桶 Brent | 官方 RWA 市场规格 |
| `multiplier` | `1.000000000000000000` | `1.000000000000000000` | 动态 `orderBookDetails` 快照；仍需以成交/账本语义核对 |
| 最小基础数量 | `0.100` | `0.0800` | 动态快照 |
| 最小报价金额 | `10.000000` | `10.000000` | 动态快照 |
| 数量小数位 | `3` | `4` | 动态快照 |
| 价格小数位 | `3` | `2` | 动态快照 |
| 初始保证金分数 | `500`（默认/最低） | `666`（默认），`500`（最低） | 动态快照；不要脱离账户和市场规则解读 |
| 维护保证金分数 | `300` | `300` | 动态快照 |
| close-out 分数 | `200` | `200` | 动态快照 |
| OI cap | 官方规格页给出 | 官方规格页给出 | 需以官方规则和动态市场状态复核 |

动态快照原始文件：

- `lab/data/lighter_rwa_raw/145_orderBookDetails.json`
- `lab/data/lighter_rwa_raw/159_orderBookDetails.json`
- 归纳矩阵：`lab/data/lighter_rwa_instrument_matrix.json`

## 3. 价格语义

官方 RWA 定价机制描述了外部 oracle、内部订单簿 impact price 和 EMA 之间的切换；oracle 失效时不能简单把价格序列当成稳定的外部现货价格。index price、mark price、成交价、mid 和 candle close 必须分列保存。[43][75]

研究数据字段至少分为：

| 字段 | 用途 | 未知时的处理 |
|---|---|---|
| `trade_price` | 观察实际成交 | 没有逐笔数据则标记 `unknown` |
| `candle_close` | 描述性时间序列 | 不代替 mark/index |
| `index_price` | 价格基准/资金费输入候选 | 必须保留源时间 |
| `mark_price` | 保证金和未实现 PnL 相关价格 | 不代替可成交价 |
| `mid_price` | 盘口描述 | 不代替目标数量成交价 |
| `oracle_state` | 识别外部源/内部 EMA 状态 | 未知时 `oracle_unknown` |

## 4. 期货价格展期和交易时间

官方展期机制说明，WTI/NATGAS 的展期窗口从美国东部时间 `17:30` 开始，BRENTOIL 的窗口从美国东部时间 `19:00` 开始；展期按每日 `20%` 从当前月迁移至下一月。两腿的底层市场关闭窗口也不同。[44]

研究中必须为每个小时生成状态字段：

- `wti_roll_window`
- `brentoil_roll_window`
- `market_closed_window`
- `展期权重资料缺失`（无法从公开接口重建具体状态时）
- `价格源资料缺失`

展期时段不能事后用“异常值”删除。至少要做三组结果：包含展期、排除展期、按展期阶段分层。若样本不足以比较，就明确写资料不足。

## 5. Funding 现金流

Lighter 官方 funding 规则涉及 premium、index 与 funding rate，并按固定周期处理多空之间的支付方向。API 中的 `value`、`rate`、`direction` 是原始字段，不应直接把两腿 `value` 相减当成策略收益。[46]

纸上账本先使用以下明确结构：

```text
leg funding cash flow
= position sign
× base quantity
× multiplier
× settlement/index price
× settled funding rate
```

每条记录至少保存：

- `market_id`
- `timestamp`
- `rate`
- `value`
- `direction`
- `position_sign`
- `base_quantity`
- `settlement_price_source`
- `cash_flow`
- `cash_flow_status`

如果 `value` 的单位、结算时点或方向不能由官方规则和受控纸上账本核对，就明确标注资金费账本资料缺失，不填零。

## 6. 订单、手续费和退出

官方手续费页说明 Standard Account 当前为 0 maker/0 taker，但文档也说明不同账户等级、延迟和其他配置可能不同。因此“费率为零”不等于“交易没有成本”。[28]

官方撮合文档定义了 market、limit、post-only、IOC、reduce-only、good-till-time 等订单行为，并采用 price-time priority；market order 仍可能产生价格冲击。[62]

研究回放必须分别计算：

1. 双腿开仓的目标数量走档成本；
2. funding 持仓现金流；
3. 双腿平仓的反向走档成本；
4. maker/taker/账户层级费用；
5. 部分成交和一腿失败准备金；
6. reduce-only 退出是否可用；
7. 延迟、断线、暂停、取消和恢复成本；
8. 保证金和清算压力。

未确认的费用、退出深度和账户权限不能当作 0。

## 7. PnL 与清算边界

Lighter 的 mark price、账户 PnL、保证金和清算规则必须分开学习。未实现 PnL 或中间价回归不等于可实现现金 PnL；清算与 close-out 是风险状态，不是策略退出机制。[61][75][76][77]

当前动态状态表只说明公共市场快照，不证明当前账户的权限、保证金余额、地区资格、可用订单类型或真实成交路径。以上字段未核验时，就明确记录权限、盘口和退出资料缺失。

## 8. API 数据契约和证据链

官方 API 文档说明 candles 单次最多 500 根、fundings 单次最多 750 条；本仓库快照中两腿共同 1h candles 为 500 根、约 21 天，funding 为 750 条、约 31 天。[47][48]

当前证据文件：

- 原始响应：`lab/data/lighter_rwa_raw/`
- 请求元数据和 SHA-256：`lab/data/lighter_rwa_capture_manifest.json`
- 审计报告：`lab/data/lighter_rwa_data_audit.json`
- 对齐小时数据：`lab/data/lighter_rwa_aligned_1h.jsonl`

REST/API 查询和 WebSocket 观测还必须保存请求时间、接收时间、源时间、状态码、延迟和原始响应。短样本的 `0.9707121232645127` 收益相关性仅为描述性结果，不能支持协整或盈利结论。

## 9. 当前未知项

- 历史窗口是否足以覆盖多个原油状态和完整展期周期；
- 每条 candle close 的具体价格来源和 oracle freshness；
- funding API 字段到个人账户实际现金账本的完整映射；
- 目标数量盘口深度、部分成交概率和退出滑点；
- 账户等级、地区、产品和实时交易权限；
- 展期/底层关闭时段的所有异常暂停和恢复行为。

任何一项未知都只能产生待验证的研究观察，不能据此声称策略成立。

## 10. 学习退出题

学习者不看本文，口头回答：

1. 为什么 WTI 和 BRENTOIL 都以美元/桶报价，仍不能默认 1:1 对冲？
2. oracle 失效时，为什么 candle close、index、mark 和可成交价可能不再表示同一个过程？
3. 为什么两个 funding `value` 字符串不能直接相减？
4. 为什么零 maker/taker fee 仍不能把执行成本设为 0？
5. 哪些字段缺失时必须明确标注资料不足？

通过标准：5 题至少答对 4 题，并能在仓库原始 JSON 或官方来源中定位至少 3 条答案。 

## Sources

[28] https://docs.lighter.xyz/trading/trading-fees — Lighter: Trading Fees
[43] https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism — Lighter Docs: RWA Pricing Mechanism
[44] https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism — Lighter Docs: Futures Contract Price Rolling Mechanism
[45] https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications — Lighter Docs: RWA Market Specifications
[46] https://docs.lighter.xyz/trading/funding — Lighter Docs: Funding
[47] https://apidocs.lighter.xyz/reference/candles — Lighter API: Candles
[48] https://apidocs.lighter.xyz/reference/fundings — Lighter API: Fundings
[61] https://docs.lighter.xyz/trading/liquidations-and-llp-insurance-fund — Lighter Docs: Liquidations and LLP Insurance Fund
[62] https://docs.lighter.xyz/trading/order-types-and-matching — Lighter Docs: Order Types & Matching
[75] https://docs.lighter.xyz/trading/fair-price-marking — Lighter Docs: Fair Price Marking
[76] https://docs.lighter.xyz/trading/pnl-and-total-account-value — Lighter Docs: PnL and Total Account Value
[77] https://docs.lighter.xyz/trading/multi-asset-margin — Lighter Docs: Multi-Asset Margin
