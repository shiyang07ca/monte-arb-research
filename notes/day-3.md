# Day 3 / 2026-08-07 — Lighter WTI/BRENTOIL 合约模型

## 今日学习目标

理解 WTI 与 BRENTOIL 的经济对象、市场规格、最小基础数量、最小报价金额、数量/价格精度、乘数和保证金字段；能够把目标报价金额转换为合法的纸上基础数量。

## 实际完成

- 读取真实 `orderBookDetails` 快照：WTI `market_id=145`，BRENTOIL `market_id=159`；两者都是 `perp` 且 `active`，但代表不同原油品种。
- 确认 WTI：`min_base_amount=0.100`、`min_quote_amount=10`、`size_decimals=3`、`price_decimals=3`、`multiplier=1`。
- 确认 BRENTOIL：`min_base_amount=0.0800`、`min_quote_amount=10`、`size_decimals=4`、`price_decimals=2`、`multiplier=1`。
- 当前快照下，目标 `$10` 的纸上数量为 WTI `0.134`、BRENTOIL `0.1266`；目标 `$50` 的纸上数量约为 WTI `0.670`、BRENTOIL `0.6327`。
- 实际运行 `python3 -m unittest lab.test_audit_lighter_rwa -v`，4 个测试全部通过。

## 关键结论

相同基础数量不等于相同报价金额，也不等于相同经济风险；满足 `min_base_amount` 不代表满足 `min_quote_amount`；纸上数量可行性不等于历史深度、真实成交能力、账户权限或策略盈利。

## 证据

- `notes/rwa-contract-model.md`
- `lab/data/lighter_rwa_raw/145_orderBookDetails.json`
- `lab/data/lighter_rwa_raw/159_orderBookDetails.json`
- `lab/data/lighter_rwa_instrument_matrix.json`
- `lab/audit_lighter_rwa.py`
- `lab/test_audit_lighter_rwa.py`
- `lab/data/icl_20260808_current_checkin_correction.json`

## 研究结论

学习进度：Day 3 核心结论已掌握。研究仍为 `Blocked`：历史、价格源状态、展期、funding 账本、盘口/退出和权限资料不足。只读学习，没有认证、下单或私钥操作。

## 下一步

进入 Day 4，区分 `oracle_price`、`index_price`、`mark_price`、`candle_close`、`mid_price` 和 `trade_price`；缺少证据的字段保持 `unknown`。
