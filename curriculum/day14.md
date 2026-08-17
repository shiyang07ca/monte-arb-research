# Day14：只读数据客户端与服务器采集

> 状态：待学习
>
> 时间：60–90 分钟学习；采集器随后持续运行 3–7 天
>
> 当日成果：锁定环境、两个只读数据客户端和服务器连续采集器。

## 真实问题

没有自行保存的历史二级订单簿（L2），就无法验证机会寿命、成交数量和延迟。网页图表、当前 REST 快照和 K 线不能重建双腿成交。

## 必须理解

- 版本、instrument 定义和事件类型都是输入的一部分。
- 实时推送协议（WebSocket）的初始快照、增量更新和全量快照不能混用。
- 原始事件与派生表分开保存；派生错误不能污染原始输入。
- 数据客户端和执行客户端必须在配置上明确分离。

## 助手实现

- 建立 Python 版本、`pyproject.toml` 和锁文件，固定当日核验的 NautilusTrader 稳定版本。
- 只构建 Lighter 与 Hyperliquid 数据客户端，先用 BTC/ETH 验证，再订阅 RWA 候选。
- 保存压缩 JSONL、instrument/status 快照、运行配置和内容哈希。
- 在东京服务器创建非特权运行用户、独立目录、磁盘上限、日志轮转和自动重启。
- 首次部署只采公开数据，不传账户密钥。

## 用户任务

1. 审查配置，指出哪一项能够证明没有创建执行客户端。
2. 修改订阅市场，预测输出中 instrument 和事件类型的变化。
3. 手动停止并重启一次采集器，检查是否生成新分段而非覆盖旧文件。
4. 诊断一个注入故障：代码收到更新事件却没有收到初始快照。

## 通过条件

- 环境可以从锁文件重新建立。
- 两个场所至少各收到 instrument、盘口和一种价格或资金费事件。
- 原始文件包含获取时间、源时间、接收时间、场所、完整 instrument 和原始引用。
- 重启、日志轮转和磁盘上限经过实际验证。
- 仓库、日志和容器镜像中没有账户密钥。

## 保存证据

```text
research/manifests/day14-environment.json
research/manifests/day14-collector.json
research/runs/day14-smoke-test.json
```

服务器原始数据不直接纳入 Git；仓库只保存采集清单、少量脱敏固定测试数据和哈希。

## 一手资料

- [NautilusTrader Lighter](https://nautilustrader.io/docs/latest/integrations/lighter/)
- [NautilusTrader Hyperliquid](https://nautilustrader.io/docs/latest/integrations/hyperliquid/)
- [Lighter WebSocket](https://apidocs.lighter.xyz/docs/websocket-reference)
- [Hyperliquid WebSocket](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket)
