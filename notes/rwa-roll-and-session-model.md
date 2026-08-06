# WTI–BRENTOIL 展期与时间状态表

> 目的：把两个 RWA 永续的时间机制作为数据字段和研究分层条件，而不是把展期造成的结构变化误判为价差信号。

## 已确认规则

| 市场 | 官方展期窗口起点 | 展期规则 | 研究含义 |
|---|---|---|---|
| WTI | 美国东部时间 17:30 | 每个营业日将 20% 从当前月迁移到下一月 | 展期期间单独标记，不能默认价差平稳 |
| BRENTOIL | 美国东部时间 19:00 | 每个营业日将 20% 从当前月迁移到下一月 | 与 WTI 的时间错位可能产生结构性差异 |

来源：Lighter 官方《Futures Contract Price Rolling Mechanism》[44]。

## 数据字段

每条小时样本增加：

```text
timestamp_utc
wti_roll_window
brentoil_roll_window
wti_underlying_closed
brentoil_underlying_closed
展期阶段资料缺失
市场状态资料缺失
```

规则：

- 先把 UTC 时间转换为美国东部时间，再判断窗口；
- 不因展期窗口直接删除样本；
- 分别报告全样本、排除窗口和按窗口分层的统计；
- 如果官方资料不能支持某天的具体底层关闭/恢复状态，写 `unknown`；
- 不用插值把关闭或陈旧区间伪装成连续交易。

## 研究资料检查

在以下问题完成前，不估计最终 beta、阈值或持仓规模：

1. candle close、index、mark 是否代表同一价格过程；
2. 展期窗口是否能按历史日期重建；
3. 两腿底层关闭窗口是否有公开、稳定且可复现的字段；
4. oracle stale 或内部 EMA 状态是否可以观测；
5. 训练/验证/测试切分是否覆盖多个展期周期。

若第 2–4 项不能取得足够证据，就继续补资料，并把结果限定为教学用的描述性分析。

## 学习退出题

不看文档回答：

- WTI 和 BRENTOIL 的展期起点分别是什么时区和时间？
- 为什么不同展期窗口会制造结构断点？
- `roll_window` 应该是删除样本的理由，还是一个需要保留的研究记录？

通过标准：3 题全部答对，并能在一份样本上写出相应 UTC 与美国东部时间标记。

## Sources

[44] https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism — Lighter Docs: Futures Contract Price Rolling Mechanism
