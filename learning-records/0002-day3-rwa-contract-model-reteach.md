# Day 3 重学记录 / 2026-08-08

## 学习主题

建立 Lighter WTI（`market_id=145`）与 BRENTOIL（`market_id=159`）商品 RWA 永续的合约模型，并通过电脑端互动课程完成纸上数量与保证金边界练习。

## 实际完成

- 重新区分 WTI 与 BRENTOIL：两者都是 `perp`，但分别代表 WTI 和 Brent 原油，不是同一个经济对象。
- 重新确认关键市场字段：WTI `min_base_amount=0.100`、`size_decimals=3`、`price_decimals=3`；BRENTOIL `min_base_amount=0.0800`、`size_decimals=4`、`price_decimals=2`；两者 `min_quote_amount=10`、`multiplier=1`。
- 理解合法纸上数量必须同时满足：基础数量下限、最小报价金额和数量精度。
- 通过浏览器加载并运行互动 HTML lesson：`lessons/0002-day3-rwa-contract-model.html`。
- 实际操作计算器完成 WTI `$50` 场景：理论数量约 `0.66941573`，向上取整为 `0.670`，纸上金额 `$50.04364`。
- 实际操作计算器完成 BRENTOIL `$100` 场景：理论数量约 `1.26534228`，向上取整为 `1.2654`，纸上金额 `$100.004562`。
- 互动验收得分 `4/4`：确认 `$50` 两腿数量、相同数量不等于相同名义、公共快照保证金字段不能证明账户实际保证金。
- 在仓库根目录实际运行 `python3 -m unittest lab.test_audit_lighter_rwa -v`，4 个测试全部通过。

## 关键理解

- 相同基础数量不等于相同报价金额，也不等于经济上的最佳对冲；例如数量 `0.650` 时，WTI 纸上金额约 `$48.5498`，BRENTOIL 约 `$51.3695`。
- `min_base_amount` 不是唯一约束；WTI `0.100 × 74.692 = $7.4692`，数量虽合格，但低于 `$10` 最小报价金额。
- `default_initial_margin_fraction` 的公共快照值（WTI `500`、BRENTOIL `666`）只能支持“默认字段不同”的观察，不能证明账户实际保证金、组合保证金、清算路径或权限。
- 本课只验证纸上可行性，不验证盘口成交、历史回放、退出能力、funding 现金流或策略盈利。

## 证据位置

- `lessons/0002-day3-rwa-contract-model.html`
- `reference/day3-rwa-contract-model.html`
- `assets/day3-contract-model.js`
- `notes/rwa-contract-model.md`
- `lab/data/lighter_rwa_raw/145_orderBookDetails.json`
- `lab/data/lighter_rwa_raw/159_orderBookDetails.json`
- `lab/data/lighter_rwa_instrument_matrix.json`
- `lab/test_audit_lighter_rwa.py`
- `lab/data/icl_20260808_current_checkin_correction.json`

## 尚未完成

- 未证明 WTI–BRENTOIL 的经济对冲比率；等名义只是纸上起点。
- 未验证历史价格源、展期、funding 账本、目标数量盘口退出、账户权限和清算路径。
- 未连接账户、私钥或发送真实订单。

## 下一步

进入 Day 4：建立价格语义模型，区分 `oracle_price`、`index_price`、`mark_price`、`candle_close`、`mid_price` 与 `trade_price`，并明确每种价格适合回答什么问题。
