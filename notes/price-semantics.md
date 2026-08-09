# Day 4｜价格语义学习材料：Oracle、Index、Mark、EMA 与可执行价格

## 学习问题

Lighter 的一个价格字段能不能直接用于价差、保证金和现金 PnL？不能。不同字段承担不同作用，先记录语义，再选择统计或执行价格。

## 字段分工

| 字段 | 研究用途 | 不能直接做什么 |
|---|---|---|
| `oracle_price` | 外部价格源观察/输入 | 不能直接视为成交价 |
| `index_price` | 指数/资金费和价格基准 | 不能替代目标数量走档 |
| `mark_price` | 保证金、清算和未实现 PnL 相关 | 不能代替可实现现金 PnL |
| `candle_close` | 固定时间窗口描述 | 不能假定等于 index/mark 或成交价 |
| `mid_price` | 盘口中心描述 | 不能代替买入 ask 或卖出 bid |
| `trade_price` | 已发生的逐笔成交观察 | 不能假定未来仍可成交 |
| `bid / ask` | 当前盘口最优买价/卖价 | 不能代表目标数量全部成交的平均价 |

## 研究问题到价格

- 立即买入：使用 ask 方向，按目标数量走 ask 深度。
- 立即卖出：使用 bid 方向，按目标数量走 bid 深度。
- 未实现 PnL/清算距离：使用 mark_price 语义。
- 外部基准/价格输入：使用 oracle/index，但必须保留状态与新鲜度。
- 历史小时收益：使用 candle_close，并保留窗口和时间戳。

## RWA stale 与 EMA

官方 RWA 定价机制：外部 oracle 是主要来源；oracle stale 时，其权重指数衰减，内部订单簿 impact price 权重上升；内部价格再通过时间加权 EMA 平滑。外部价格恢复时，内部价格即时向外部价格收敛。

这里有**两组不同的时间常数**，不要混成一个：

1. **来源权重切换**：当前官方页面列出的 `τ_mark` 和 `τ_index` 都是 1 分钟。它控制 oracle stale 后，系统多快把“价格来源的权重”从外部 oracle 转向内部价格。
2. **内部价格 EMA 平滑**：index 的内部 EMA 使用 `τ = 30` 分钟，mark 的内部 EMA 使用 `τ = 2` 分钟。它控制内部 impact price 进入计算后，数值对新订单簿信息反应多快。

```text
外部 oracle ──正常──→ index / mark 定价
       │
       └─ stale：oracle 权重下降，内部价格权重上升
                         ↓
              订单簿 impact price
                         ↓
                    时间加权 EMA
                    ├─ index：τ = 30 min
                    └─ mark ：τ = 2 min

w_oracle(t) = w_oracle(t−1) × exp(−Δt / τ_source)
w_internal(t) = 1 − w_oracle(t)

EMA_t = α × impact_t + (1 − α) × EMA_(t−1)
α = 1 − exp(−Δt / τ_ema)
```

`τ_source` 和 `τ_ema` 回答不同问题：前者是“信谁”，后者是“内部价格反应多快”。不要把它们理解成成交延迟或市场关闭时间。

## 真实快照与 unknown

当前 raw `orderBookDetails` 快照：

| 市场 | mark | index | last trade | mark − index |
|---|---:|---:|---:|---:|
| WTI（145） | 74.692 | 74.670 | 74.677 | 0.022 |
| BRENTOIL（159） | 79.03 | 79.04 | 79.01 | -0.01 |

当前快照没有直接提供：

```text
oracle_price
mid_price
bid
ask
oracle_state
source_timestamp
```

这些字段应写 `unknown`，不能使用 mark、last trade 或插值填补。

## PnL 反例

```text
entry = 75.00, quantity = 1
mark = 75.03, bid = 74.90, ask = 75.10

多头 mark 未实现 PnL = (75.03 − 75.00) × 1 = +$0.03
多头立即卖出纸上 PnL = (74.90 − 75.00) × 1 = −$0.10
```

二者不同并不矛盾：前者是 mark 估值，后者是按 bid 平仓的纸上可实现结果；两者都还没有计入手续费、funding、深度、部分成交和延迟。

## Sources

- [Lighter RWA Pricing Mechanism](https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism)
- [Lighter Fair Price Marking](https://docs.lighter.xyz/trading/fair-price-marking)
- [Lighter PnL and Total Account Value](https://docs.lighter.xyz/trading/pnl-and-total-account-value)
- [Lighter RWA Market Specifications](https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications)
- 本地证据：`lab/data/day4_price_semantics_snapshot.json`
