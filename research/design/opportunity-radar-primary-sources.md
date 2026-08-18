# 机会雷达一手资料与接入路线

> 核对时间：2026-08-18
>
> 目的：扩大研究搜索空间，但不把每个新场所立即开发成完整适配器。

## 1. 机会雷达的职责

机会雷达只回答：

1. 是否有可公开读取的数据；
2. 是否存在值得持续监控的市场结构异象；
3. 下一项低成本验证是什么；
4. 是否值得升级为主工作台适配器。

它不输出自动交易信号，也不因页面写着“套利”就假定可执行。

## 2. 升级进主工作台的最低标准

一个方向只有同时满足以下条件才正式接入：

- 能取得稳定且有明确身份的实时市场数据；
- 能确定产品经济对象、价格机制、交易时段和结算/抵押品；
- 能取得或保守估计费率、最小数量与可成交深度；
- 有至少一个可验证的异常指标，而不是纯粹叙事；
- 账户、地域、链、资金与 API 限制已记录；
- 新适配器带来的研究价值高于维护成本；
- 只读侦察阶段不需要私钥或交易权限。

## 3. 第一批雷达方向

| 方向/场所 | 一手数据入口 | 值得监控的现象 | 约束与接入建议 |
|---|---|---|---|
| dYdX Chain perpetuals | 官方 Indexer HTTP API、WebSocket、Python/TS/Rust clients | 与 Hyperliquid/Lighter 的同资产 BBO、funding、OI、成交活跃度差异 | 公共市场数据充分；作为第三个 crypto perp 对照场所优先级高 |
| Drift / Velocity（Solana） | Velocity 官方 Data API、SDK、DLOB/orderbook WS；Drift 生态模型 | DLOB、JIT auction、AMM 与 CLOB 报价差；perp funding 与 borrow/lend | 模型比纯 CLOB 复杂；先雷达化，不直接与 CLOB 屏幕价一一比较 |
| Architect / AX | 官方 SDK marketdata：status、ticker、L1/L2 snapshot、diff、sequence、trades、candles | RWA/TradeFi 多 venue 行情、CME/股票与链上 RWA 报价状态差 | 创建 API key 才能访问；数据语义清晰，适合作为后续 RWA 专业数据基准 |
| Ostium | Builder SDK、市场/费用/协议文档、链上可审计 fill | 股票、ETF、商品、指数、FX、crypto 的 24/7/时段价格恢复与链上 fill | 定价/流动性模型非 CLOB；先研究 oracle 与 fill 机制，再谈跨场执行 |
| Avantis | 官方 SDK/API、market hours、execution/pricing、future feed roll adjustment | RWA 零费率阶段、future roll adjustment、价格恢复、资金费 bot 数据 | 官方明确提供 market data/API；先做价格与时段雷达，执行模型需单独验证 |
| trade.xyz 其他 HIP-3 RWA | Hyperliquid `perpDexs`、`metaAndAssetCtxs`、`l2Book`、trade.xyz specs | 股票/指数/商品在 cash/extended/internal session 间的价差与流动性 | 与现有适配器复用度最高，应先扩展到全部可映射 RWA |
| Hyperliquid 其他 HIP-3 dex | `perpDexs` 自动发现各 builder dex | 同一资产跨 builder dex 的 collateral、oracle、funding 与深度差 | settlement collateral 可能不同；必须按 dex 分隔，不按 ticker 直接配对 |
| CEX–DEX crypto perp funding | CEX 公共 futures API + Lighter/HL/dYdX 公共数据 | funding 分化、basis、OI/volume、资金迁移 | 地域/账户/费用和转账时延重要；先比较资金费与可成交成本，不假定 delta-neutral 免费 |
| 链上借贷与清算 | Aave/Compound/Morpho 官方 subgraph/API/合约事件、oracle | 借贷利率分化、健康因子集中、清算密度、抵押品折价 | 与 perp 系统不同领域；先建事件雷达，不急于统一执行模型 |
| AMM/聚合器跨池现货 | Uniswap v3/v4、Curve、Balancer、1inch/0x 官方 quote/API/链上事件 | 同链池间净报价差、流动性迁移、gas/MEV 后可执行差 | 必须使用交易规模 quote、gas、批准、MEV 与失败模型；中间价没有意义 |

## 4. 当前最值得优先研究的三条扩展线

### A. 全部 HIP-3 RWA

理由：已有 Hyperliquid `xyz` 数据路径，新增成本最低；能训练股票、指数、商品、FX 的不同 session 与 oracle 机制。

第一步：自动发现 `perpDexs`，建立经济映射候选，不直接把相似 ticker 当作同一对象。

### B. dYdX 作为第三个 crypto perp 对照

理由：官方 Indexer 提供 HTTP 与 WebSocket 市场数据；适合测试双榜在第三个成熟 perpetual CLOB 上能否迁移。

第一步：只读拉取 markets、orderbook、trades 与 funding，比较与 Lighter/Hyperliquid 的字段和时间语义。

### C. Architect / AX 作为 RWA 专业数据源

理由：官方 marketdata SDK 明确提供 market status、ticker、L1/L2、diff sequence、trades 和 candles，且覆盖传统市场 venue；能成为 RWA 时段、底层价格与合约状态的证据补充。

第一步：确认账户/API key 获取与市场权限；不在主工作台保存 secret。

## 5. 一手资料

### dYdX

- dYdX Integration Documentation[1]
- dYdX Indexer HTTP API[2]
- dYdX WebSocket API[3]

### Drift / Velocity

- Velocity Protocol[4]
- Velocity for Developers[5]
- 官方文档说明 Data API 用于 analytics、dashboards、historical queries 与 offchain data；SDK 覆盖 markets、oracles、positions、orders、events 与 DLOB。

### Architect / AX

- Architect SDK Introduction[6]
- Architect Marketdata[7]
- 官方 marketdata 文档说明 L2 diff 首条为完整快照，后续为 diff；sequence number 可检测缺口，sequence ID 改变时应重新订阅快照。

### Ostium

- Ostium Trader Docs[8]
- Ostium Builder SDK[9]
- 官方资料说明覆盖 stocks、ETFs、commodities、indices、forex 与 crypto，并由链上 USDC settlement 与可审计 fill 支撑；这不等同于 CLOB 深度。

### Avantis

- Avantis Docs[10]
- Avantis SDK / APIs[11]
- 官方页面明确列出 market hours、execution & pricing、future feeds roll adjustment，并说明 SDK/API 可用于 market data、funding arbitrage bots 与 RWA engine integration。

### Hyperliquid / trade.xyz

- Hyperliquid Perpetuals API[12]
- HIP-3[13]
- trade.xyz Specifications[14]

### 链上方向

- Aave Developers[15]
- Morpho Docs[16]
- Uniswap Docs[17]
- Curve Technical Docs[18]
- Balancer Docs[19]

## 6. 雷达初版不做什么

- 不同时实现十个执行适配器；
- 不把 API 宣传语当成成交证据；
- 不把 AMM quote、oracle price、CLOB bid/ask 放进同一无语义价格列；
- 不在没有账户/地域/抵押品核验时估算“可投入资金”；
- 不因发现一次大价差就提升为交易候选。

## Sources

[1] https://docs.dydx.xyz — dYdX Integration Documentation
[2] https://docs.dydx.xyz/indexer-client/http — dYdX Indexer HTTP API
[3] https://docs.dydx.xyz/indexer-client/websockets — dYdX WebSocket API
[4] https://docs.velocity.exchange/protocol — Velocity Protocol
[5] https://docs.velocity.exchange/developers — Velocity for Developers
[6] https://docs.architect.co — Architect SDK Introduction
[7] https://docs.architect.co/sdk-reference/marketdata — Architect Marketdata
[8] https://docs.ostium.com/traders/welcome — Ostium Trader Docs
[9] https://docs.ostium.com/developer/sdk/overview — Ostium Builder SDK
[10] https://docs.avantisfi.com — Avantis Docs
[11] https://docs.avantisfi.com/avantis-sdk/avantis-sdk-apis. — Avantis SDK / APIs
[12] https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals — Hyperliquid Perpetuals API
[13] https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-3-builder-deployed-perpetuals — HIP-3
[14] https://docs.trade.xyz/consolidated-resources/specification-index — trade.xyz Specifications
[15] https://aave.com/docs/developers — Aave Developers
[16] https://docs.morpho.org — Morpho Docs
[17] https://docs.uniswap.org — Uniswap Docs
[18] https://docs.curve.finance — Curve Technical Docs
[19] https://docs.balancer.fi — Balancer Docs
