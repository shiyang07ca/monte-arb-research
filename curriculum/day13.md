# Day13：经济对象与 RWA 价格状态

> 状态：进行中
>
> 学习时间：30–45 分钟；助手整理来源、实现和测试不占用户学习时间
>
> 互动入口：`lessons/0009-day13-economic-object.html`
>
> 当日成果：一个失败关闭的经济对象映射器，以及对当前原油候选“已知、未知、不可比”的明确判断。

## 今天真正要学什么

Day12 已证明四份盘口属于四个明确市场。Day13 继续回答两个不同问题：

1. 两个市场是否代表同一个经济对象？
2. 在某个报价时刻，两边是否处于可以比较的价格来源和展期状态？

名称相似、单位相同或价格接近，都不能单独回答这两个问题。

## 当前官方现象

Lighter 官方当前规格把 `WTI` 定义为 1 桶 WTI Light Sweet Crude Oil，把 `BRENTOIL` 定义为 1 桶 Brent Crude Oil；当前链接分别指向 `WTIQ6/USD` 与 `BRENTU6/USD` 价格源。[1]

Lighter 的当前 2026 年 8 月展期表又说明：`WTI` 在 `2026-08-07` 至 `2026-08-13` 从 `U6` 过渡到 `V6`；`BRENTOIL` 在同一日期范围从 `V6` 过渡到 `X6`。WTI 每天 17:30 ET 调整权重，Brent 每天 19:00 ET 调整权重。[2]

trade.xyz 当前商品说明同样把 `WTIOIL (CL)` 定义为 1 桶 WTI，把 `BRENTOIL` 定义为 1 桶 Brent，并说明能源商品使用指定期货合约、在每月第 5–10 个工作日附近展期。[3] 当前规格索引显示 `WTIOIL` 的 underlying 为 `Q6/USD`，`BRENTOIL` 为 `U6/USD`；但该表没有在字段中明确写出合约年份，且官网不同页面的当前月份文字需要先解释时间含义，不能直接把 `U` 或 `V` 当作完整、永久合约身份。[4]

因此当前最诚实的程序结果是：

```text
WTI ↔ xyz:CL              unknown: CONTRACT_YEAR_UNKNOWN
BRENTOIL ↔ xyz:BRENTOIL  unknown: CONTRACT_YEAR_UNKNOWN
WTI ↔ xyz:BRENTOIL       not_comparable: BENCHMARK_MISMATCH + CONTRACT_MONTH_MISMATCH
```

前两对不是“已经证明相同”，而是“基准和单位看起来一致，但完整合约月份证据仍不够”。第三对明确不可比，因为 WTI 与 Brent 是不同原油基准。

## 经济对象需要哪些字段

```python
@dataclass(frozen=True)
class EconomicSpecification:
    identity: MarketIdentity
    asset_class: str | None
    benchmark: str | None
    unit: str | None
    quote_currency: str | None
    settlement_currency: str | None
    contract_month_code: str | None
    contract_year: str | None
    external_session: str | None
    pricing_rule: str | None
    evidence: tuple[str, ...]
```

这里故意使用 `None` 表示未知。映射器不能因为两个 symbol 都包含 `OIL`，或价格都在 80 美元附近，就自行补上缺失字段。

## 失败关闭的配对规则

```python
for field in required_fields:
    if left[field] is None or right[field] is None:
        unknowns.append(field)
    elif left[field] != right[field]:
        mismatches.append(field)

if mismatches:
    return "not_comparable"
if unknowns:
    return "unknown"
return "comparable_definition"
```

`unknown` 不等于不可能比较，只表示当前证据不足；`not_comparable` 表示已有字段直接冲突。两者都不能进入价差收益计算。

## 价格状态是另一个维度

Lighter 的 RWA 机制以外部 oracle 为主要价格源；外部数据 stale 时，权重逐步转向订单簿 impact price 的内部 EMA，外部价格恢复时立即收敛回外部价格。[5]

trade.xyz 也区分外部和内部定价：外部市场开放时，外部公允价作为 oracle；外部输入不可用时，oracle 从最后外部价格开始，按订单簿 impact price 的连续时间 EMA 更新；外部输入恢复时，下一个 tick 回到外部价格。[6] `external price` 在外部市场关闭后保持在外部收盘价，而 oracle 仍可经内部机制变化。[7]

所以程序不能只看纽约时间推断价格状态。最低观察字段是：

```python
ObservationState(
    external_market_open=...,
    external_price_available=...,
    oracle_fresh=...,
    in_roll_transition=...,
)
```

只知道“现在是 17:30 ET”但不知道 oracle 是否 fresh，结果必须是 `unknown`，不能默认 external 或 internal。

## 可运行结果

```bash
PYTHONPATH=src python3 -m monte_arb.cli map-economics \
  --specifications tests/fixtures/day13/economic-specifications.json \
  --output research/runs/day13-economic-map.json
```

测试：

```bash
PYTHONPATH=src python3 -m unittest tests.test_day13_economic -v
```

测试覆盖：不同原油基准不能因单位相同而配对；缺少年份保持未知；时钟不能替代价格源证据；external、internal 和 roll transition 分开分类。

## 今天的实质验收

先看真实现象，不先背规则：

```text
时刻：17:40 ET
Lighter WTI：当天 17:30 的展期权重更新已经发生
trade.xyz xyz:CL：外部市场处于 17:00–18:00 ET 日维护窗口
两边盘口都仍有 bid/ask，价格只差 8 bps
```

你需要判断：这 8 bps 能否进入“同一价格状态下的可比较价差样本”？说明你还需要哪类证据。页面提供即时反馈；在聊天中用自己的话解释，才算今天的理解证据。

## Day13 边界

今天不计算价差收益、共同数量、盘口成交均价、费用或资金费。Day13 最多把候选标为：

- `comparable_definition`：静态经济定义已通过；
- `unknown`：关键字段或实时价格状态缺证据；
- `not_comparable`：已有定义冲突。

当前原油主线仍为 `unknown / 继续核验`，不是可交易候选。

## 一手资料

1. [Lighter RWA Market Specifications](https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications)
2. [Lighter Futures Contract Price Rolling Mechanism](https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism)
3. [trade.xyz Commodities](https://docs.trade.xyz/asset-directory/commodities)
4. [trade.xyz Specification Index](https://docs.trade.xyz/consolidated-resources/specification-index)
5. [Lighter RWA Pricing Mechanism](https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism)
6. [trade.xyz Oracle Price](https://docs.trade.xyz/perp-mechanics/oracle-price)
7. [trade.xyz External Price](https://docs.trade.xyz/perp-mechanics/external-price)
8. [Hyperliquid HIP-3](https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-3-builder-deployed-perpetuals)

## Sources

[1] https://apidocs.lighter.xyz/reference/orderbooks — Lighter Order Books API
[2] https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals — Hyperliquid Perpetuals API
[3] https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids — Hyperliquid Asset IDs
[4] https://api.hyperliquid.xyz/info — Hyperliquid Info API (live endpoint)
[5] https://mainnet.zklighter.elliot.ai/api/v1/orderBooks — Lighter Order Books API (live endpoint)
[6] https://apidocs.lighter.xyz/reference/orderbookorders — Lighter Order Book Orders API
[7] https://mainnet.zklighter.elliot.ai/api/v1/orderBookOrders — Lighter Order Book Orders API (live endpoint)
