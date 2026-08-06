# Funding 现金流模型与纸上账本

## 学习边界

Lighter funding 是持仓现金流，不是两个 API 字符串的价差。官方 Funding 文档解释 funding rate、premium、index 和方向；当前公开快照的 `value`、`rate`、`direction` 仍需与账户账本核对。[46]

## 纸上账本字段

```text
market_id
timestamp
position_sign          # long=+1, short=-1
base_quantity
multiplier
settlement_price
settled_rate
api_value
api_direction
cash_flow
cash_flow_status       # verified / paper_only / unknown
```

暂定纸上公式：

```text
cash_flow
= position_sign
× base_quantity
× multiplier
× settlement_price
× settled_rate
```

公式中的 `settlement_price`、`settled_rate`、方向和符号必须通过官方规则和受控账本核对；不能因为公式看起来合理就把状态写成 `verified`。

## 四个主动回忆场景

| 持仓 | funding 为正时的方向 | 当前状态 |
|---|---|---|
| WTI 多头 | 多头通常为支付方 | 需用规则/账本核对 |
| WTI 空头 | 空头通常为收款方 | 需用规则/账本核对 |
| BRENTOIL 多头 | 多头通常为支付方 | 需用规则/账本核对 |
| BRENTOIL 空头 | 空头通常为收款方 | 需用规则/账本核对 |

研究回放必须按每条腿、每个结算时点分别记账，再合并为组合现金流。

## 阻断规则

以下任一项未知，输出 `FUNDING_LEDGER_UNKNOWN`：

- `value` 的单位；
- `rate` 是否已结算或只是展示值；
- `direction` 与仓位符号的映射；
- 结算时间点；
- 账户账本中实际入账/扣款金额。

## 学习退出题

1. 为什么 `WTI.value - BRENTOIL.value` 不是组合 funding PnL？
2. 空头在正 funding 时的现金流方向是什么？
3. 哪个证据能把 `paper_only` 改成 `verified`？

通过标准：3 题全部回答，并能指出原始 funding JSON 的一条记录以及官方 Funding 文档。[46]

## Sources

[46] https://docs.lighter.xyz/trading/funding — Lighter Docs: Funding
[48] https://apidocs.lighter.xyz/reference/fundings — Lighter API: Fundings
