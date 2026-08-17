# Day19：NautilusTrader 确定性重放

> 状态：待学习
>
> 时间：60–90 分钟
>
> 当日成果：同一研究逻辑在 NautilusTrader 历史重放中运行，并得到可重复结果。

## 真实问题

研究脚本和最终运行程序各写一套成本或状态规则，会产生两个不同策略。重放好看但实时运行调用另一套逻辑，结果没有可比性。

## 必须理解

- 市场身份、成本、候选判断和执行状态是纯逻辑；NautilusTrader 只负责事件、时钟、数据和运行环境。
- 策略类（`Strategy`）不得读取未来事件或在运行中重新估计最终检验参数。
- 配置、数据、代码版本和结果哈希共同确定一次实验。
- 确定性只证明同一输入重复，不证明市场未来会重复。

## 助手实现

- 将 Day14–15 数据写入 `ParquetDataCatalog`。
- 用 `BacktestNode` 驱动最小策略类，调用 Day16–18 的同一核心函数。
- 保存完整配置、输入清单、事件摘要、仓位、现金和决定。
- 重放两次并自动比较结果哈希。
- 加入未来数据泄漏和错误 instrument 映射测试。

## 用户任务

1. 运行前预测提高费率或延迟后结果的方向。
2. 审查策略类与纯研究逻辑的分界。
3. 亲自修改一个费率或最长持有时间参数，再验证预测。
4. 诊断一个注入故障：策略类使用下一条事件价格决定当前订单。

## 通过条件

- 相同输入两次得到相同事件、仓位、现金、决定和哈希。
- 策略类内没有第二套成本计算或市场映射。
- 时间泄漏测试先失败、修复后通过。
- 参数改变后的方向与用户运行前预测一致。
- 数据不足仍输出继续采集，不降低规则。

## 保存证据

```text
research/manifests/day19-backtest.json
research/runs/day19-replay-a.json
research/runs/day19-replay-b.json
research/decisions/day19-replay.md
```

## 一手资料

- [NautilusTrader Getting Started](https://nautilustrader.io/docs/latest/getting_started/)
- [NautilusTrader Backtesting](https://nautilustrader.io/docs/latest/concepts/backtesting/)
- [NautilusTrader Data](https://nautilustrader.io/docs/latest/concepts/data/)
