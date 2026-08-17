# Day12：从官方目录构造可信的当前市场清单

> 状态：可开始
>
> 学习时间：30–45 分钟；助手实现和运行测试不占用户学习时间
>
> 当日成果：一个只读 `scan` 命令；它保留两家场所各自的完整市场身份，并判断当前目录与双边盘口是否足以进入 Day13。

## 今天真正要学什么

扫描器最先回答的不是“价差多大”，而是下面三个工程问题：

1. **我请求的究竟是哪一个市场？**
2. **目录记录、市场状态和盘口是否属于同一市场？**
3. **这份当前数据是否只够进入下一项研究，还是已经应该停止？**

今天不判断 `WTI` 与 `xyz:CL` 是否代表同一经济对象，也不计算费用、资金费或收益。那些问题从 Day13 开始。Day12 只保证后续计算不会建立在串错市场、过期硬编码或空盘口之上。

## 当前市场现象

在 `2026-08-17T12:32:01Z` 的一次只读查询中，四个原油市场返回了以下结果。[4][5][7]

| 场所 | 完整交易标识 | 本地编号 | 目录状态 | 返回买盘条目 | 返回卖盘条目 |
|---|---|---:|---|---:|---:|
| Lighter | `WTI` | `market_id=145` | `active` | 20 | 20 |
| Lighter | `BRENTOIL` | `market_id=159` | `active` | 20 | 20 |
| Hyperliquid `xyz` | `xyz:CL` | `asset=110029` | 未下架 | 20 | 20 |
| Hyperliquid `xyz` | `xyz:BRENTOIL` | `asset=110049` | 未下架 | 20 | 20 |

Lighter 的 20 条是限价订单记录；Hyperliquid 的 20 条是按价格聚合的二级订单簿（L2）档位。两个数字不能拿来比较深度，今天只用它们确认响应中买卖两侧都非空。

这次观察使用的只读请求是：

```text
GET  /api/v1/orderBooks
GET  /api/v1/orderBookOrders?market_id=145&limit=20
GET  /api/v1/orderBookOrders?market_id=159&limit=20
POST https://api.hyperliquid.xyz/info {"type":"perpDexs"}
POST https://api.hyperliquid.xyz/info {"type":"metaAndAssetCtxs","dex":"xyz"}
POST https://api.hyperliquid.xyz/info {"type":"l2Book","coin":"xyz:CL"}
POST https://api.hyperliquid.xyz/info {"type":"l2Book","coin":"xyz:BRENTOIL"}
```

这个快照只证明：查询时，官方目录中存在这些记录，并且盘口接口返回双边数据。它**没有证明**：

- `WTI` 与 `xyz:CL` 是同一合约；
- 两个 `BRENTOIL` 的单位、到期月份、价格来源和结算规则相同；
- 返回的盘口条目能成交目标数量；
- 任何方向扣除成本后有正收益。

因此 Day12 的成功结果不是“发现两个机会”，而是“得到四个身份明确、可以继续核对的市场记录”。

## 1. 市场身份不能只用名称

扫描器内部使用下面五部分确定一条市场记录：

```text
场所 + 产品类型 + 场所命名空间 + 完整交易标识 + 场所本地编号
```

对应当前例子：

```text
lighter | perp | default | WTI          | market_id=145
lighter | perp | default | BRENTOIL     | market_id=159
hyperliquid | perp | xyz | xyz:CL       | asset=110029
hyperliquid | perp | xyz | xyz:BRENTOIL | asset=110049
```

`BRENTOIL` 这个名称不是跨场所主键。即使两边名称完全相同，也只能生成一个**待核对映射**；Day13 还要检查单位、基准、结算和价格状态。

建议的数据类型：

```python
@dataclass(frozen=True)
class MarketIdentity:
    venue: str
    product_type: str
    venue_namespace: str
    symbol: str
    local_id: str
```

这里故意没有 `canonical_symbol="BRENT"`。在经济对象尚未核验前提前写入统一名称，会把一个研究假设伪装成事实。

## 2. 两家接口最容易出错的地方不同

### Lighter：盘口响应不携带市场身份

`orderBooks` 目录响应会给出 `symbol`、`market_id`、`market_type` 和 `status`。随后查询 `orderBookOrders?market_id=145` 时，盘口响应只包含买卖订单，不再重复 `market_id` 或 `symbol`。[1][6][7]

因此保存盘口时，程序必须同时保存**请求身份**：

```json
{
  "requested_market": {
    "venue": "lighter",
    "symbol": "WTI",
    "market_id": 145
  },
  "response": {
    "bids": [],
    "asks": []
  }
}
```

如果只保存裸响应，之后无法从响应本身证明这是谁的盘口。最危险的错误不是接口报错，而是程序把一个成功响应贴到错误的市场名称上。

### Hyperliquid：元数据与市场上下文按位置对应

`metaAndAssetCtxs` 返回两个数组：第一个对象中的 `universe` 保存市场元数据，第二个数组保存对应的市场上下文。[2][4]

安全解析顺序是：

```python
universe = response[0]["universe"]
contexts = response[1]

if len(universe) != len(contexts):
    raise SourceShapeError("meta/context length mismatch")

for index, (meta, context) in enumerate(zip(universe, contexts, strict=True)):
    record = normalize(meta=meta, context=context, index_in_meta=index)
```

下面的写法会制造静默错配：

```python
active_meta = [m for m in universe if not m.get("isDelisted", False)]
records = zip(active_meta, contexts)  # 错：只过滤了其中一个数组
```

只要中间出现一条下架记录，后面的市场上下文就会整体错位。程序仍能输出看似合理的价格，所以测试不能只断言“有 100 多条结果”，必须检查已知完整交易标识是否拿到自己的上下文。

另外，Hyperliquid 的 HIP-3 市场必须保留 `{dex}:{coin}` 完整名称；`CL` 不能代替 `xyz:CL`。交易使用的资产编号按 `100000 + perp_dex_index * 10000 + index_in_meta` 计算。在这次查询中，`xyz` 的 `perp_dex_index=1`，所以 `xyz:CL` 的资产编号是 `110029`，`xyz:BRENTOIL` 是 `110049`。[3][4] 解析器仍要另外保存 `index_in_meta`，因为它是把 `universe` 与 contexts 正确配对的位置，不等同于资产编号。

## 3. “目录活跃”和“盘口可用”是两个判断

目录状态与盘口状态分开保存：

```text
目录状态：active / inactive / delisted / unknown
盘口状态：two_sided / one_sided / empty / invalid
```

Day12 的处理规则：

| 条件 | `scan_status` | 原因代码 |
|---|---|---|
| 目录活跃，响应身份正确，买卖两侧都有有效价格与数量 | `ready_for_market_mapping` | 无 |
| 目录活跃，但本次未请求盘口 | `catalog_only` | `BOOK_NOT_INSPECTED` |
| 目录为 inactive 或 delisted | `stopped` | `MARKET_NOT_ACTIVE` |
| 盘口为空 | `stopped` | `BOOK_EMPTY` |
| 只有买盘或只有卖盘 | `stopped` | `BOOK_ONE_SIDED` |
| 请求与响应中的完整交易标识不同 | `invalid` | `IDENTITY_MISMATCH` |
| `universe` 与 contexts 长度不同 | `invalid` | `SOURCE_SHAPE_MISMATCH` |
| 用户指定的完整交易标识不存在 | `invalid` | `UNKNOWN_SYMBOL` |
| 本地编号或完整身份重复 | `invalid` | `DUPLICATE_IDENTITY` |

“可进入 Day13”只是允许继续检查经济对象，不是交易建议，也不是候选排名。

## 4. 今天要实现的最小程序

正式代码进入：

```text
src/monte_arb/
  market.py       # 市场身份、目录状态、盘口状态和原因代码
  adapters.py     # Lighter 与 Hyperliquid 官方响应解析
  cli.py          # scan 命令
```

程序先取得两家场所的完整目录，再只为调用者明确指定的市场请求盘口。目录扫描不应默认为几百个市场逐一请求盘口；这既浪费请求额度，也不能替代 Day13 的经济对象筛选。

外部调用只需要一个主要入口：

```python
report = scan_markets(adapters, inspect_books_for=market_identities)
```

复杂的场所差异留在两个解析器中，不把每家接口的字段散落到命令行和后续成本模块。

第一版命令使用 Python 标准库运行，不等待 Day14 的 NautilusTrader 环境：

```bash
PYTHONPATH=src python3 -m monte_arb.cli scan \
  --venue lighter \
  --venue hyperliquid:xyz \
  --inspect-book lighter/perp/default/WTI \
  --inspect-book lighter/perp/default/BRENTOIL \
  --inspect-book hyperliquid/perp/xyz/xyz:CL \
  --inspect-book hyperliquid/perp/xyz/xyz:BRENTOIL \
  --output research/runs/day12-scan.json
```

`--inspect-book` 只能引用本次目录中实际发现的完整身份；不存在或重复时显式失败。它选择要检查的单个市场，不声明这些市场可以彼此对冲。

输出至少包含：

```json
{
  "observed_at": "...",
  "markets": [
    {
      "identity": {
        "venue": "lighter",
        "product_type": "perp",
        "venue_namespace": "default",
        "symbol": "WTI",
        "local_id": "145"
      },
      "catalog_status": "active",
      "book_status": "two_sided",
      "scan_status": "ready_for_market_mapping",
      "reason_codes": []
    }
  ]
}
```

未请求盘口的活跃目录记录保留为 `catalog_only`，不会被误标为 `ready_for_market_mapping`。

原始响应和内容哈希用于以后复现扫描结果，但它们是研究辅助信息，不是今天的学习目标。

## 5. 测试只覆盖会制造错误决定的行为

使用冻结响应测试以下公开行为：

1. Lighter 的 `market_id` 与请求身份一起进入结果；裸盘口不会自行获得一个猜测的 symbol。
2. Hyperliquid 在原始顺序上配对元数据和上下文；长度不一致立即失败。
3. 未知完整交易标识返回 `UNKNOWN_SYMBOL`，不会落到列表第一项或默认市场。
4. 空盘口和单边盘口不能进入 Day13；未检查盘口的目录记录保持 `catalog_only`。
5. 同一冻结输入重复扫描，市场身份、状态和原因代码相同。

运行方式：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 6. 本课唯一理解检验

实现和真实运行完成后，只处理下面一个故障，不做固定模板填空：

> 开发者先从 `universe` 删除所有下架市场，再把结果与未经处理的 contexts 用 `zip` 配对。程序没有崩溃，却有一些活跃市场突然得到 `midPx=null`，另一些市场价格明显属于相邻标的。

你需要指出：

1. 哪个位置关系被破坏；
2. 为什么“数组长度仍然很多、价格也能转成数字”不能证明程序正确；
3. 应在哪一步检查并阻止这个结果进入扫描报告。

如果这个故障已经讲透，就不再额外要求预测、改规则或填写学习记录。若仍不清楚，再换一组短数据现场重放。

## 完成标准

Day12 完成时应同时满足：

- `scan` 能从当前官方目录发现全部市场，不依赖硬编码候选列表；
- 只为明确指定且确实存在的完整市场身份请求盘口；
- 输出保留场所、产品类型、场所命名空间、完整交易标识和本地编号；
- 两家响应各自最危险的身份错误有测试；
- 活跃且有双边盘口只被标为“可进入 Day13”；
- 你能解释为什么不能过滤一个位置数组后再与另一个数组配对。

## 当日文件

```text
src/monte_arb/market.py
src/monte_arb/adapters.py
src/monte_arb/cli.py
tests/fixtures/day12/
tests/test_day12_scan.py
research/manifests/day12-universe.json
research/runs/day12-scan.json
```

## Sources

[1] https://apidocs.lighter.xyz/reference/orderbooks — Lighter Order Books API
[2] https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals — Hyperliquid Perpetuals API
[3] https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids — Hyperliquid Asset IDs
[4] https://api.hyperliquid.xyz/info — Hyperliquid Info API (live endpoint)
[5] https://mainnet.zklighter.elliot.ai/api/v1/orderBooks — Lighter Order Books API (live endpoint)
[6] https://apidocs.lighter.xyz/reference/orderbookorders — Lighter Order Book Orders API
[7] https://mainnet.zklighter.elliot.ai/api/v1/orderBookOrders — Lighter Order Book Orders API (live endpoint)
