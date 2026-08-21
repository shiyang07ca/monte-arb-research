# Day16：可执行性与容量

> 状态：工作台能力已实现并运行（2026-08-21），用户研究动作待完成
>
> 里程碑允许跨多个工作日

## 已实现（2026-08-21）

- `src/monte_arb/day16_execution.py`：冻结 L2 走档引擎（`walk_book`、`order_qty_for_notional`、`leg_execution`、`pair_execution`、`capacity_usd`）+ `build_execution_snapshot` + CLI `run_execution_scan`；
- 真实扫描 `research/runs/day16-execution-scan.json`：60 对候选、120 本盘口、0 请求错误；Lighter `orderBookDetails` 批量参数（费率/精度/最小单/multiplier）+ 逐对 L2（Lighter 限流 1.1s 间隔）；
- 工作台执行视图 `/workbench/execution`：深色 UI（参考 perpdexlist Execution Cost），pair/方向/规模选择、容量曲线条、逐规模表、自定义规模即时重算（`POST /workbench/api/execution/compute`）、30s 自动刷新 + 手动刷新（`POST /workbench/api/refresh`）；
- `tests/test_day16_execution.py`：23 项新测试（全仓 134 项通过）；
- 课程页 `lessons/0012-day16-execution-capacity.html` + 参考卡 `reference/day16-execution-capacity.html` + 数据生成器 `day16_lesson_data.py`。

## 真实发现（2026-08-21 00:14 UTC 快照）

- **BRENTOIL 买左卖右 +0.44 bps（$25–250）→ +0.15（$500）→ −0.03（$1000）**：翻转来自卖腿（HL）滑点随档位消耗上升，容量曲线完整可见；
- **AAPL 方向不对称**：买右卖左 +4.80 bps 稳定到 $500（$1000 才降到 +4.70），反向始终 −6 bps 附近；Lighter tick 0.001 极窄而 xyz 盘口更厚；
- **$10 档全部 MIN_QUOTE**：向下取整后名义低于最小报价金额，预算档不等于可下单档；
- **HL HIP-3 费率未公开** → 卖腿/买腿 `fee_bps=null`，总成本保持 null，未知不填零。

## 用户研究动作（待完成）

- [ ] 从三个真实候选中选择一个方向与研究规模，回答：为什么这个规模有意义 / 哪一项成本最可能改变结论 / 如果持有时间改变，哪里需要重新计算；
- [ ] 打开 `/workbench/execution` 完成迁移验收：SPCX 或 META 在哪个规模失去吸引力；HL 假设 2.5 bps 后哪些方向翻负。

## 完成条件核对

- [x] 多个规模、两个方向可从冻结 L2 重算；
- [x] 深度不足保留未成交数量；
- [x] mark/oracle/mid 不替代成交价；
- [x] 未知账户费率不填公开默认零成本；
- [ ] 用户能解释候选在哪个规模失去吸引力，以及为什么；
- [x] 结果形成工作台通用容量视图和交易榜特征。

## 下一步（Day17 或用户选择）

- Day17 机制实验室：用区分性实验解释方向/规模翻转的机制（卖腿深度 vs tick 结构 vs 未知费率）；
- 或先追 HL HIP-3 账户费率证据（userFees 只读端点），把 `fee_bps=null` 变成已知值。
