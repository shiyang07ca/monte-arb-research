# 研究能力训练设计

> 目标：训练用户发现市场现象、提出竞争解释、选择区分性实验、解释结果并迁移到新场景，而不是训练填写模板或接受 Agent 结论。

## 1. 对旧课程的诊断

旧 Day14–21 虽然包含真实数据和测试，但学习行为仍以“读 Agent 做好的实现 → 回答一个浅问题”为主，存在四个根本问题：

1. **产出属于 Agent，不属于学习者的研究过程。** 用户没有参与候选选择、假设竞争和实验取舍。
2. **问题多为单步分类。** `same/different/unknown`、`include/exclude` 能检查局部概念，却不能训练发现机会。
3. **每天重新包装概念。** 独立 HTML、状态码和记录没有持续累积成用户真正使用的研究系统。
4. **否定成为课程主线。** 失败关闭是系统安全属性，但不断重复“证据不足”不能训练提出新研究方向。

## 2. 新的核心训练循环

```text
工作台扫描真实市场
→ 分别生成交易吸引力榜与研究价值榜
→ 优先展示最多 3 个候选
→ 用户选择 1 个
→ 页面先只显示现象与证据
→ 用户给出简短初步解释
→ 解锁 Agent 的竞争假设
→ 用户选择/质疑最有区分力的实验
→ Agent 实现并运行
→ 用户解释结果与下一步
→ 结果升级工作台指标、实验器或雷达
→ 以后在新资产/场所再次迁移
```

用户不写代码。Agent 负责实现、运行、修复和维护；用户负责研究判断。

## 3. 为什么这样训练

### 3.1 先独立提取，再看 Agent 分析

检索练习比重复阅读更能促进保持与迁移。候选页先隐藏 Agent 解释，迫使用户从真实图表和市场背景中提取已有知识；提交初步解释后立即解锁分析，避免演变成冗长考试。

来源：Karpicke & Blunt, *Retrieval Practice Produces More Learning than Elaborative Studying with Concept Mapping*, Science (2011), DOI [1]。

### 3.2 要求解释机制，不要求猜标签

自我解释能提高理解。用户应说明“什么机制能产生这个图形，以及还会看到什么证据”，而不是只选 `A/B/C`。

来源：Chi et al., *Eliciting self-explanations improves understanding*, Cognitive Science (1994), DOI `10.1016/0364-0213(94)90016-7`，见 [2]。

### 3.3 竞争假设与区分性实验

每个候选至少保持两个可证伪解释。实验的价值不在于“收集更多数据”，而在于不同解释对结果有不同预测。例如价差扩大可能来自：

- 一边报价延迟；
- oracle 或 session 状态变化；
- 深度真实失衡；
- funding/OI 驱动的仓位压力。

好的实验必须说明：如果结果 A 出现，哪个解释变强；如果结果 B 出现，哪个解释变弱。

来源：

- Klayman & Ha, *Confirmation, disconfirmation, and information in hypothesis testing*, Psychological Review (1987), DOI [3]。
- Platt, *Strong Inference*, Science (1964), DOI [4]。
- Klahr & Dunbar, *Dual Space Search During Scientific Reasoning*, Cognitive Science (1988), DOI [5]。

### 3.4 预测需要校准和可追踪更新

工作台保存用户对机制和结果方向的置信度，但不把概率评分做成形式任务。用途是观察用户何时会根据新证据合理更新，而不是事后总说“我早就知道”。

来源：

- Mellers et al., *Psychological Strategies for Winning a Geopolitical Forecasting Tournament*, Psychological Science (2014), DOI [6]。
- Mellers et al., *The psychology of intelligence analysis: Drivers of prediction accuracy in world politics*, Journal of Experimental Psychology: Applied (2015), DOI [7]。

这些研究不是交易盈利证据；这里只借用分解问题、校准、更新和比较解释的方法。

### 3.5 间隔与交错迁移

同一机制不能只在原案例里做一次。几天后应在不同资产、venue 或历史时期重新出现，检验是否能识别共同结构。工作台需要混合展示价差、funding、RWA session、深度与链上事件，而不是连续十次同类练习。

来源：

- Cepeda et al., *Distributed practice in verbal recall tasks: A review and quantitative synthesis*, Psychological Bulletin (2006), DOI [8]。
- Rohrer & Taylor, *The shuffling of mathematics problems improves learning*, Instructional Science (2007), DOI [9]。
- Barnett & Ceci, *When and where do we apply what we learn? A taxonomy for far transfer*, Psychological Bulletin (2002), DOI [10]。

### 3.6 反馈针对推理过程

反馈不应只是“正确/错误”，而应指出：

- 哪条证据被漏看；
- 哪个隐含假设未经验证；
- 哪个实验不能区分解释；
- 哪个结论超出了数据；
- 下一次遇到相似现象应该先看什么。

来源：

- Hattie & Timperley, *The Power of Feedback*, Review of Educational Research (2007), DOI [11]。
- Shute, *Focus on Formative Feedback*, Review of Educational Research (2008), DOI [12]。

## 4. 候选页的展示顺序

### 第一屏：不显示 Agent 机制解释

只显示：

- 现象图；
- 可成交盘口与规模；
- 发生时段；
- 当前 funding/OI/volume；
- 数据质量与已知事实；
- 为什么被推荐（交易榜、研究榜分别说明）。

用户只需给出简短解释，可包含“不知道，但我想先查 X”。不要求固定模板。

### 第二屏：解锁竞争分析

显示：

- Agent 提出的 2–4 个竞争解释；
- 每个解释支持/反对证据；
- 最有区分力的实验及预期结果；
- 用户解释与 Agent 解释的差异。

### 第三屏：实验与结果

用户决定运行哪个实验，或指出实验设计问题。Agent 执行后，用户解释：

- 哪个机制更可信；
- 哪个仍不能排除；
- 是否值得继续；
- 工作台应该新增什么能力。

## 5. 双榜不是考试分数

### 交易吸引力榜

交易吸引力榜按里程碑逐步增加真实可计算的组成：Day14 只使用当前快照可计算的价差、深度、状态和数据质量；Day15 加入持续时间与重复频率；Day16 加入资金费、费用和退出成本；Day19 加入执行失败成本。每项保留原值和理由，不隐藏为单一总分。

### 研究价值榜

展示现象新颖度、竞争解释数量、实验信息增益、工具复用价值和跨市场迁移价值。

每次优先展示最多 3 个；不足 3 个时不凑数。两个榜不合成神秘总分。

## 6. 无好候选时

用历史真实异常或注入故障升级工作台，而不是制造机会。可用任务包括：

- 识别时间错位造成的伪价差；
- 解释 funding 突变；
- 检测 RWA 展期/休市价格断层；
- 回放深度与机会寿命；
- 诊断市场映射、快照缺口或重连错误；
- 为机会雷达增加一个低成本数据源。

当天必须留下可复用指标、实验器、诊断视图或新数据适配，而不是学习记录本身。

## 7. Day14–21 的能力验收

里程碑可跨多天，只有工作台能力和真实研究动作同时完成才推进。

- **Day14**：用户能从双榜展示的真实候选中选择一个，并给出初步解释；Agent 的后续分析不会覆盖用户原始推理；实验记录能回到候选页。
- **Day15**：用户能从连续数据区分一次性噪声、持续异常和时段结构，并选择值得继续的异常。
- **Day16**：用户能读懂不同规模下的可成交结果，选择方向与规模，并识别屏幕价差为何不等于现金结果。
- **Day17**：用户能比较竞争机制，选择真正有区分力的实验，并根据结果更新判断。
- **Day18**：用户能解释纸上交易分布、持有时间与失败样本，不用最佳单笔替代整体结果。
- **Day19**：用户能在部分成交/第二腿失败回放中说明实际敞口、允许动作和最差结果。
- **Day20**：用户能从实时候选与机会雷达中选一个方向，判断是否值得投入适配成本。
- **Day21**：在未详细教学的新候选上，用户能独立完成选择、机制解释、实验取舍、结果解释和系统下一步。

## 8. 明确删除的形式

- 不再用按钮点击、页面完成状态或 Agent 测试通过证明掌握；
- 不再每天固定问四个步骤；
- 不再用大量浅选择题；
- 不要求用户写代码；
- 不要求为每次思考填概率模板；
- 不把哈希、manifest、状态码作为学习内容；
- 不把 `unknown/exclude` 当作每天的主题；
- 不在用户思考前展示 Agent 的完整结论。

## Sources

[1] https://doi.org/10.1126/science.1199327
[2] https://doi.org/10.1016/0364-0213%2894%2990016-7
[3] https://doi.org/10.1037/0033-295X.94.2.211
[4] https://doi.org/10.1126/science.146.3642.347
[5] https://doi.org/10.1207/s15516709cog1201_1
[6] https://doi.org/10.1177/0956797614524255
[7] https://doi.org/10.1037/xap0000040
[8] https://doi.org/10.1037/0033-2909.132.3.354
[9] https://doi.org/10.1007/s11251-007-9015-8
[10] https://doi.org/10.1037/0033-2909.128.4.612
[11] https://doi.org/10.3102/003465430298487
[12] https://doi.org/10.3102/0034654307313795
