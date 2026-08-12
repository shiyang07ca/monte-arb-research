# Day 9 学习记录 — 参数重新核验

## 唯一问题

把参数矩阵当「事实表」用，还是当「快照」用？重新抓取后如何区分规则变化与状态变化？

## 实际动作

- 抓取 3 个公开只读响应（orderBooks + 两腿 orderBookDetails），HTTP 全 200，原始 JSON + manifest 落盘；
- 编写 `lab/day9_parameter_recheck.py`（抓取 + 自动 diff + 合约/状态分类）；
- 编写 `lab/test_day9_parameter_recheck.py`，7/7 通过；
- 浏览器打开 Day 9 lesson，完成字段分类与 5 题验收。

## 关键结论

1. **参数矩阵是快照，不是事实表**：必须带 `captured_at`；重新抓取是研究常态，不是异常。
2. **合约级字段（杠杆、精度、最小单、费率）7 天 0 变化**：决定「能不能下单」，一般稳定但可能被交易所调整。
3. **状态级字段（价格、成交量、笔数、OI）大幅变化**：决定「有没有机会」，每次对比都要重新核验。
4. **两个真实数据教训**：
   - BRENTOIL 成交额 +354% 但笔数几乎不变 → 平均单笔变大，不能断言「散户暴增」；
   - WTI 价格 +11% 但 OI −12.5% → 无法仅凭两个数字判断驱动力量，需要更多证据。
5. 规则没变 ≠ 机会存在；参数核验只是第一道闸门。

## 证据路径

- `lab/data/day9_raw/orderBooks.json`、`orderBookDetails_145.json`、`orderBookDetails_159.json`、`day9_capture_manifest.json`
- `lab/data/day9_parameter_diff.json`
- `lab/day9_parameter_recheck.py` / `lab/test_day9_parameter_recheck.py`
- `notes/day9-parameter-recheck.md`
- `lessons/0008-day9-parameter-recheck.html` / `reference/day9-parameter-recheck.html`

## Go / No-Go / Blocked 结论

- 学习层面：Day 9 完成（测试 7/7、验收通过、证据可复查）。
- 研究层面：**Blocked**。参数允许下单只是第一道闸门；走档、资金费账本、退出路径仍未验证，不能因此认为策略可交易。

## 明日唯一动作

Day 10：WebSocket 实时盘口采集（快照+增量+连续性校验），自建 L2 历史。
