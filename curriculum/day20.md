# Day20：实时模拟与故障恢复

> 状态：待学习
>
> 时间：60–90 分钟监督运行；采集器继续后台运行
>
> 当日成果：真实行情、本地模拟成交、运行指标和四类故障复盘。

## 真实问题

历史重放能够完成，不代表实时系统能处理断连、过期行情、坏快照和进程重启。无法解释本地仓位或现金差异时，系统必须停止，而不是静默继续。

## 必须理解

- 实时模拟使用真实行情，但所有订单只进入本地执行模型。
- 当前市场状态、盘口年龄、未对冲名义和净现金组成必须随时可见。
- 重启后状态从持久事件重建，并与模拟账户摘要比较。
- 自动恢复只用于结果明确的情况；歧义状态进入停止。

## 助手实现

- 使用 NautilusTrader 实时数据客户端运行 Day19 的同一策略类。
- 所有订单路由到本地模拟执行，不注册场所执行客户端。
- 命令行状态显示数据延迟、盘口年龄、候选状态、模拟订单、仓位、剩余敞口和现金组成。
- 注入断网、过期行情、坏快照和进程重启。
- 使用账户密钥的独立只读进程核验费率、余额、持仓和资金费记录；输出脱敏。

## 用户任务

1. 监督运行前写出四类故障各自预期的状态。
2. 审查停止条件和状态恢复函数。
3. 修改一个过期或停止阈值，预测告警和模拟订单数量变化。
4. 根据日志定位一个重启后重复处理事件的故障。

## 通过条件

- 连续监督运行至少 60 分钟。
- 四类故障均有可复现输入、预期状态和实际结果。
- 无法解释的仓位或现金差异进入停止状态。
- 停止后不产生新模拟开仓。
- 代码、配置和日志中没有密钥，也没有真实订单路径。

## 保存证据

```text
research/manifests/day20-shadow.json
research/runs/day20-metrics.jsonl
research/runs/day20-faults.md
research/decisions/day20-operational-status.md
```

## 一手资料

- [NautilusTrader Live Trading](https://nautilustrader.io/docs/latest/concepts/live/)
- [NautilusTrader Lighter](https://nautilustrader.io/docs/latest/integrations/lighter/)
- [NautilusTrader Hyperliquid](https://nautilustrader.io/docs/latest/integrations/hyperliquid/)
