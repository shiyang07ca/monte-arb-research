# Day15：连续数据与异常发现

> 状态：工作台能力已实现并运行（2026-08-20），用户研究动作待完成

## 已实现（2026-08-20）

- `src/monte_arb/day15_collector.py`：Lighter/Hyperliquid 公共 WS 连续采集（l2Book/trades/activeAssetCtx；Lighter order_book），追加式 gzip JSONL，每次运行新建会话目录；
- `src/monte_arb/day15_analysis.py`：市场自身基线（spread/深度/更新频率/价格波动/静默缺口）、异常窗口（transient/repeating/persistent/structural）、500 小时时段结构；
- `tests/test_day15_collector.py` + `tests/test_day15_analysis.py`：23 项新测试（全仓 79 项通过）；
- 真实采集会话 `research/raw/day15/20260820T001309Z`（9 分钟，4 市场），分析报告 `research/runs/day15-analysis-20260820T001309Z.json`；
- 课程页 `lessons/0011-day15-continuous-data.html` + 参考卡 + 数据生成器 `day15_lesson_data.py`。
>
> 里程碑允许跨多个工作日

## 目标

让工作台从“当前快照推荐”升级为“根据连续真实数据发现异常”。用户学习区分一次噪声、持续异常、重复模式和时段结构，而不是背时间字段。

## 工作台新增能力

- Lighter 与 Hyperliquid 公共 WS 连续采集；
- BBO/L2、trades、mark/index、funding、status 的追加式事件；
- 每个连接的数据新鲜度、断连、重连、缺口与覆盖情况；
- 每个市场自身基线：spread、depth、更新频率、volume、funding、price deviation；
- 异常窗口：突变程度、持续时间、重复频率、session 标签；
- 候选图表支持前后窗口与原始事件钻取；
- 双榜使用连续数据，不再只靠一次 REST 快照。

## 用户研究动作

工作台提供：

- 一个瞬时但迅速消失的异常；
- 一个持续或重复的异常；
- 一个由时段/维护/展期解释的结构变化。

用户选择一个继续研究，并解释它为何比其他两个更值得投入实验。Agent 随后展示竞争解释与数据质量诊断。

## 无实时好候选时

使用保存的真实历史窗口或重连故障，升级异常检测、时段标签或数据健康视图。

## 完成条件

- 原始事件可回放且重启不覆盖；
- 断连、缺口和过期在候选页可见；
- 同一异常检测器可用于不同资产；
- 用户能从真实连续数据区分噪声、持续异常和时段结构；
- 用户选择的研究方向形成一个新 detector、feature 或诊断视图。

不要求用户修改代码，不用固定阈值预测题证明掌握。
