# Day 3 价格语义学习材料：Oracle、Index、Mark 与成交价

## 学习问题

Lighter 的一个价格字段能不能直接用于价差、保证金和现金 PnL？答案是不能。不同字段承担不同作用，先记录语义，再选择统计或执行价格。

## 字段分工

| 字段 | 研究用途 | 不能直接做什么 |
|---|---|---|
| `oracle_price` | 外部价格源观察 | 不能直接视为你的成交价 |
| `index_price` | 指数/资金费和价格基准 | 不能替代目标数量走档 |
| `mark_price` | 保证金、清算和未实现 PnL 相关 | 不能代替可实现现金 PnL |
| `candle_close` | 固定时间窗口描述 | 不能假定等于 index/mark |
| `mid_price` | 盘口中心描述 | 不能代替买入 ask 或卖出 bid |
| `trade_price` | 逐笔成交观察 | 不能假定未来仍可成交 |

## RWA 特有状态

Lighter 官方 RWA 定价机制描述了外部 oracle 与内部订单簿 impact price EMA 的转换。oracle stale 时，价格过程可能逐步由内部 EMA 主导；外部价格恢复时又会收敛。[43]

研究表必须保留：

```text
source_timestamp
received_at
oracle_state
index_price
mark_price
candle_close
bid
ask
```

字段不存在时写 `unknown`；不能为了画出连续曲线而插值。

## 练习

假设某小时：

- `mid = 75.00`；
- `ask = 75.10`；
- `bid = 74.90`；
- `mark = 75.03`；
- `candle_close = 75.00`。

回答：

1. 立即买入用哪个价格作为保守估计？
2. 立即卖出用哪个价格作为保守估计？
3. 保证金距离用哪个价格语义核对？
4. 为什么不能用 `mark - mark` 证明两腿可以以该价格成交？

通过标准：四题答对三题，并能在官方 RWA 定价或 Fair Price 文档中定位依据。

## Sources

[43] https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism — Lighter Docs: RWA Pricing Mechanism
[75] https://docs.lighter.xyz/trading/fair-price-marking — Lighter Docs: Fair Price Marking
[76] https://docs.lighter.xyz/trading/pnl-and-total-account-value — Lighter Docs: PnL and Total Account Value
