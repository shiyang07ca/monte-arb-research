# 0012 · Day15 连续数据与异常发现

> 日期：2026-08-20
> 状态：已记录
> 里程碑：Day15（工作台能力 + 用户研究动作均完成）

## 背景

Day14 工作台 v0 的候选全部来自单次 REST 快照，无法回答"机会持续多久"。Day15 把候选生成升级为基于连续真实数据：Lighter/Hyperliquid 公开 WS 连续采集、市场自身基线、异常窗口分类（transient/repeating/persistent/structural）、时段结构。

## 非显眼教训（需要以后修订的知识）

1. **Lighter WS 是"初始全量快照 + 增量更新"语义**：`subscribed/order_book` 带全量（观察 109 档），`update/order_book` 每消息只带 1–5 个变化档位。把增量消息当独立快照统计，会得到"只有 2 档"的错误盘口结构结论。正确的盘口结构必须用初始快照或 REST 全档。采集器当前保存的是消息原文（增量），分析层需要 book replay 才能在深度/档位数上做跨场对比——这是 Day15 明确的遗留项。
2. **时间戳基准必须同源**：REST 请求内部用 `time.monotonic_ns()`（day14 遗留），WS 事件用 `time.time_ns()`。跨源对齐前必须补记 wall-clock 时间戳，否则"同时刻对比"永远失败且不易察觉（对齐数=0 或全部 miss）。
3. **MAD=0 时阈值退化**：完全平静的序列（合成或真实极低波动）MAD=0，`median + k*MAD` 会把中位数自己当阈值。必须加 `1.5×median` 下限，否则整个序列都是"异常"。
4. **窗口缝合禁止**：静默缺口（>5s 无事件）或乱序时间戳会把两次独立异常缝合成一次长异常；运行拆分规则必须同时处理正间隔超限和负间隔（乱序）。
5. **B 候选的机制修正**："Lighter BRENTOIL 价差是 xyz 的 12 倍"最初候选解释是深度薄/流动性差；REST+WS 同时刻证据显示 Lighter 档1深度反而更厚（165 vs 83），真实机制是 **tick 粒度**：Lighter price_decimals=2（tick 0.01≈1.11bps）vs xyz 0.001（0.11bps），10 倍 tick 差 ≈ 10 倍价差差。大 tick 市场做市商最少报 1–2 tick 间距。**交易所参数（tick）是价差结构的第一性解释，先查参数再猜流动性。**
6. **mark < index 是 mid 偏差的候选来源**：Lighter BRENTOIL mark(90.26) < index(90.31) 5.5bps，与两所 mid 系统性差 3–4bps 方向一致。合约权重仍是 unknown（Day13 遗留），mid 偏差是否有经济意义待确认。
7. **负结果也是结果**：有界采集无瞬时异常时，候选榜显示"无窗口"而不是凑数；这本身是市场平静的证据。

## 已发生事实（证据可复查）

- `src/monte_arb/day15_collector.py`：Lighter/Hyperliquid 公共 WS 采集，追加式 gzip JSONL，会话目录 `research/raw/day15/<utc>/`，重启不覆盖；健康事件独立文件。
- `src/monte_arb/day15_analysis.py`：自身基线（spread/depth/更新频率/10s 波动/静默缺口）、异常窗口（k=6 MAD + 1.5× 下限）、500 小时时段结构。
- `src/monte_arb/day15_depth_diagnosis.py`：B 实验——REST/WS 同时刻对比（wall-clock 对齐）、深度结构、mid 对齐；`--live-duration` 模式。
- 真实采集：本机会话 `20260820T001309Z`（9 分钟 4 市场 0 错误）；VPS `139.162.68.224` systemd `monte-arb-capture.service` 7 天录制运行中（会话 `20260820T011135Z`）。
- 测试 84/84；提交 `969e9ef`（B 实验）、`981a529`（Day15 主体）。
- 课程页 `lessons/0011-day15-continuous-data.html` + 参考卡 `reference/day15-continuous-data.html`。
- 报告：`research/runs/day15-analysis-20260820T001309Z.json`、`day15-experiment-b-live2.json`、`day15-experiment-b-tick-evidence.json`。

## 研究状态

**Blocked / No-Go**：B 的持续价差差确认为真，但机制是 tick 粒度 + 做市行为，不是可成交套利证据。Lighter 零费率与 mark<index 5.5bps 是新线索，合约权重未确认前不能计算经济意义。

## 下一步（Day16 或用户选择）

- Day16 可执行性与容量：两所 BBO 逐档、共同数量、零费率下保守可成交价差与容量曲线。
- 或先追合约权重证据（回答 mid 偏差是否有经济意义）。
- 遗留工程项：Lighter 增量消息的 book replay（盘口重建）用于深度/档位统计；采集器增量语义确认（size=0 是否删除档位）。
