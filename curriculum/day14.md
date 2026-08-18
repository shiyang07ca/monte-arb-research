# Day14：同一采集轮次不等于同一市场时刻

> 状态：学习中
>
> 学习时间：30–45 分钟；助手实现与核验不计入
>
> 互动入口：`lessons/0010-day14-synchronized-quotes.html`
>
> 当日成果：四个原油市场的只读并发快照、三种时间含义和失败关闭的样本准入报告。

## 今天真正要回答的问题

Day13 已经把判断拆成两层：`economic_object` 与 `quote_sample`。Day14 不再搭建泛化服务器工程，而是直接取得四个原油市场的一轮真实盘口，并回答：

> 四个请求在同一个程序里并发完成，是否足以证明这些价格代表同一市场时刻？

答案不是自动的 `yes`。必须区分请求开始时间、本机接收时间和交易所来源时间；任何缺失都要显式保留。

## 当前真实采集

2026-08-18 的只读并发采集使用：

- Lighter `GET /orderBookOrders?market_id=...`；官方定义为取得订单簿订单。[6]
- Hyperliquid `POST /info`，请求 `{"type":"l2Book","coin":"..."}`；其返回包含 `coin`、毫秒级 `time` 和双边 `levels`。[2]

本轮结果：

```text
capture_span_ms = 1124.0355
observations = 4
request_errors = 0

Lighter WTI       bid=84.056 ask=84.070 source_time=None
Lighter BRENTOIL  bid=89.20  ask=89.22  source_time=None
xyz:CL            bid=84.075 ask=84.076 source_time=1787017114726
xyz:BRENTOIL      bid=89.236 ask=89.239 source_time=1787017114726
```

这些价格只证明四份双边盘口被本机收到。它们不证明合约权重相同，不证明 external/internal oracle 状态相同，也不证明 Lighter 与 Hyperliquid 的交易所事件时间可以直接相减。

## 三种时间不能混用

```text
request_started_ns
    本机开始发请求的单调时钟；用于测请求窗口。

response_received_ns
    本机完整收到响应的单调时钟；可比较同一进程内的接收先后与偏差。

source_time_ms
    响应中由交易所提供的事件/快照时间；只有响应明确提供时才存在。
```

当前 Hyperliquid `l2Book.time` 提供来源时间。Lighter `orderBookOrders` 的当前响应只有 `code`、`bids`、`asks` 与数量字段，没有盘口快照来源时间。因此：

```text
Hyperliquid source_time - Lighter source_time
```

无法计算；不能拿 Lighter 的本机接收时间冒充交易所来源时间。

`capture_span_ms` 从最早请求开始算到最晚响应完成，描述的是**采集轮次宽度**，不是“市场同时性证明”。

## 原始观察与研究决定分开

一条原始观察保留：

```python
QuoteObservation(
    identity,
    request_started_ns,
    response_received_ns,
    source_time_ms,
    best_bid,
    best_ask,
    bid_size,
    ask_size,
    raw_sha256,
)
```

派生准入决定另行计算：

```text
经济映射不是 same                  → exclude
合约权重 unknown / mismatch          → exclude
oracle_state unknown / mismatch      → exclude
本机接收偏差超过上限                  → exclude
盘口无效、锁定、交叉、空或单边         → exclude
```

原始盘口不能因为当前 `exclude` 而删除。等后续取得更可靠的规则状态，仍可重新计算派生决定。

## 本轮为何必须排除

```text
WTI ↔ xyz:CL
status = exclude
reasons =
  ECONOMIC_MAPPING_UNKNOWN
  CONTRACT_WEIGHT_UNKNOWN
  ORACLE_STATE_UNKNOWN
  SOURCE_TIME_NOT_COMPARABLE

BRENTOIL ↔ xyz:BRENTOIL
status = exclude
reasons = 同上
```

盘口价很接近不是准入条件。本轮即使表面出现跨场买卖价关系，也不计算利润，因为 Day13 的合约权重和 oracle 状态仍未知。

## 可运行代码

```bash
PYTHONPATH=src python3 -m monte_arb.day14_collector \
  --output research/runs/day14-smoke-test.json \
  --raw-output research/raw/day14/attempts.jsonl.gz

PYTHONPATH=src python3 -m unittest tests.test_day14_synchronized_quotes -v
```

关键路径：

```text
src/monte_arb/synchronized_quotes.py
src/monte_arb/day14_collector.py
tests/test_day14_synchronized_quotes.py
research/manifests/day14-environment.json
research/manifests/day14-collector.json
research/runs/day14-smoke-test.json
```

`research/raw/day14/attempts.jsonl.gz` 是本机追加式原始采集，不进入 Git。仓库保存派生报告、配置和测试；长期采集仍需独立目录、轮转、磁盘上限与重启验证，今天不声称已经完成服务器部署。

## 只读边界

报告明确保存：

```json
{
  "read_only": true,
  "execution_client_present": false
}
```

采集器只调用公共数据端点，不载入账户凭据，也没有订单创建、签名、撤单或持仓接口。今天不引入 NautilusTrader：先把真实接口的身份与时间语义证明清楚，再决定何时需要事件引擎，避免用框架掩盖缺失的来源时间。

## 综合验收

页面会给出本轮四条真实观察。你只需一次完成以下任务，不做逐项选择题：

1. 决定这轮数据能否用于跨场价差样本；
2. 指出最关键的证据缺口；
3. 说明保留原始观察而不直接丢弃的理由；
4. 如果下一轮把四个请求的本机接收偏差降至 20ms，但合约权重和 oracle 状态仍未知，说明结论是否改变。

## Day14 边界与下一步

今天完成的是可回放的本地 REST 冒烟采集，不是 3–7 天服务器采集。Day15 才继续研究时间、顺序、缺口、过期和连续采集；只有样本准入证据完整后，才进入可成交价差与纸上回放。

## 一手资料

1. [Lighter `orderBookOrders`](https://apidocs.lighter.xyz/reference/orderbookorders)
2. [Hyperliquid Perpetuals info endpoints](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals)
3. [Hyperliquid WebSocket](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket)
4. [Lighter WebSocket Reference](https://apidocs.lighter.xyz/docs/websocket-reference)

## Sources

[2] https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals — Hyperliquid Perpetuals API
[6] https://apidocs.lighter.xyz/reference/orderbookorders — Lighter Order Book Orders API
