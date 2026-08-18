# 研究工作台一手资料与数据能力核对

> 核对时间：2026-08-18
>
> 用途：Day14–21 研究工作台详细设计。动态接口与规则在正式实现时仍需重新读取。

## 1. 结论

Lighter 与 Hyperliquid 已足以支持工作台的第一条完整研究路径：市场发现、当前行情扫描、盘口/成交/资金费连续采集、候选排序、异常研究和纸上回放。不能从公开盘口直接取得的关键状态必须单独建模，尤其是 RWA 实际合约权重与 external/internal oracle 状态。

NautilusTrader 可以在后续里程碑承接数据持久化、历史重放和实时影子运行，但 Day14 初版不需要先引入完整事件引擎。先建立稳定领域模型和候选工作流，再将同一数据与研究逻辑接入 `ParquetDataCatalog` 和 backtest/live 节点。

## 2. 数据能力矩阵

| 能力 | Lighter | Hyperliquid / HIP-3 | 工作台使用方式 |
|---|---|---|---|
| 市场目录与完整身份 | `orderBookDetails` / `orderBooks` 提供 symbol、market ID、状态、精度、最小数量与费率 | `perpDexs`、`meta`、`metaAndAssetCtxs` 提供 dex、symbol、精度、杠杆和上下文 | 每日重建可映射市场，不写死 symbol |
| L2 当前盘口 | REST `orderBookOrders`；WS `order_book/{market_id}` 首次快照后更新 | REST `l2Book`；WS `l2Book` | 交易吸引力榜的可成交价差、深度和容量 |
| BBO | 可从 L2 维护，也可用 Nautilus Lighter quote stream | WS `bbo` 或 L2 | 候选实时刷新 |
| 成交 | REST `recentTrades` 与 WS trades；官方 `Trade` 模型含 market ID、price、size、timestamp、maker side | WS `trades`；用户/市场成交接口 | 成交活跃度、方向、机会发生后的真实交易反应 |
| 当前 mark/index | Lighter market stats stream；Nautilus 适配器映射为 `MarkPriceUpdate` / `IndexPriceUpdate` | `metaAndAssetCtxs` 有 `markPx`、`oraclePx`、`midPx`、`impactPxs`、premium | 解释价差机制，不替代可成交价 |
| 资金费当前值 | `funding-rates`；详情模型有 market ID、exchange、symbol、rate | `metaAndAssetCtxs.funding` | 资金费候选榜与持有成本估计 |
| 资金费历史 | `fundings`，记录 timestamp、value、rate、direction | `fundingHistory`，记录 coin、fundingRate、premium、time | 回放持有现金流与资金费异象 |
| OHLCV | candles / market charts | `candleSnapshot` 与 WS candle | 低频基线和候选预筛；不替代 L2 回放 |
| 市场状态 | 目录 status、instrument status stream | meta/delisted、市场状态 API、HIP-3 dex 元数据 | 停市/下架/状态切换标签 |
| 用户实际费率 | Lighter 账户/API 只读端点，需要单独安全进程 | `userFees` 返回 maker/taker schedule 与用户 rate | Day16 后只读获取，凭据与公开采集器分离 |
| 历史 L2 | 官方接口未提供完整历史 L2；必须自行采集 | 官方 REST 只给当前快照，历史 L2需自行采集或外部数据 | Day15 起持续采集，不从 K 线重建成交 |
| RWA 实际合约权重 | 规则页给展期表；公开盘口不直接给观察时刻权重 | trade.xyz 规则页给展期机制；book/context 不直接给实时权重 | 独立规则状态证据；未知时标注，不阻止保存原始行情 |
| external/internal oracle 状态 | 定价规则说明切换机制；当前盘口响应不直接标状态 | trade.xyz 说明 external/internal；`oraclePx` 本身不说明来源状态 | 候选解释器需要从官方状态、时段和价格行为组合推断，并区分“观察”与“确认” |

## 3. Lighter 一手资料

### 官方 SDK

官方 Python SDK：`elliottech/lighter-python`[1]，本次核对 commit `da322db2ca4fb3fac56b463d0ade4e54960e32be`。

关键模型：

- `PerpsOrderBookDetail`[2]：symbol、market ID、status、maker/taker fee、最小数量、精度、保证金、24h 量、OI、funding 参数。
- `OrderBookOrders`[3]：双边订单列表，但响应模型没有盘口快照来源时间。
- `Trade`[4]：成交 ID、market ID、price、size、maker side、block height、timestamp、transaction time。
- `FundingRate`[5] 与 `Funding`[6]：当前与历史资金费字段。
- `PaperOrderBookListener`[7]：连接 `wss://mainnet.zklighter.elliot.ai/stream`，订阅 `order_book/{market_id}`；`subscribed/order_book` 被当作初始快照，之后处理 `update/order_book`。

### 官方/第一方文档

- Lighter API `orderBookOrders`[8]
- Lighter WebSocket Reference[9]
- Lighter Funding[10]
- Lighter RWA Pricing Mechanism[11]
- Lighter Futures Rolling Mechanism[12]

## 4. Hyperliquid 与 trade.xyz 一手资料

### 官方 SDK

官方 Python SDK：`hyperliquid-dex/hyperliquid-python-sdk`[13]，本次核对 commit `2fdb18f9517675ea03695a0962bd19eece9c83f0`。

`Info`[14] 明确提供：

- `meta` / `meta_and_asset_ctxs`；
- `perp_dexs`；
- `funding_history`；
- `l2_snapshot`，包含 coin、levels、毫秒 `time`；
- `candles_snapshot`；
- `user_fees`。

`WebsocketManager`[15] 支持 `allMids`、`l2Book`、`trades`、`candle`、`bbo`、`activeAssetCtx` 等公开或账户订阅。

### 官方/第一方文档

- Hyperliquid Perpetuals Info Endpoints[16]
- Hyperliquid Funding[17]
- Hyperliquid HIP-3[18]
- trade.xyz Specification Index[19]
- trade.xyz Oracle Price[20]
- trade.xyz External Price[21]
- trade.xyz Mark Price[22]

## 5. NautilusTrader 的接入位置

第一方源码：`nautechsystems/nautilus_trader`[23]，本次核对 develop commit `7a6dff49e0d953c85fd980b70f715a9cec1b2829`。PyPI 当前稳定版为 `1.231.0`，支持 Python `3.12–3.14`。[29] 本仓库目前没有锁定 NautilusTrader 依赖，因此 develop 文档只用于能力调研，不能直接当作当前运行依赖。正式接入前必须固定版本、创建兼容 Python 环境并对稳定版适配器做只读 smoke test。

- Data 概念[24]：内置支持 L2/L1、quote、trade、bar、mark/index、funding、instrument status；instrument 定义提供精度、货币和合约语义。
- Custom Data[25]：自定义数据可以进入同一 routing、Arrow/Parquet 持久化与查询路径，适合保存候选特征、oracle 状态、展期状态和实验标注。
- Backtesting[26]：高层 `BacktestNode` 使用数据目录和批量运行；低层 `BacktestEngine` 适合直接控制。后续纸上回放应复用工作台核心成本与状态逻辑，而不是重写策略。
- Lighter integration[27]：适配器有独立 `LighterDataClient` 与 `LighterExecutionClient`；数据能力包括 instrument、trade、quote、L2、mark/index、funding、bars。工作台只注册数据客户端。
- Hyperliquid integration[28]：支持普通 perp、HIP-3 perp、spot 与 outcomes；数据与 execution client 分离。

## 6. 分阶段实现建议

### Day14 初版

不依赖连续历史即可完成：

1. 每日目录发现与经济映射；
2. 全市场 BBO/L2 当前扫描；
3. 当前 mark/oracle/funding/OI/volume 上下文；
4. 交易吸引力榜与研究价值榜分开；
5. 每次优先展示最多 3 个；不足 3 个时不凑数；
6. 单候选研究页先显示现象，用户提交简短解释后解锁竞争假设；
7. 实验记录持久化。

### Day15–16

- 公开 WS 连续采集 BBO/L2/trade/reference/funding/status；
- 追加式原始事件保存与分段；
- 自身基线、持续时间、事件时段与容量曲线；
- 只读账户费率独立进程。

### Day17–18

- 区分性实验与机制标签；
- 四次主动成交、费用、资金费和退出成本；
- 真实连续数据纸上回放；
- 实验历史不覆盖旧参数。

### Day18–20

- 先固定 NautilusTrader 版本并建立 Python `>=3.12,<3.15` 的独立环境；
- 分别通过 Lighter 与 Hyperliquid 只读数据适配器 smoke test；
- 再将稳定数据与研究逻辑接入 Nautilus `ParquetDataCatalog`；
- 执行失败和双腿状态回放；
- 相同核心逻辑用于历史与实时影子运行；
- 不注册 execution client。

## 7. 明确不能声称的能力

- 当前 REST 冒烟快照不能证明机会寿命。
- K 线不能重建可成交 L2。
- `oraclePx` 不能单独证明 external/internal 状态。
- 官方展期规则不能替代观察时刻实际权重证据。
- Nautilus 的确定性重放不能证明未来盈利。
- 双榜推荐是研究排序，不是自动交易信号。

## Sources

[1] https://github.com/elliottech/lighter-python — elliottech/lighter-python
[2] https://github.com/elliottech/lighter-python/blob/main/docs/PerpsOrderBookDetail.md — PerpsOrderBookDetail
[3] https://github.com/elliottech/lighter-python/blob/main/docs/OrderBookOrders.md — OrderBookOrders
[4] https://github.com/elliottech/lighter-python/blob/main/docs/Trade.md — Trade
[5] https://github.com/elliottech/lighter-python/blob/main/docs/FundingRate.md — FundingRate
[6] https://github.com/elliottech/lighter-python/blob/main/docs/Funding.md — Funding
[7] https://github.com/elliottech/lighter-python/blob/main/lighter/paper_client/live.py — PaperOrderBookListener
[8] https://apidocs.lighter.xyz/reference/orderbookorders — Lighter API orderBookOrders
[9] https://apidocs.lighter.xyz/docs/websocket-reference — Lighter WebSocket Reference
[10] https://docs.lighter.xyz/trading/funding — Lighter Funding
[11] https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism — Lighter RWA Pricing Mechanism
[12] https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism — Lighter Futures Rolling Mechanism
[13] https://github.com/hyperliquid-dex/hyperliquid-python-sdk — hyperliquid-dex/hyperliquid-python-sdk
[14] https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/hyperliquid/info.py — Info
[15] https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/master/hyperliquid/websocket_manager.py — WebsocketManager
[16] https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals — Hyperliquid Perpetuals Info Endpoints
[17] https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding — Hyperliquid Funding
[18] https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-3-builder-deployed-perpetuals — Hyperliquid HIP-3
[19] https://docs.trade.xyz/consolidated-resources/specification-index — trade.xyz Specification Index
[20] https://docs.trade.xyz/perp-mechanics/oracle-price — trade.xyz Oracle Price
[21] https://docs.trade.xyz/perp-mechanics/external-price — trade.xyz External Price
[22] https://docs.trade.xyz/perp-mechanics/mark-price — trade.xyz Mark Price
[23] https://github.com/nautechsystems/nautilus_trader — nautechsystems/nautilustrader
[24] https://nautilustrader.io/docs/latest/concepts/data — Data 概念
[25] https://nautilustrader.io/docs/latest/concepts/custom_data — Custom Data
[26] https://nautilustrader.io/docs/latest/concepts/backtesting — Backtesting
[27] https://nautilustrader.io/docs/latest/integrations/lighter — Lighter integration
[28] https://nautilustrader.io/docs/latest/integrations/hyperliquid — Hyperliquid integration
[29] https://pypi.org/project/nautilus-trader/ — NautilusTrader PyPI
