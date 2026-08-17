# Day15：时间、顺序、缺口与过期

> 状态：待学习
>
> 时间：60–90 分钟
>
> 当日成果：从原始事件重建有效盘口，并只生成可比较时间窗口。

## 真实问题

两边表面有 40 个基点价差，但源时间相差 650 毫秒，而价差中位寿命只有 250 毫秒。事后取最近值或插值不会恢复同时可执行的报价。

## 必须理解

- 源时间、接收时间和本机处理时间回答不同问题。
- 时钟偏差、网络延迟、事件缺口和盘口年龄必须分别记录。
- 只有通过初始快照和连续更新构建的盘口才有效。
- 最大允许时间差必须在看策略结果前固定，并与机会寿命比较。

## 助手实现

- 为两个场所实现各自的盘口重建规则。
- 记录序号、快照标志、缺口、重复、乱序和最后有效时间。
- 全量验证新 market/status 快照后再替换上一份有效状态。
- 生成可比较窗口，并为被排除的记录保存明确原因。
- 注入断连、乱序、坏数值、缺少快照和时钟偏差测试。

## 用户任务

1. 预测 650 毫秒错位样本的决定。
2. 审查盘口有效性和比较窗口函数。
3. 修改最大盘口年龄，先预测样本数量怎样变化，再运行验证。
4. 从日志定位一个“重连后增量接在旧快照上”的故障。

## 通过条件

- 不使用插值、前值填充或事后平移制造同步盘口。
- 断连前后的事件不会组成一个候选。
- 过期阈值变化的影响方向与用户预测一致。
- 相同事件序列两次重建得到相同盘口和排除原因。

## 保存证据

```text
research/runs/day15-book-health.json
research/runs/day15-comparable-windows.parquet
research/decisions/day15-data-admission.md
```

## 一手资料

- [Lighter WebSocket](https://apidocs.lighter.xyz/docs/websocket-reference)
- [Hyperliquid WebSocket](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket)
- [NautilusTrader 数据](https://nautilustrader.io/docs/latest/concepts/data/)
