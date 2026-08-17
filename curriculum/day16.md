# Day16：主动成交与完整现金结果

> 状态：待学习
>
> 时间：60–90 分钟
>
> 当日成果：两腿主动成交的共同数量、盘口成交均价和逐事件现金账本。

## 真实问题

开仓时买低卖高不等于已经获得利润。跨场所永续没有共同到期交割；退出需要反向完成另外两次成交，期间还有费率、资金费、滑点和未对冲风险。

## 必须理解

- 买入走 ask，卖出走 bid；退出方向相反。
- 共同数量同时受两边精度、最小名义、深度、保证金和资金限制约束。
- 开仓与退出一共四次成交，每次单独记录成交均价、数量和费用。
- 不可成交的中间价（`mid`）、标记价和指数价不能替代成交价格。
- 资金费必须使用正确结算价格、时间和账户方向；证据缺失时保持未知。

## 助手实现

- 实现纯函数：共同数量、订单簿走档、两种方向的开仓与退出。
- 使用带价格上限的可成交限价单模型，不假设无限深度。
- 只读查询实际账户费率；字段脱敏并保留获取时间。
- 建立成交、费用、资金费、剩余敞口和现金变化的事件账本。
- 加入错误方向、使用中间价、深度不足、费用未知和时间错位反例。

## 用户任务

1. 运行前判断两个方向分别使用哪边 bid/ask。
2. 审查共同数量和现金账本两个函数。
3. 修改费率或最大滑点，预测候选排序变化。
4. 诊断一个注入故障：退出仍然使用开仓方向的盘口。

## 通过条件

- 两个方向都能从冻结二级订单簿独立重算。
- 任何一腿深度不足都会保留未成交数量并阻止“可执行”结论。
- 四次成交和所有已知成本在现金账本中逐项出现。
- 账户费率未知时不使用公开默认值代替。
- 相同输入的结果、事件顺序和哈希一致。

## 保存证据

```text
research/runs/day16-active-execution.jsonl
research/runs/day16-cost-table.csv
research/decisions/day16-baseline.md
```

## 一手资料

- [Lighter 交易费用](https://docs.lighter.xyz/trading/trading-fees)
- [Lighter Funding](https://docs.lighter.xyz/trading/funding)
- [Hyperliquid 费用](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees)
- [NautilusTrader Execution](https://nautilustrader.io/docs/latest/concepts/execution/)
