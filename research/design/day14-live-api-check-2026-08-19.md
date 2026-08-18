# Day14 实时 API 核对（2026-08-19）

> 核对窗口（本地 CST）：2026-08-19 07:30–07:40（UTC 2026-08-18T23:30–23:40Z）。
> 方法：curl 直连双方公共 REST 端点验证实际响应；官方文档核对（Lighter apidocs.lighter.xyz、Hyperliquid hyperliquid.gitbook.io）；官方 SDK 源码核对（elliottech/lighter-python、hyperliquid-dex/hyperliquid-python-sdk）。全部动态事实带时间戳与来源（见第 5 节）。本文件只核对事实，不提供交易建议。
> 与 `research/design/workbench-primary-sources.md`（2026-08-18 核对）的关系：本文件更新动态实现细节；静态设计结论仍以该文件为准。

## 1. 结论摘要（Day14 v0 最小事实）

1. Lighter 公共 REST 基址 `https://mainnet.zklighter.elliot.ai/api/v1/`。`orderBooks` 返回 `{code, order_books[]}`，共 235 个市场（227 perp / 8 spot；217 active / 18 inactive；活跃 perp 210 个）。`orderBookOrders` 返回 `{code, total_asks, asks[], total_bids, bids[]}`，**逐单而非聚合价档**，响应**没有时间戳**，limit 为每侧上限（1–250）。`funding-rates` 返回 `{code, funding_rates[]}`，718 条 = 210 个活跃 perp × 最多 4 个交易所来源，`exchange` 字段区分来源，本所条目为 `exchange=="lighter"`。
2. Lighter 限流（官方文档）：标准（未认证）账户 60 请求/滚动分钟；public 端点权重 300（"Other endpoints" 类，含 orderBooks/orderBookOrders/funding-rates）；超限返回 HTTP 429/405，防火墙冷却 60 秒。**全市场逐 market 扫 orderBookOrders（210 个）会超出 60/min，Day14 只能扫候选市场（≤3 个）。**
3. Hyperliquid：`perpDexs` 当前返回 11 个元素：`null`（主盘）+ 10 个 HIP-3 dex（xyz、flx、vntl、hyna、km、abcd、cash、para、mkts、io），响应含 `assetToStreamingOiCap`、`subDeployers`、`assetToFundingMultiplier`、`assetToFundingInterestRate`。`metaAndAssetCtxs` 支持 `dex` 参数（空串=主盘），主盘 232 资产，xyz 114 资产；响应为 `[meta, assetCtxs]` 两元素列表。`l2Book` 用 `coin` 参数（`"BTC"` 或 `"xyz:NVDA"` 格式），响应 `{coin, time(毫秒), levels: [[bids...],[asks...]]}`，每档 `{px, sz, n}`。
4. Hyperliquid 限流（官方文档）：REST 按 IP 合计 1200 权重/分钟；`l2Book` 权重 2，其余 info（含 metaAndAssetCtxs、perpDexs）权重 20 → 分钟预算：l2Book 600 次、metaAndAssetCtxs 60 次。WS 每 IP 最多 10 连接、1000 订阅。
5. 符号映射（2026-08-18T23:33Z 快照）：Lighter 227 个 perp 符号中，97 个与 HL 主盘 coin 完全同名，59 个与 `xyz:<symbol>` 后缀完全同名（需加 `xyz:` 前缀请求），71 个两边都无同名；**三重重叠（Lighter ∩ 主盘 ∩ xyz）= 0，HL 主盘 ∩ xyz 命名 = 0**（当前快照，不可硬编码）。同名不能确认同标的：Lighter 目录无资产类别字段；`LITE`、`QNT`、`BE`、`BOT` 等符号在两边目录中含义可能不同；当日实测 LITE/SPCX 两边价格接近（一致性好），QNT/BE 在 Lighter 盘口为空（无法对照）。

## 2. Lighter 端点与响应形状（实测）

基址：`https://mainnet.zklighter.elliot.ai/api/v1/`（官方 SDK `lighter/endpoint_profiles.py` 与 apidocs 一致；另有 robinhood 环境 `api.rh.lighter.xyz`，Day14 不用）。

### 2.1 `GET /api/v1/orderBooks`（无参数）

实测（2026-08-18T23:32:31Z，HTTP 200，113 KB）：

```json
{"code": 200, "order_books": [{
  "symbol": "OP", "market_id": 55, "market_type": "perp",
  "base_asset_id": 0, "quote_asset_id": 0, "status": "active",
  "taker_fee": "0.0000", "is_taker_fee_enabled": true,
  "maker_fee": "0.0000", "is_maker_fee_enabled": true,
  "liquidation_fee": "1.0000",
  "min_base_amount": "80.0", "min_quote_amount": "10.000000",
  "order_quote_limit": "281474976.710655",
  "supported_size_decimals": 1, "supported_price_decimals": 5, "supported_quote_decimals": 6,
  "created_at": "1753809197905", "multiplier": "1.000000000000000000"
}, ...]}
```

- 全部 235 个订单簿同一字段集（18 个字段）；`status` 只有 `active`/`inactive`；`market_type` 只有 `perp`/`spot`。
- **没有资产类别（crypto/RWA/指数/外汇）字段**——判断标的只能靠外部知识或价格对照。
- 汇总：227 perp（210 active / 17 inactive）、8 spot（7 active / 1 inactive）。

### 2.2 `GET /api/v1/orderBookOrders?market_id=<int16>&limit=<1..250>`

官方文档参数：`market_id`（int16，必填）、`limit`（int64，必填，1–250）。实测（market_id=55 即 OP）：

```json
{"code": 200, "total_asks": 5, "asks": [
  {"order_index": 15762598835430320, "order_id": "15762598835430320",
   "owner_account_index": 317068, "initial_base_amount": "11118.7",
   "remaining_base_amount": "11118.7", "price": "0.08205",
   "order_expiry": 1789515146146, "transaction_time": 0}, ...],
 "total_bids": 5, "bids": [...]}
```

- **逐单响应**：每条是一张挂单（含 owner_account_index），不是聚合价档；构建 L2 必须按 `price` 聚合（同价多单合并）。asks 按价升序、bids 按价降序。
- `total_asks`/`total_bids` 只是本次返回条数（=min(limit, 实际挂单数)），不是全深度计数。
- limit=250 实测（OP）：返回 39 asks / 34 bids——**盘口稀疏，limit 是上限不是保证**。
- **响应没有盘口快照时间戳**：快照时间只能记本机请求时刻，不能声称是盘口生成时间。
- 字段说明：`price`/`initial_base_amount`/`remaining_base_amount` 为字符串；`order_expiry` 为毫秒时间戳（样例 1789515146146 = 2026-09-15）；`transaction_time` 实测为 0。
- 陷阱：部分活跃市场盘口为空（见 4.3 实测 QNT/BE 无任何 bids/asks），实现必须处理空列表。

### 2.3 `GET /api/v1/funding-rates`（无参数）

实测（2026-08-18T23:32:39Z，HTTP 200，51 KB）：

```json
{"code": 200, "funding_rates": [
  {"market_id": 43, "exchange": "binance", "symbol": "TRX", "rate": -2.477e-05},
  {"market_id": 43, "exchange": "bybit", "symbol": "TRX", "rate": -0.00012687},
  {"market_id": 43, "exchange": "hyperliquid", "symbol": "TRX", "rate": 5.9408e-05},
  {"market_id": 43, "exchange": "lighter", "symbol": "TRX", "rate": 4e-05}, ...]}
```

- 718 条；`exchange` 分布：lighter 210、binance 189、bybit 186、hyperliquid 133。同一 `market_id` 最多 4 个来源（实测分布：4 源 113 个、3 源 67 个、2 源 20 个、1 源 25 个）。
- **这是跨交易所参考费率表**：`exchange=="lighter"` 才是 Lighter 本所当前费率。225 个 market_id 全部在 orderBooks 中；`exchange=="lighter"` 恰好覆盖全部 210 个活跃 perp，17 个 inactive perp 与 8 个 spot（market_id 2048–2055）无任何条目。
- `rate` 为小数（如 -2.477e-05），不是百分比；取本所条目即可，不要用其他交易所条目冒充本所费率。

### 2.4 补充：`GET /api/v1/orderBookDetails?market_id=<int16>`（可选）

返回 `{code, order_book_details: [...]}`，字段 = orderBooks 全部字段 + 精度（`size_decimals`、`price_decimals`、`quote_multiplier`）、保证金分数（`default_initial_margin_fraction` 等）、当前上下文（`mark_price`、`index_price`、`last_trade_price`、`daily_*`、`open_interest`）、资金费参数（`funding_premium_multiplier`、`funding_clamp_small/big`、`base_interest_rate`）、`market_config`（trading_hours、rfq_enabled、hidden 等）。Day14 若要对单个候选做上下文页，可选用；不是最小必需。

### 2.5 Lighter 限流（官方文档 apidocs.lighter.xyz/docs/rate-limits，约 1 个月前更新）

- REST（`/api/v1/`，不含 sendTx/sendTxBatch）：按 IP 与 L1 地址双重限制。未认证标准账户：**60 请求/滚动分钟**；Premium 24000 权重/分；Plus 120000；Builder 240000（需申请并认证每个请求）。
- 权重表（对认证账户生效）：`trades`/`recentTrades` = 600；`accountInactiveOrders`、`deposit/latest` = 100；`sendTx`/`sendTxBatch`/`nextNonce` = 6；**"Other endpoints"（含 orderBooks、orderBookOrders、funding-rates、orderBookDetails）= 300**。
- 超限行为：HTTP 429 或 405；防火墙冷却固定 60 秒；API 服务器冷却 = `weightOfEndpoint/(totalWeight/60)`（示例：weight 300 端点冷却 750ms）。REST 被限时 WS 同时受限。
- WS（每 IP）：连接 255、每连接订阅 500、每分钟新连接 255、客户端每分钟消息 200、inflight 50。Day14 只用 REST 快照，WS 留待 Day15。
- 实测响应头无 `X-RateLimit-*` 字段（2026-08-18T23:36:48Z 检查 orderBooks 响应头）。
- **Day14 含义**：未认证扫描 1 次 orderBooks + 1 次 funding-rates + 每个候选 1 次 orderBookOrders（≤3 候选）≈ 5 请求，远低于 60/min；但"全 210 个 perp 逐市场扫盘口"（210+ 请求）会超限，只能用于候选市场或认证后（Builder/Premium）运行。

## 3. Hyperliquid 端点与响应形状（实测）

基址：`https://api.hyperliquid.xyz/info`（POST + JSON body）。

### 3.1 `{"type":"perpDexs"}`

实测（2026-08-18T23:34:03Z，HTTP 200）：返回 11 元素数组，**第一个元素 `null`（主盘无条目）**，其后 10 个 HIP-3 dex：

| # | name | fullName | assetToStreamingOiCap 条数 |
|---|---|---|---|
| 0 | null | 主盘（无条目） | — |
| 1 | xyz | XYZ | 114 |
| 2 | flx | Felix Exchange | 15 |
| 3 | vntl | Ventuals | 15 |
| 4 | hyna | HyENA | 24 |
| 5 | km | Markets by Kinetiq | 22 |
| 6 | abcd | ABCDEx | 0 |
| 7 | cash | dreamcash | 15 |
| 8 | para | Paragon | 20 |
| 9 | mkts | Markets By Kinetiq | 2 |
| 10 | io | EntropyIO | 0 |

单 dex 条目字段：`name`、`fullName`、`deployer`、`oracleUpdater`、`feeRecipient`、`assetToStreamingOiCap`（`[["xyz:AAOI","25000000.0"],...]` 形式，字符串金额）、`subDeployers`、`assetToFundingMultiplier`、`assetToFundingInterestRate`（后三者实测存在；官方文档示例只到 assetToStreamingOiCap）。Day14 目标为 xyz，但发现 dex 列表用 `perpDexs` 动态获取，不写死。

### 3.2 `{"type":"metaAndAssetCtxs","dex":"<dex>"}`（dex 可省略）

官方文档：`dex` 为字符串，"Defaults to the empty string which represents the first perp dex"（即主盘）。两种模式实测：

- 无 dex（主盘，2026-08-18T23:32:49Z）：`[meta, assetCtxs]`，meta keys = `universe`(232)、`marginTables`、`collateralToken`；assetCtxs 与 universe 等长。
- `dex:"xyz"`（2026-08-18T23:33:00Z）：同构，`universe` 114 个（名称形如 `xyz:XYZ100`、`xyz:TSLA`）；meta **响应中不含 dex 字段**（dex 只作为请求参数）。

universe 条目（xyz 实测）：`{"szDecimals":4, "name":"xyz:XYZ100", "maxLeverage":30, "marginTableId":30, "growthMode":"enabled", "lastFeeScaleChangeTime":"2025-11-23T17:37:10.033211662", "deployerFeeScale":"1.0"}`（主盘条目另有 `isDelisted`、`hasOracle`、`onlyIsolated` 等字段，xyz 条目字段集更小）。

assetCtx 条目（实测）：`{"funding":"0.00000625","openInterest":"7916.9594","prevDayPx":"29985.0","dayNtlVlm":"279543086.758800149","premium":"-0.0001528065","oraclePx":"29449.0","markPx":"29445.0","midPx":"29444.5","impactPxs":["29444.0","29445.0"],"dayBaseVlm":"9435.4366"}`。**`funding` 是当前资金费率（小数）**，可替代 Lighter `funding-rates` 的本所条目做双榜对照；`oraclePx`/`markPx` 解释价差但（沿用手册结论）不能单独证明 external/internal oracle 状态。

### 3.3 `{"type":"l2Book","coin":"<coin>"}`

官方文档参数：`coin`（必填；文档示例 `"BTC"`，实测 `"xyz:NVDA"` 等 dex 前缀格式可用）；可选 `nSigFigs`（2–5 或 null）、`mantissa`（仅 nSigFigs=5 时，1/2/5）。实测（2026-08-18T23:32:49Z）：

```json
{"coin": "xyz:NVDA", "time": 1787095968922, "levels": [
  [{"px": "219.05", "sz": "43.057", "n": 4}, ...],   // levels[0] = bids（降序）
  [{"px": "219.06", "sz": "1.0", "n": 1}, ...]       // levels[1] = asks（升序）
]}
```

- `time` 为毫秒时间戳（1787095968922 = 2026-08-18T23:32:48Z，与请求时刻一致）——**HL 盘口快照自带时间戳，Lighter 没有**。
- `levels` 两元素：`[bids, asks]`；每档 `px`/`sz` 字符串 + `n`（档内挂单数）。默认深度：主盘约 20 档/侧（实测 xyz:NVDA 返回 20 档），可选 `nSigFigs`/`mantissa` 聚合。
- 注意：**HIP-3 dex 的 coin 必须带前缀**（`xyz:NVDA`）；不带前缀 `"NVDA"` 会查主盘。实现上用 `metaAndAssetCtxs` 的 universe name 直接作为 l2Book 的 coin 值即可，不要自己拼。

### 3.4 Hyperliquid 限流（官方文档 rate-limits-and-user-limits 页）

- REST 按 IP：**1200 权重/分钟**。`l2Book`、`allMids`、`clearinghouseState`、`orderStatus`、`spotClearinghouseState`、`exchangeStatus` = 权重 2；`userRole` = 60；**其余 info（含 meta、metaAndAssetCtxs、perpDexs）权重 20**；`recentTrades` 等另有按返回条数的附加权重；explorer API 权重 40。
- 分钟预算含义：l2Book 600 次/分（全 xyz 114 资产扫 2 轮也仅 228），metaAndAssetCtxs 60 次/分——Day14 的"每轮全市场扫描"在 HL 侧没有压力。
- WS 每 IP：最多 10 连接、30 新连接/分、1000 订阅、2000 消息/分。Day14 不用。

## 4. Lighter ↔ Hyperliquid 符号映射

### 4.1 映射发现方法（不写死）

1. `Lighter orderBooks`（过滤 `market_type=="perp"` 且 `status=="active"`）→ Lighter 侧符号集（无后缀，如 `OP`、`SPCX`）。
2. `HL meta`（主盘 universe `name`）→ 主盘 coin 集；`HL metaAndAssetCtxs dex="xyz"` → xyz coin 集（自带 `xyz:` 前缀）。
3. 匹配规则：Lighter 符号 == 主盘 coin（直连 `l2Book coin="OP"`）；Lighter 符号 == `xyz:` 后缀（请求 `coin="xyz:SPCX"`）。
4. 每日重建映射表并保存快照（含两边目录与价格），Day14 先扫描再定候选。

### 4.2 当日统计（2026-08-18T23:33Z 快照）

- Lighter 活跃 perp：210；HL 主盘：232；xyz：114。
- **97** 个 Lighter 符号与主盘 coin 完全同名（BTC、ETH、SOL、OP、WIF、JUP、POPCAT、TRUMP、SPX 等）。
- **59** 个与 `xyz:<symbol>` 完全同名（AAPL、AMD、NVDA、TSLA、GOOGL、MSTR、PLTR、COIN、GME、SPCX、LITE、QNT、BE、BB、BOT、H100、WHEAT、BRENTOIL 等）。
- **71** 个无同名：外汇对（EURUSD、USDJPY、GBPUSD、USDCHF、USDHKD、USDKRW、USDCAD、NZDUSD、AUDUSD）、指数/金属（US500、US100、KRCOMP、SPY、QQQ、IWM、XAU、XAG、XPT、XPD、XCU、WTI）、股票（BYD、SAMSUNG、SMIC、TENCENT、XIAOMI、OPENAI、ANTHROPIC、SPACEX、TTWO、IWM 等）、代币（WEN、PIPPIN、EDEN、DUSK、CRO、NMR、1000BONK、1000PEPE 等）——当前 HL 侧无同名标的，映射不到。
- **三重重叠（Lighter ∩ 主盘 ∩ xyz）= 0；HL 主盘 ∩ xyz = 0**：当前快照下"符号 → dex"无歧义，但这是快照性质，不是协议保证，实现必须保留映射来源与日期。

### 4.3 哪些映射不能仅靠 symbol 确认

1. **同名≠同标的（所有匹配都适用）**：两边目录都只有 ticker，无资产类别字段；同名只构成候选假设。确认至少需要：扫描时刻两边 oracle/mark 价格对照（应接近且方向一致）、合约规格（multiplier、min size、decimals）、以及 listing 文档/公告中的标的信息。Day14 只做"候选标注 + 价格对照展示"，不声称确认。
2. **高风险同名样例（当日目录）**：`LITE`（Lighter 生态代币 LIT/LITE 与 xyz 的 LITE 很可能是不同标的——当日实测价格都在 ~$864–868，一致性看似好，但这是单一快照，不能替代标的身份确认）；`QNT`、`BE`、`BB`、`BOT`、`H100`、`MINIMAX`、`STRC` 等符号在两边目录中可能分别指代不同资产（代币 vs 股票/ETF/指数）。判断依据需来自价格行为与公开 listing 信息，symbol 本身不足以定论。
3. **无法对照的情形**：Lighter 部分活跃市场盘口为空（当日实测 QNT、BE 的 orderBookOrders 返回 0 条 bids/asks），此时无价格可对照，只能标 unknown。
4. **Lighter 内部同名不同品**：同一标的在 Lighter 可能出现多个符号（如 SPX 与 US500/SP500 都是标普相关产品），"Lighter 符号 ↔ HL 符号"映射表应逐符号建立，不做 1:1 假设。
5. **HL 侧 dex 前缀是强约束**：`xyz:` 前缀在 HL 命名中是规范的一部分（universe name 自带前缀），不出现主盘/xyz 裸名冲突（当日如此）；但实现仍应从 universe 名称取 coin 值，不手工拼前缀。

### 4.4 当日价格对照实例（2026-08-18T23:37Z，只作展示不作结论）

| 符号 | HL xyz 最优 bid/ask | Lighter 最优 bid/ask | 备注 |
|---|---|---|---|
| SPCX | 142.49 / 142.50 | 142.52 / 142.54 | 一致性好 |
| LITE | 864.47 / 864.64 | 865.01 / 868.49 | 接近但价差不同 |
| QNT | 59.495 / 59.529 | 空盘（0 条） | 无法对照 |
| BE | 206.51 / 206.58 | 空盘（0 条） | 无法对照 |

## 5. 今日动态事实时间戳与来源

统一说明：请求时刻为 2026-08-18T23:30–23:40Z（本地 2026-08-19 07:30–07:40 CST）；UTC+8。以下"快照时间"均为本机请求时刻（Lighter 响应无自身时间戳；HL l2Book 自带 `time`）。

| 事实 | 值 | 来源 | 时间戳（UTC） |
|---|---|---|---|
| Lighter orderBooks 全量 | 235 市场（227 perp/8 spot；active 217；活跃 perp 210） | `GET https://mainnet.zklighter.elliot.ai/api/v1/orderBooks`（HTTP 200） | 2026-08-18T23:32:31Z |
| Lighter orderBookOrders 形状 | `{code,total_asks,asks[],total_bids,bids[]}`，逐单、无时间戳；limit=250 时 OP 仅 39/34 条 | `GET .../orderBookOrders?market_id=55&limit=250` | 2026-08-18T23:32:39Z（limit=5 同刻） |
| Lighter funding-rates 全量 | 718 条；lighter 210/binance 189/bybit 186/hyperliquid 133；覆盖全部 210 个活跃 perp | `GET .../funding-rates` | 2026-08-18T23:32:39Z |
| Lighter orderBookDetails（补充） | 精度/保证金/mark/index/OI/资金费参数字段确认 | `GET .../orderBookDetails?market_id=55` | 2026-08-18T23:37Z 前后 |
| Lighter 限流规则 | 标准账户 60 req/min；public 端点权重 300；429/405；防火墙冷却 60s；WS 255 连接/500 订阅 | apidocs.lighter.xyz/docs/rate-limits（页面标注"约 1 个月前更新"） | 读取时刻 2026-08-18T23:38Z |
| Lighter REST 响应头 | 无 X-RateLimit-* 头 | 实测响应头 | 2026-08-18T23:36:48Z（Date 头） |
| HL perpDexs | 11 元素：null + 10 dex（xyz 114、flx 15、vntl 15、hyna 24、km 22、abcd 0、cash 15、para 20、mkts 2、io 0 个 OI cap 条目） | `POST https://api.hyperliquid.xyz/info {"type":"perpDexs"}`（HTTP 200） | 2026-08-18T23:34:03Z |
| HL metaAndAssetCtxs（主盘） | 232 资产；`[meta,ctxs]` 形状；ctx 含 funding/oraclePx/markPx/midPx/impactPxs/OI/日成交 | `{"type":"metaAndAssetCtxs"}` | 2026-08-18T23:32:49Z |
| HL metaAndAssetCtxs（xyz） | 114 资产；universe name 带 `xyz:` 前缀；meta 响应无 dex 字段 | `{"type":"metaAndAssetCtxs","dex":"xyz"}` | 2026-08-18T23:33:00Z |
| HL l2Book（xyz:NVDA 等） | `{coin,time(ms),levels[bids,asks]}`，档 `{px,sz,n}`；响应 time=1787095968922（23:32:48Z） | `{"type":"l2Book","coin":"xyz:NVDA"}` | 2026-08-18T23:32:49Z |
| HL meta（dex=xyz） | universe 114；marginTables/collateralToken 确认 | `{"type":"meta","dex":"xyz"}` | 2026-08-18T23:37Z 前后 |
| HL 限流规则 | 1200 权重/min/IP；l2Book=2；其余 info=20；WS 10 连接/1000 订阅 | hyperliquid.gitbook.io/.../rate-limits-and-user-limits.md | 读取时刻 2026-08-18T23:34:30Z |
| 符号映射统计 | 97 主盘同名 / 59 xyz 同名 / 71 无匹配 / 三重 0 / 主盘∩xyz 0 | 由上述 orderBooks + meta + metaAndAssetCtxs(dex=xyz) 计算 | 2026-08-18T23:33Z（数据） |
| 价格对照（SPCX/LITE/QNT/BE） | 见 4.4 | HL l2Book + Lighter orderBookOrders | 2026-08-18T23:37Z |
| lighter-python SDK | main commit `0cafd65ab058`（2026-08-18T13:38:32Z） | GitHub API | 2026-08-18T23:35Z 前后 |
| hyperliquid-python-sdk | master commit `2fdb18f95176`（2026-06-04T19:46:55Z） | GitHub API | 2026-08-18T23:35Z 前后 |

## 6. 明确 unknown（当前核对无法确认）

1. Lighter `orderBooks`/`orderBookOrders`/`funding-rates` 的**精确权重归属**：官方权重表只列了部分端点，orderBooks 等归入 "Other endpoints"(300) 是文档结构推断，官方未逐端点列出；未认证账户 60/min 的硬上限不受影响。
2. Lighter 各市场的**资产类别与标的身份**：公开目录无该字段；同名符号是否同标的未经 listing 文档与多快照价格序列确认。
3. Lighter 空盘市场（如当日 QNT、BE）的**可成交价差**：无盘口数据，unknown，不猜价。
4. `funding-rates` 的**更新频率与"当前"语义**：响应无时间戳，无法确认每条 rate 的生成时刻；只能记录本机请求时刻。
5. HL `perpDexs` 中 `abcd`、`io` 两个 dex 的 OI cap 为空（0 条）：是"无资产"还是"尚未启用"unknown；Day14 不扫这两个 dex。
6. `metaAndAssetCtxs(dex)` 响应中的 `growthMode`/`deployerFeeScale` 等新字段（2025-11-23 的 lastFeeScaleChangeTime）的官方语义说明未在本轮核对中取得，Day14 不使用这些字段做判断。
7. Lighter WS 与 HL WS 的具体消息形状（Day15 再核对；Day14 只 REST 快照，不涉及）。

## 7. Day14 实现提示（只读约束下）

- 请求预算：Lighter 未认证 ≤60 req/min → 每轮 = 1×orderBooks + 1×funding-rates + ≤3×orderBookOrders（+可选 1×orderBookDetails），约 5–6 请求；HL 侧无压力（l2Book 权重 2）。不要做全市场 Lighter 盘口扫描。
- Lighter orderBookOrders 是逐单流：聚合按 `price` 合并 `remaining_base_amount` 成 L2 档；同价多单的档量是求和而非取最大。
- 快照时间戳：Lighter 侧一律记"本机请求时刻"，并在数据模型里与 HL l2Book 自带的 `time` 区分标注；不给 Lighter 盘口伪造时间。
- 空盘口：bids/asks 为空时该市场"无可成交价差"，从候选榜剔除或标 unknown，不填 0 价。
- funding 对照：Lighter 取 `exchange=="lighter"` 条目；HL 取 `metaAndAssetCtxs[1][i].funding`（与 universe 同序）。两边都是小数费率，单位一致。
- 映射表：每日从三个目录重建并落盘（含来源日期）；候选展示时对每个映射标注"符号同名候选（未确认标的）"与价格对照结果。
- 双榜透明：交易吸引力榜与价值榜分开；最多 3 个候选；不凑数；不声称持续时间、完整费用或盈利结论（沿用 workbench-primary-sources.md 第 7 节边界）。

## Sources

- Lighter API Reference: https://apidocs.lighter.xyz/reference/orderbookorders 、/reference/orderbooks 、/reference/funding-rates 、/reference/orderbookdetails
- Lighter Rate Limits: https://apidocs.lighter.xyz/docs/rate-limits
- Lighter SDK（main commit 0cafd65ab058）: https://github.com/elliottech/lighter-python （configuration.py 基址、endpoint_profiles.py、api/info_api.py、api/funding_api.py、api/order_api.py）
- Hyperliquid Perpetuals Info Endpoints: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals.md
- Hyperliquid Rate limits and user limits: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits.md
- Hyperliquid SDK（master commit 2fdb18f95176）: https://github.com/hyperliquid-dex/hyperliquid-python-sdk
- 本文所有"实测"数据来自 2026-08-18T23:30–23:40Z 对 `https://mainnet.zklighter.elliot.ai/api/v1/` 与 `https://api.hyperliquid.xyz/info` 的直连请求（见第 5 节时间戳表）。
