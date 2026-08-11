# Day 8 学习记录 — 统一跨场所数据结构

## 唯一问题

把 Lighter、Binance、Hyperliquid 的盘口放进同一张研究表时，哪些字段可以合并、哪些必须保留语义差异、哪些必须标 `unknown`？

## 实际用时与动作

- 抓取 13 个公开只读响应（含 2 个失败的 400 样本），全部保存原始 JSON + 元数据；
- 首次调用 Lighter `orderBookOrders` 只传 `market_id` 返回 400；按官方文档补 `limit` 后返回 200，失败样本保留为课程证据；
- 编写 `lab/venue_schema.py` 与 `lab/test_venue_schema.py`，输出 333 行统一长表；
- 浏览器打开 Day 8 lesson，验收题先 0/5（故意答错验证反馈），再 5/5；
- 全部测试 29/29 通过（原 22 + Day 8 新增 7）。

## 一手资料与查询时间

| 来源 | 内容 | 抓取时间（UTC） |
|---|---|---|
| Lighter orderBookOrders | `limit` 1–250 必填 | 2026-08-11 01:50–01:52 |
| Binance Order Book / Funding | `limit` 规则、`E`/`T`、fundingTime | 2026-08-11 01:50 |
| Hyperliquid Info / WebSocket | l2Book 每侧 ≤20、fundingHistory、500 分页上限 | 2026-08-11 01:50–02:01 |

## 关键发现

1. **档位语义不同**：Lighter 是订单级视图（`remaining_base_amount`，可部分成交）；Binance/Hyperliquid 是聚合档。
2. **时间戳不同**：Lighter 盘口无公共快照时间 → `missing_source_timestamp`；Binance 有 `E`/`T`；Hyperliquid 有 `time`。
3. **接口契约不同**：Lighter `limit` 必填（1–250）；Binance 有效值 `[5,10,20,50,100,500,1000]`；Hyperliquid 每侧最多 20。
4. **精度字段不同**：`supported_*_decimals` vs `pricePrecision`/`quantityPrecision` vs `szDecimals`。
5. **funding 时间单位不同**：Lighter 秒，Binance/Hyperliquid 毫秒。
6. **不可类比字段 ≥7 个**：size、source_timestamp、limit、price_precision、size_precision、min_order、funding_timestamp。

## 证据路径

```text
lab/data/day8_raw/*.json + *.meta.json
lab/data/day8_capture_manifest.json
lab/venue_schema.py / lab/test_venue_schema.py
lab/data/day8_venue_snapshots.csv
lab/data/day8_venue_field_mapping.json
lab/data/day8_venue_schema_summary.json
notes/venue-schema.md
lessons/0007-day8-venue-schema.html / reference/day8-venue-schema.html
```

## Go / No-Go / Blocked 结论

- 学习层面：**Day 8 完成**（验收 5/5、测试通过、证据可复查）。
- 研究层面：**Blocked**。跨场所统一表只是研究基础，成本、执行、账户 funding 和连续盘口证据仍未取得，不能因此认为策略可交易。

## 已确认 / 仍未知

- 已确认：三个场所盘口端点、limit 规则、时间戳语义、精度字段、funding 单位（官方文档 + 实际响应）。
- 仍未知：Lighter 盘口公共时间戳、Hyperliquid 最小单、funding rate 的账户账本语义、跨场所资金占用/转账/借贷成本。

## 明日唯一动作

Day 9：对 `$10/$20/$50/$100` 目标名义做盘口走档，计算 VWAP、spread、冲击、余量和未对冲名义，分开开仓/平仓，禁止用 midpoint 冒充成交。
