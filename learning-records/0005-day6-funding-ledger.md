# Day 6 学习记录 / Funding 现金流与纸上账本

> **已退役（2026-08-17）**：本记录中的 `index_price` 现金流公式与当前 Lighter Funding 文档不一致；当前规则使用 mark。相关程序、测试、快照和网页课程已删除。本记录只保留错误历史，不能作为资金费公式或现金账本依据。

## 学习目标

把 WTI/BRENTOIL 的 funding 观察放入两腿纸上现金流账本，区分 funding rate 的付款方向、API 原始字段和账户真实 PnL。

## 已完成

- 完成 Day 6 互动课程：`lessons/0005-day6-funding-ledger.html`。
- 使用真实本地 funding 快照识别 `rate`、`value`、`direction` 的边界。
- 掌握规则：正 funding 时多头通常付款，负 funding 时空头通常付款。
- 掌握纸上公式：

  ```text
  cash_flow = − position_sign × quantity × multiplier × index_price × funding_rate
  ```

- 能解释为什么 `WTI.value - BRENTOIL.value` 不是组合 funding PnL。
- 完成可运行账本：`lab/day6_funding_ledger.py`。
- Day 6 公式和未知边界测试通过：`lab/test_day6_funding_ledger.py`。

## 关键理解

`value` 是公共 API 观察字段，不等于已经核验的账户扣款/入账金额；`direction` 也不能代替账户仓位的 `position_sign`。真实 funding PnL 需要时间对齐的 index、实际仓位数量、乘数、结算 rate 和账户 funding ledger。

## 证据路径

- 参考卡：`reference/day6-funding-ledger.html`
- 纸上账本快照：`lab/data/day6_funding_ledger_snapshot.json`
- 模型笔记：`notes/funding-ledger-model.md`
- 官方规则：[Lighter Funding](https://docs.lighter.xyz/trading/funding)

## 未完成 / 未知

- 当前示例使用的 orderBookDetails index 没有与 funding timestamp 历史对齐。
- 没有账户真实 funding ledger、权限、成交和退出数据。
- 纸上结果只能标记 `paper_only`，不代表策略成立或真实收益。

## 下一步

Day 7：建立可重复的数据清洗和样本准入规则，不覆盖原始 JSON，不静默删除异常。
