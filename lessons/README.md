# Lighter WTI–BRENTOIL 研究教学工作区

本目录按 `teach` skill 的结构保存课程材料：

- `lessons/0001-day2-audit-lighter-rwa.html`：Day 2 HTML lesson；
- `lessons/0002-day3-rwa-contract-model.html`：Day 3 互动 HTML lesson；
- `lessons/0003-day4-price-semantics.html`：Day 4 互动 HTML lesson；
- `lessons/0004-day5-roll-session.html`：Day 5 展期与市场状态互动 HTML lesson；
- `lessons/0005-day6-funding-ledger.html`：Day 6 funding 现金流与纸上账本互动 HTML lesson；
- `lessons/0006-day7-data-cleaning.html`：Day 7 数据清洗与可复现规则互动 HTML lesson；
- `lessons/0007-day8-venue-schema.html`：Day 8 跨场所盘口与 funding 统一 schema 互动 HTML lesson；
- `lessons/0008-day9-parameter-recheck.html`：Day 9 参数重新核验互动 HTML lesson；
- `reference/day2-lighter-rwa-audit-cheatsheet.html`：Day 2 打印版 reference；
- `reference/day3-rwa-contract-model.html`：Day 3 打印版 reference；
- `reference/day4-price-semantics.html`：Day 4 打印版 reference；
- `reference/day5-roll-session.html`：Day 5 展期与市场状态打印版 reference；
- `reference/day6-funding-ledger.html`：Day 6 funding 现金流与纸上账本打印版 reference；
- `assets/course.css`：课程共用样式；
- `assets/day3-contract-model.js`：Day 3 纸上数量计算器和验收组件；
- `assets/day4-price-semantics.js`：Day 4 价格语义、EMA、PnL 和验收组件；
- `assets/day5-roll-session.js`：Day 5 时区、展期阶段和迁移验收组件。
- `assets/day6-funding-ledger.js`：Day 6 funding 方向、纸上现金流和迁移验收组件。
- `assets/day7-data-cleaning.js`：Day 7 数据质量、准入分类和迁移验收组件。
- `assets/day8-venue-schema.js`：Day 8 跨场所盘口对照和迁移验收组件。
- `assets/day9-parameter-recheck.js`：Day 9 参数 diff 对照、字段分类和迁移验收组件。
- `lab/day5_roll_session.py`：Day 5 时区转换、展期阶段和关闭窗口规则；
- `lab/test_day5_roll_session.py`：Day 5 规则测试；
- `lab/data/day5_roll_session_snapshot.json`：Day 5 官方规则与派生时区快照。
- `lab/day6_funding_ledger.py`：Day 6 funding 公式、方向判断和纸上账本生成器。
- `lab/test_day6_funding_ledger.py`：Day 6 funding 公式与未知边界测试。
- `lab/data/day6_funding_ledger_snapshot.json`：Day 6 脱敏纸上账本快照。
- `lab/day7_data_cleaning.py`：Day 7 可重复清洗、质量标记和样本准入脚本。
- `lab/test_day7_data_cleaning.py`：Day 7 清洗边界与输出模式测试。
- `lab/data/lighter_rwa_clean_1h.csv`：Day 7 长表清洗输出。
- `lab/data/day7_cleaning_summary.json`：Day 7 脱敏清洗汇总。
- `lab/venue_schema.py`：Day 8 跨场所统一 schema、字段映射和归一化脚本。
- `lab/test_venue_schema.py`：Day 8 跨场所字段语义与输出模式测试。
- `lab/data/day8_venue_snapshots.csv`：Day 8 统一长表（333 行）。
- `lab/data/day8_venue_field_mapping.json`：Day 8 字段映射与 not_equivalent 清单。
- `lab/data/day8_venue_schema_summary.json`：Day 8 schema 汇总与 unknowns。
- `notes/venue-schema.md`：Day 8 证据笔记。
- `lab/day9_parameter_recheck.py`：Day 9 参数重新抓取与合约/状态字段 diff 脚本。
- `lab/test_day9_parameter_recheck.py`：Day 9 参数 diff 分类与快照完整性测试。
- `lab/data/day9_raw/`：Day 9 原始响应 + manifest（HTTP 状态、时间、延迟、SHA-256）。
- `lab/data/day9_parameter_diff.json`：Day 9 新旧参数逐字段差异。
- `notes/day9-parameter-recheck.md`：Day 9 证据笔记。

练习和课程材料绑定以下真实文件：

- `lab/data/lighter_rwa_raw/`；
- `lab/data/lighter_rwa_capture_manifest.json`；
- `lab/data/lighter_rwa_data_audit.json`；
- `lab/data/lighter_rwa_aligned_1h.jsonl`；
- `lab/audit_lighter_rwa.py`。

运行：

```bash
python3 lab/audit_lighter_rwa.py
python3 -m unittest lab.test_audit_lighter_rwa -v
```

本教学阶段只读、不认证、不发单、不连接私钥。当前资料仍不足以判断策略是否成立。
