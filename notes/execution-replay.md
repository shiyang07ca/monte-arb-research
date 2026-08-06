# 目标数量执行回放模板

> Day 9 使用。当前只定义回放结构，不发送订单。

## 输入

- WTI 与 BRENTOIL 的目标名义：`$10/$20/$50/$100`；
- 每腿数量精度、最小基础数量和最小报价金额；
- 带源时间的 bid/ask 深度；
- 订单类型、账户费用和延迟假设；
- funding paper ledger；
- 开仓、持仓、平仓和失败恢复状态。

## 回放步骤

1. 根据目标名义和参考价格计算两腿数量；
2. 按数量精度向下/向上取整，并记录剩余净暴露；
3. 买入腿从 ask 走档，卖出腿从 bid 走档；
4. 反向平仓时使用相反方向的盘口；
5. 分别记录成交数量、VWAP、未成交数量、费用和冲击；
6. 加入延迟、盘口变化、部分成交和单腿失败场景；
7. 用 reduce-only/人工 kill switch 定义停止动作；
8. 计算净现金而不是中间价 PnL。

## 输出字段

```text
scenario_id
timestamp_utc
target_notional
wti_quantity
brentoil_quantity
residual_exposure
entry_vwap_wti
entry_vwap_brent
exit_vwap_wti
exit_vwap_brent
fees
funding_cash_flow
impact_cost
failure_reserve
liquidation_reserve
net_cash_pnl
unknowns
decision
```

## 拒绝规则

- 只有 top-of-book 快照：不能证明连续容量；
- 没有退出方向盘口：`DEPTH_AND_EXIT_UNKNOWN`；
- 未知费用或 funding：`Blocked`；
- 单腿失败后没有处理：不能进入 paper `Go`；
- 理论价差被双腿开平仓和压力成本吞没：`No-Go`。

## 当前状态

尚未完成实际目标数量回放，继续保持 `DEPTH_AND_EXIT_UNKNOWN` 和 `Blocked`。
