# 数据质量报告模板

> Day 7 使用。当前文件先固定清洗规则和待填证据，不把尚未运行的结果写成已完成。

## 原始证据

- 原始目录：`lab/data/lighter_rwa_raw/`
- 采集记录：`lab/data/lighter_rwa_capture_manifest.json`
- 现有审计：`lab/data/lighter_rwa_data_audit.json`
- 对齐序列：`lab/data/lighter_rwa_aligned_1h.jsonl`

## 清洗规则

1. 时间统一解析为 UTC；原始 timestamp 不覆盖；
2. 相同市场、相同 timestamp 的重复记录全部保留在审计中；统计输入必须有明确去重规则；
3. 缺失小时不插值，增加 `missing_interval` 状态；
4. 非正价格、非法数量和不可解析字段不进入统计，原始记录保留并写 `invalid_value`；
5. 展期、关闭、oracle 状态不因异常直接删除，写入状态字段；
6. 所有删除/排除都必须写原因码；
7. 训练、验证、测试按时间顺序切分，不用未来数据确定过去参数；
8. 每条统计样本保留原始文件名、原始 timestamp 和清洗版本。

## 质量检查表

| 检查 | 状态 | 证据/说明 |
|---|---|---|
| WTI 1h 重复 timestamp | 待检查 | 运行清洗脚本后填写 |
| BRENTOIL 1h 重复 timestamp | 待检查 | 运行清洗脚本后填写 |
| WTI daily 重复 timestamp | `checked` | 现有 audit 为 0 |
| BRENTOIL daily 重复 timestamp | `checked` | 现有 audit 为 0 |
| 缺失小时 | 待检查 | 不能从当前共同行数推断 |
| 非正价格 | 待检查 | 逐字段检查 |
| 展期状态 | 待检查 | 需要时间状态字段 |
| oracle freshness | `unknown` | 当前原始 candle 不足以证明 |
| funding 结算账本 | 资料缺失 | 尚未完成 `FUNDING_LEDGER_UNKNOWN` 核对 |

## 统计准入

只有当样本有明确时间、价格语义和清洗状态时，才能进入描述性统计。历史不足、价格源未知或资金费无法入账时，统计结果只能作为教学材料，不能声称策略成立。

## 预期产出

- `lab/data/lighter_rwa_clean_1h.csv`
- 本报告的已填写版本
- 运行命令和审计输出
