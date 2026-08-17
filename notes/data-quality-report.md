# Day 7 数据质量报告 / 可复现清洗结果

> 清洗版本：`day7-v1`；生成方式：`derived-from-source-snapshot`。原始 JSON 只读，未被覆盖。

## 唯一问题

哪些样本可以进入描述性统计，哪些必须保留为异常证据？答案不是删除异常，而是给每一行可复查的状态。

## 输入与覆盖

| 市场 | candles 原始行 | fundings 原始行 | candle 时间范围 | funding 时间范围 | funding-only 行 | 组合可用行 |
|---|---:|---:|---|---|---:|---:|
| WTI | 500 | 750 | 2026-07-16T05:00:00+00:00 → 2026-08-06T00:00:00+00:00 | 2026-07-05T19:00:00+00:00 → 2026-08-06T00:00:00+00:00 | 250 | 500 |
| BRENTOIL | 500 | 750 | 2026-07-16T05:00:00+00:00 → 2026-08-06T00:00:00+00:00 | 2026-07-05T19:00:00+00:00 → 2026-08-06T00:00:00+00:00 | 250 | 500 |

API candles 文档说明单次最多返回 500 根 candle，且零值字段可能省略；因此当前 500 行不是完整历史，缺字段也不能自动补零。

## 清洗规则

1. candle 的毫秒 timestamp、funding 的秒 timestamp 统一转换为 UTC，同时保留 `raw_*_timestamp`。
2. 重复 timestamp 不静默覆盖：原始 JSON 保留，输出写入重复计数，并排除出统计直到明确复核。
3. 缺失小时只标记 `missing_interval`，不插值。
4. 非数字、非有限值和非正价格保留原行并标记 `invalid_numeric` / `non_positive_price`。
5. 相邻 close 的绝对跳幅超过 5% 只标记 `close_jump_gt_5pct`，不自动删除。
6. 按唯一 UTC timestamp 做 60%/20%/20% 的 train/validation/test 时间切分，禁止随机打乱。

## 输出计数

- 长表行数：`1500`；唯一 timestamp：`750`。
- candle + funding：`1000`；funding-only：`500`；candle-only：`0`。
- price 可用：`1000`；funding 可用：`1500`；两者同时可用：`1000`。
- 带跳点标记但仍保留的组合行：`1`；完全不准入行：`0`。

## 市场级异常证据

- **WTI**：重复 candle `0`，重复 funding `0`；candle 缺口 `0`，funding 缺口 `0`；>5% close 跳点 `1`。
  - 跳点时间：`2026-08-04T11:00:00+00:00`。
- **BRENTOIL**：重复 candle `0`，重复 funding `0`；candle 缺口 `0`，funding 缺口 `0`；>5% close 跳点 `0`。

## 时间切分

| split | 唯一 timestamp 数 | 范围 |
|---|---:|---|
| train | 450 | 2026-07-05T19:00:00+00:00 → 2026-07-24T12:00:00+00:00 |
| validation | 150 | 2026-07-24T13:00:00+00:00 → 2026-07-30T18:00:00+00:00 |
| test | 150 | 2026-07-30T19:00:00+00:00 → 2026-08-06T00:00:00+00:00 |

## 展期覆盖与未知

- 当前 candle 覆盖：`2026-07-16T05:00:00+00:00` → `2026-08-06T00:00:00+00:00`。
- 官方示例展期窗口从 2026-08-07 开始；当前 candle 只到 2026-08-06，因此本数据集是 `pre_roll_only`，不能用来证明展期期间的反应。
- candle timestamp 是区间开始还是结束仍 unknown。
- funding `value` / `direction` 仍未与账户 funding ledger 核验；清洗完成不等于 funding PnL 已验证。
- 当前输出适合教学和可复现审计，不足以证明 WTI–BRENTOIL 策略成立或可交易。

## 证据路径

- 原始输入：`lab/data/lighter_rwa_raw/`
- 清洗脚本：`lab/day7_data_cleaning.py`
- 清洗输出：`lab/data/lighter_rwa_clean_1h.csv`
- 脱敏汇总：`lab/data/day7_cleaning_summary.json`
- 测试：`lab/test_day7_data_cleaning.py`

## Primary source

- [Lighter API candles](https://apidocs.lighter.xyz/reference/candles)
- [Lighter API fundings](https://apidocs.lighter.xyz/reference/fundings)
