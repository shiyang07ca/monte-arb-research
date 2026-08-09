# Day 2 教学工作区

本目录按 `teach` skill 的结构保存课程材料：

- `lessons/0001-day2-audit-lighter-rwa.html`：Day 2 HTML lesson；
- `lessons/0002-day3-rwa-contract-model.html`：Day 3 互动 HTML lesson；
- `lessons/0003-day4-price-semantics.html`：Day 4 互动 HTML lesson；
- `reference/day2-lighter-rwa-audit-cheatsheet.html`：Day 2 打印版 reference；
- `reference/day3-rwa-contract-model.html`：Day 3 打印版 reference；
- `reference/day4-price-semantics.html`：Day 4 打印版 reference；
- `assets/course.css`：课程共用样式；
- `assets/day3-contract-model.js`：Day 3 纸上数量计算器和验收组件；
- `assets/day4-price-semantics.js`：Day 4 价格语义、EMA、PnL 和验收组件。

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
