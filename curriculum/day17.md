# Day17：双腿状态与挂单补对冲

> 状态：待学习
>
> 时间：60–90 分钟
>
> 当日成果：可重放的双腿订单状态和挂单/补对冲模型。

## 真实问题

计划在 A 买入 `0.010`、B 卖出 `0.010`，结果 A 只成交 `0.006`，B 已成交 `0.010`。组合实际是净空 `0.004`；若旧 A 订单仍可能成交，直接再补买还会制造反向敞口。

## 必须理解

- 提交、交易所确认、部分成交、全部成交、撤单和拒单是不同事件。
- 一腿挂单、另一腿主动补对冲的收益来自更低入场成本，但会引入排队、未成交和逆向选择。
- 没有真实排队与成交数据时，挂单方案不能用假定成交率挽救亏损候选。
- 未对冲状态只允许撤销、补对冲、减仓或停止，不允许开新组合。

## 助手实现

- 实现最小状态：空仓、开仓中、已对冲、未对冲、退出中、停止。
- 事件账本区分订单与成交；仓位只由成交事件改变。
- 为主动成交基线与挂单/补对冲分别计算结果。
- 记录信号、提交、确认、首次成交、全部成交、撤单时间，及预期/实际成交均价、剩余敞口和补对冲成本。
- 注入部分成交、拒单、撤单晚到、重复成交和行情过期场景。

## 用户任务

1. 在运行前计算给定事件序列的净敞口和允许动作。
2. 审查状态转换和成交入账两个函数。
3. 修改未对冲超时，预测补对冲次数和最差损失怎样变化。
4. 诊断一个注入故障：订单确认被错误地当成成交。

## 通过条件

- 任意时刻的仓位和现金都能由事件重新计算。
- 旧订单未终止前不会盲目补单。
- 主动成交与挂单方案分开报告，使用不同证据。
- 无成交概率证据时，挂单方案最多保持“继续采集”。
- 进入停止状态后不会产生新开仓动作。

## 保存证据

```text
research/runs/day17-execution-events.jsonl
research/runs/day17-failure-scenarios.json
research/decisions/day17-passive-execution.md
```

## 开源参考

- [NautilusTrader Execution](https://nautilustrader.io/docs/latest/concepts/execution/)
- [Lighter 官方 paper client](https://github.com/elliottech/lighter-python/tree/main/lighter/paper_client)
- [Hummingbot 跨交易所做市实现](https://github.com/hummingbot/hummingbot/blob/master/hummingbot/strategy/cross_exchange_market_making/cross_exchange_market_making.py)
