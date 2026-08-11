# Day 8 — 统一跨场所数据结构（venue schema）

> 唯一问题：把 Lighter、Binance、Hyperliquid 的数据放进同一张研究表时，
> 哪些字段可以合并，哪些字段必须保留语义差异，哪些字段必须标 `unknown`？

## 证据（均为本次实际抓取或官方文档）

| venue | endpoint | HTTP | 记录 | 时间（UTC） | 证据文件 |
|---|---|---|---|---|---|
| Lighter | `/api/v1/orderBookOrders?market_id=145&limit=20` | 200 | 20 bid + 20 ask | 2026-08-11 01:52 | `lab/data/day8_raw/lighter_wti_book_ok.json` |
| Lighter | `...?market_id=159&limit=20` | 200 | 20 bid + 20 ask | 2026-08-11 01:52 | `lab/data/day8_raw/lighter_brent_book_ok.json` |
| Lighter | `orderBookOrders?market_id=145`（缺 limit） | **400** | 0 字节 | 2026-08-11 01:50 | `lab/data/day8_raw/lighter_wti_book.json`（失败样本） |
| Binance | `/fapi/v1/depth?symbol=BTCUSDT&limit=20` | 200 | 20 bid + 20 ask | 2026-08-11 01:50 | `lab/data/day8_raw/binance_book.json` |
| Binance | `/fapi/v1/exchangeInfo` | 200 | BTCUSDT 规格 | 2026-08-11 01:50 | `lab/data/day8_raw/binance_exchange_info.json` |
| Binance | `/fapi/v1/fundingRate?symbol=BTCUSDT&limit=5` | 200 | 5 行 | 2026-08-11 01:50 | `lab/data/day8_raw/binance_funding.json` |
| Hyperliquid | `POST /info {"type":"meta"}` | 200 | BTC szDecimals=5 | 2026-08-11 01:50 | `lab/data/day8_raw/hyperliquid_meta.json` |
| Hyperliquid | `POST /info {"type":"l2Book","coin":"BTC"}` | 200 | 20/20 | 2026-08-11 01:50 | `lab/data/day8_raw/hyperliquid_l2book.json` |
| Hyperliquid | `POST /info {"type":"fundingHistory","coin":"BTC","startTime":<7d前>}` | 200 | 168 行 | 2026-08-11 02:01 | `lab/data/day8_raw/hyperliquid_funding_recent.json` |

全部请求元数据（HTTP 状态、latency、SHA-256、received_at）：
`lab/data/day8_capture_manifest.json` 与 `lab/data/day8_raw/*.meta.json`。

## 官方文档关键事实

- Lighter `orderBookOrders`：**必须**同时提供 `market_id` 和 `limit`（1–250）；只传 `market_id` 会返回 400。
  https://apidocs.lighter.xyz/reference/orderbookorders
- Lighter `orderBooks`：返回市场规格（费用百分比、最小基础数量、最小报价金额、size/price 小数位）。
  https://apidocs.lighter.xyz/reference/orderbooks
- Lighter WebSocket：`wss://mainnet.zklighter.elliot.ai/stream`；每 2 分钟至少一帧，否则断开。
  https://apidocs.lighter.xyz/docs/websocket-reference
- Binance `/fapi/v1/depth`：`limit` 有效值 `[5,10,20,50,100,500,1000]`，默认 500；每条 `[price, quantity]`；响应含 `lastUpdateId`、`E`、`T`。
  https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Order-Book
- Binance `/fapi/v1/fundingRate`：`limit` 最大 1000，缺省返回最近 200 条。
  https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History
- Hyperliquid Info：时间范围查询最多返回 500 个元素，需用返回时间戳分页；
  `l2Book` 每侧最多 20 档；`candleSnapshot` 最多 5000 根。
  https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
- Hyperliquid WebSocket：主网 `wss://api.hyperliquid.xyz/ws`；服务端可能无公告断线，需自动重连，重连后快照 ack 补齐。
  https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket

## 最小统一 schema

```text
venue, market, instrument_type, source_timestamp, received_at,
price_semantics, bid, ask, size, funding_rate, funding_timestamp,
precision, quality_flags, raw_ref
```

## 字段映射与 not_equivalent 清单（≥5 个，全部有证据）

| 概念 | Lighter | Binance | Hyperliquid | 判断 |
|---|---|---|---|---|
| 盘口单档 | `asks[i].price`+`remaining_base_amount`（可部分成交，`initial_base_amount`≠`remaining`） | `asks[i][0]`+`[1]`（聚合档） | `levels[1][i].px`+`sz`+`n`（聚合档，带订单数） | **not_equivalent**：Lighter 单档含订单级字段且是 REST 订单级视图；其余是聚合档。 |
| 档位数量 | `limit` 1–250，必填 | `limit` 5–1000，默认 500 | 每侧最多 20 | **not_equivalent**：上限与必填性不同。 |
| 盘口时间 | 无公共 `timestamp`（订单字段 `order_expiry`） | `E`（消息输出）/`T`（交易时间） | `time`（毫秒） | **not_equivalent**：Lighter 无等价公共快照时间。 |
| 小数位 | `supported_size_decimals`=3、`supported_price_decimals`=3 | `quantityPrecision`=3、`pricePrecision`=2 | `szDecimals`=5（meta） | **not_equivalent**：Lighter 用两个字段，Binance 用 precision，Hyperliquid 只有 szDecimals。 |
| 最小单 | `min_base_amount`/`min_quote_amount` | `LOT_SIZE.minQty`+`MIN_NOTIONAL` | 无等价公开字段 | **not_equivalent**：Hyperliquid 最小单未在 meta 暴露。 |
| funding 时间 | `timestamp`（秒） | `fundingTime`（毫秒） | `time`（毫秒） | **not_equivalent**：单位不同（秒 vs 毫秒）。 |
| funding rate | `rate`（小数） | `fundingRate`（小数） | `fundingRate`（小数） | 可比，但语义/账本未核验，保留 `unknown` 边界。 |
| 数量单位 | `remaining_base_amount` 字符串 | `quantity` 字符串 | `sz` 字符串 | 可比，但 Lighter 为订单级、可部分成交。 |

## 验收（迁移）

1. 看盘口时，先确认档位是聚合档还是订单级；
2. 若只给 `market_id` 不传 `limit`，Lighter 会返回什么？（400）
3. `source_timestamp` 缺省时，是否允许用 `received_at` 冒充？（不允许，标记 `missing_timestamp`）
4. 最小单、小数位、funding 时间单位在三个场所是否一致？（不一致，列明）
5. 至少给出 5 个 `not_equivalent` 字段。

## 证据路径

```text
lab/data/day8_raw/*.json + *.meta.json
lab/data/day8_capture_manifest.json
lab/venue_schema.py            # 统一 schema 与字段映射
lab/test_venue_schema.py       # 测试
notes/venue-schema.md          # 本文件
```

## 边界声明

- 全部数据为公开只读快照；不连接私钥、不发单、不认证。
- `received_at` 与 `source_timestamp` 是两种时间，不得混用。
- 跨场所资金费收益仍需资金占用、转账、借贷、保证金、延迟与执行风险证据；本页不构成可交易结论。
