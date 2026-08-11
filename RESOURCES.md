# Lighter WTI–BRENTOIL 相对价值研究资源

## Knowledge

### Lighter 官方机制

- [RWA 总览](https://docs.lighter.xyz/trading/real-world-assets-rwas)：说明 RWA 市场类别和基本市场结构。[42]
- [RWA 定价机制](https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism)：说明外部 oracle、内部订单簿 impact price、EMA，以及 oracle 失效时的价格过渡。[43]
- [期货价格展期机制](https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism)：说明 WTI 与 BRENTOIL 使用期货价格、不同展期窗口，以及每日 20% 的当前月到下一月迁移。[44]
- [RWA 市场规格](https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications)：说明 WTI/BRENTOIL 的经济对象、Pyth Lazer 价格源和动态市场规格。[45]
- [Funding](https://docs.lighter.xyz/trading/funding)：说明 funding rate、premium、index、方向和结算规则；不能把 API 原始字段直接当成现金收益。[46]
- [Trading Fees](https://docs.lighter.xyz/trading/trading-fees)：说明账户层级费率和延迟；0 maker/0 taker 不代表没有 spread、冲击或排队成本。[28]
- [Order Types & Matching](https://docs.lighter.xyz/trading/order-types-and-matching)：说明 market、limit、post-only、IOC、reduce-only、good-till-time 和 price-time priority。[62]
- [Liquidations & LLP Insurance Fund](https://docs.lighter.xyz/trading/liquidations-and-llp-insurance-fund)：用于理解清算和保险基金风险边界。[61]
- [Fair Price Marking](https://docs.lighter.xyz/trading/fair-price-marking)：用于区分 mark price、index price 和清算/PnL 相关价格。[75]
- [PnL and Total Account Value](https://docs.lighter.xyz/trading/pnl-and-total-account-value)：用于区分未实现 PnL、账户价值和可实现现金结果。[76]
- [Multi-Asset Margin](https://docs.lighter.xyz/trading/multi-asset-margin)：用于补充保证金和账户风险检查。[77]
- [Contract Specifications](https://docs.lighter.xyz/trading/contract-specifications)：用于核对合约参数和保证金语义。[72]

### Lighter 官方 API

- [Candles](https://apidocs.lighter.xyz/reference/candles)：K 线接口、时间周期和单次最多 500 根的限制。[47]
- [Fundings](https://apidocs.lighter.xyz/reference/fundings)：funding 接口、1h/1d 周期和单次最多 750 条的限制。[48]
- [Order Book Details](https://apidocs.lighter.xyz/reference/orderbookdetails)：市场详情端点。[16]
- [Order Book Orders](https://apidocs.lighter.xyz/reference/orderbookorders)：盘口档位端点；用于目标数量走档，而不是仅使用中间价。[78]
- [Trades](https://apidocs.lighter.xyz/reference/trades)：成交查询和过滤字段；账户相关查询可能需要认证。[79]
- [Asset Details](https://apidocs.lighter.xyz/reference/assetdetails)：资产/市场详情字段。[80]
- [Markets](https://apidocs.lighter.xyz/reference/markets)：市场查询入口。[81]
- [Rate Limits](https://apidocs.lighter.xyz/docs/rate-limits)：REST/API 限流约束。[29]
- [WebSocket Reference](https://apidocs.lighter.xyz/docs/websocket-reference)：实时订阅、保活和重连研究入口。[30]

### 跨场所迁移的官方接口

- [Lighter orderBookOrders](https://apidocs.lighter.xyz/reference/orderbookorders)：盘口订单级视图，`market_id` + `limit`（1–250）必填。
- [Lighter orderBooks](https://apidocs.lighter.xyz/reference/orderbooks)：市场规格（费用百分比、最小数量、小数位）。
- [Binance USDⓈ-M Exchange Information](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information)：交易规则、精度和限流字段。
- [Binance USDⓈ-M Funding Rate History](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History)：公共 funding 历史接口。
- [Binance USDⓈ-M Order Book](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Order-Book)：盘口快照接口。
- [Hyperliquid Info Endpoint](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint)：公开市场信息、盘口、成交和 candle 查询入口。
- [Hyperliquid WebSocket](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket)：实时订阅与重连练习入口。

### 学习科学原始研究

- [Roediger & Karpicke, 2006](https://pubmed.ncbi.nlm.nih.gov/16507066/)：测试效应与延迟保持。
- [Karpicke & Roediger, 2008](https://pubmed.ncbi.nlm.nih.gov/18276894/)：重复检索比单纯重复学习更能支持延迟回忆。
- [Karpicke & Bauernschmidt, 2011](https://pubmed.ncbi.nlm.nih.gov/21574747/)：绝对间隔对重复检索保持的影响。
- [Cepeda et al., 2006](https://pubmed.ncbi.nlm.nih.gov/16719566/)：分布式练习的定量综述。

### 动态证据

本仓库保存的动态快照只描述抓取时刻，不代表长期规则：

- `lab/data/lighter_rwa_raw/WTI_candles_1h.json`
- `lab/data/lighter_rwa_raw/BRENTOIL_candles_1h.json`
- `lab/data/lighter_rwa_raw/WTI_candles_1d.json`
- `lab/data/lighter_rwa_raw/BRENTOIL_candles_1d.json`
- `lab/data/lighter_rwa_raw/WTI_fundings_1h.json`
- `lab/data/lighter_rwa_raw/BRENTOIL_fundings_1h.json`
- `lab/data/lighter_rwa_raw/145_orderBookDetails.json`
- `lab/data/lighter_rwa_raw/159_orderBookDetails.json`
- `lab/data/lighter_rwa_capture_manifest.json`
- `lab/data/lighter_rwa_data_audit.json`

## Wisdom

暂不把社群观点作为策略证据。若未来收集交易者执行经验，必须与官方规则和可复现实测分开记录。

## Gaps

- 当前共同 1h 样本约 21 天，不足以证明长期协整；
- 需要明确 candle close、index、mark、oracle freshness 的对应关系；
- funding `value/rate/direction` 到个人账户现金账本的映射尚未验证；
- 目标数量连续盘口、部分成交、退出滑点和异常恢复尚未完成；
- 账户、地区、产品权限和保证金状态不是公开只读审计能够证明的；
- 展期和底层市场关闭/恢复的完整历史状态仍可能未知。

## 研究边界

当前研究结论：关键历史、展期、资金费账本、目标数量退出和权限资料仍不完整，不能据此判断策略是否成立。

未知字段不能默认为 0。本仓库只做只读研究和纸上验证，不连接私钥、不保存认证凭据、不发送真实订单。

## Sources

[16] https://apidocs.lighter.xyz/reference/orderbookdetails — Lighter API: Order Book Details
[28] https://docs.lighter.xyz/trading/trading-fees — Lighter: Trading Fees
[29] https://apidocs.lighter.xyz/docs/rate-limits — Lighter API: Rate Limits
[30] https://apidocs.lighter.xyz/docs/websocket-reference — Lighter API: WebSocket
[42] https://docs.lighter.xyz/trading/real-world-assets-rwas — Lighter Docs: Real World Assets (RWAs)
[43] https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism — Lighter Docs: RWA Pricing Mechanism
[44] https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism — Lighter Docs: Futures Contract Price Rolling Mechanism
[45] https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications — Lighter Docs: RWA Market Specifications
[46] https://docs.lighter.xyz/trading/funding — Lighter Docs: Funding
[47] https://apidocs.lighter.xyz/reference/candles — Lighter API: Candles
[48] https://apidocs.lighter.xyz/reference/fundings — Lighter API: Fundings
[61] https://docs.lighter.xyz/trading/liquidations-and-llp-insurance-fund — Lighter Docs: Liquidations and LLP Insurance Fund
[62] https://docs.lighter.xyz/trading/order-types-and-matching — Lighter Docs: Order Types & Matching
[72] https://docs.lighter.xyz/trading/contract-specifications — Lighter Docs: Contract Specifications
[75] https://docs.lighter.xyz/trading/fair-price-marking — Lighter Docs: Fair Price Marking
[76] https://docs.lighter.xyz/trading/pnl-and-total-account-value — Lighter Docs: PnL and Total Account Value
[77] https://docs.lighter.xyz/trading/multi-asset-margin — Lighter Docs: Multi-Asset Margin
[78] https://apidocs.lighter.xyz/reference/orderbookorders — Lighter API: Order Book Orders
[79] https://apidocs.lighter.xyz/reference/trades — Lighter API: Trades
[80] https://apidocs.lighter.xyz/reference/assetdetails — Lighter API: Asset Details
[81] https://apidocs.lighter.xyz/reference/markets — Lighter API: Markets
