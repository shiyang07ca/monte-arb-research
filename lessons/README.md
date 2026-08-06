# Day 2 教学工作区

本目录按 `teach` skill 的结构保存课程材料：

- `lessons/0001-day2-audit-lighter-rwa.html`：短 HTML lesson；
- `lessons/day2-real-data-exercise.md`：真实仓库数据练习；
- `reference/day2-lighter-rwa-audit-cheatsheet.html`：打印友好的 reference cheat sheet；
- `assets/course.css`：课程共用样式。

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
