# 研究工作台详细设计

> 版本：2026-08-18
>
> 状态：Day14–21 重构后的实现依据
>
> 真实订单：禁止

## 1. 产品目标

构建一个持续运行、可扩展、可回放的市场机会研究工作台。它帮助用户：

```text
从全部市场发现异常
→ 选择值得研究的候选
→ 提出竞争机制
→ 运行区分性实验
→ 回放可成交结果与失败
→ 把结论变成下一轮更好的扫描能力
```

Agent 负责实现、运行、修复与维护。用户不写代码，训练重点是发现现象、提出解释、选择验证、解释结果和迁移研究方法。

## 2. 主界面

浏览器工作台是每天的主入口，Telegram 用于选择候选、提交初步解释和下达实验方向。CLI、Python 模块和 Jupyter 是同一系统的可复用工具，不另做孤立课程。

### 页面结构

```text
/workbench
  今日概览：数据状态、扫描范围、优先展示最多 3 个候选

/workbench/candidates
  交易吸引力榜
  研究价值榜
  全部候选与筛选条件

/workbench/candidates/{candidate_id}
  第一屏：现象与证据（隐藏 Agent 解释）
  用户初步解释
  第二屏：竞争假设与实验建议
  第三屏：实验运行、结果、解释与后续

/workbench/experiments
  所有实验历史、输入、结果和系统改进

/workbench/radar
  其他 venue / RWA / TradeFi / funding / 链上侦察

/workbench/system
  数据新鲜度、断连、采集覆盖、任务和存储
```

初版可以是本地 Python Web 应用；框架选择服从快速迭代和可测试性，不把 UI 框架变成课程内容。

## 3. 领域对象

### MarketIdentity

沿用 Day12：

```text
venue + product_type + namespace + full_symbol + local_id
```

### EconomicMapping

描述两个市场是否可能代表可比较的经济对象，以及字段证据和当前不确定性。不能按 ticker 相似度自动定为 same。

### Observation

原始不可变市场事件：instrument、BBO/L2、trade、mark/index、funding、status、source/receive time 与原始引用。

### Candidate

由一组市场、方向和一个异常窗口组成。Candidate 不是机会结论，必须指向所有原始 Observation 和派生 Feature。

### CandidateFeature

可重算指标，例如：

- 可成交双向 spread；
- 目标规模 VWAP 与容量；
- funding 差；
- OI/volume 变化；
- 持续时间与重复频率；
- session / oracle / roll 标签；
- 数据新鲜度与缺口；
- 退出成本和失败成本。

### Recommendation

分别包含 `trade_rank` 与 `research_rank` 的可解释组成，不保存神秘总分。

### Hypothesis

对候选现象的可证伪机制解释，包含支持、反对证据，以及如果为真还应看到什么。

### Experiment

用于区分两个或多个 Hypothesis 的运行。保存问题、输入窗口、方法、预期区分、实际结果和限制。

### ResearchSession

一次用户研究过程：选择候选、初步解释、解锁 Agent 分析、实验选择、结果解释、系统改进。用户原始解释不可被 Agent 内容覆盖。

### RadarLead

尚未接入主工作台的 venue/机制线索，包含数据入口、约束、异象、最低下一步和升级状态。

## 4. 数据与计算分层

```text
官方 REST/WS/链上事件
        ↓
Raw Event Store（追加式）
        ↓
Normalized Observations（保留 venue 语义）
        ↓
Market State / Pair State
        ↓
Features and Baselines
        ↓
Candidate Detection
        ↓
Trade Ranking / Research Ranking
        ↓
Experiment and Replay
        ↓
Workbench UI
```

### 原始层

- 公开采集器不需要账户凭据；
- 原始响应/事件追加写入，不因派生规则变化而覆盖；
- 每个数据源有独立连接状态与时间语义；
- 长期原始数据不进 Git；仓库保存 schema、代码和小型 fixture。

### 标准化层

公共字段只统一身份、时间和数值类型；oracle、mark、mid、bid/ask、AMM quote 不塞进同一个模糊 `price` 字段。

### 特征层

所有特征由原始数据确定性重算。版本变化不修改旧实验；新版本生成新结果。

## 5. 自动扫描

### 扫描范围

Day14 初版扫描 Lighter–Hyperliquid 全部可映射永续：

1. 每日获取当前目录；
2. 发现可能映射，不写死 WTI/Brent；
3. 为每个方向计算当前 BBO/L2 与上下文；
4. 保留映射不确定性，同时允许原始行情进入研究价值榜；
5. 生成全量候选，不只保存前三名。

### 候选检测器

初版只需要少数透明检测器：

- `cross_venue_executable_spread`：两种方向的可成交 top-of-book/目标规模差；
- `funding_divergence`：同资产 funding 差与方向；
- `reference_dislocation`：mark/oracle/mid 与可成交价关系异常；
- `liquidity_asymmetry`：深度、spread、size 或更新频率不对称；
- `session_transition`：RWA 外部时段、维护、展期或恢复附近异常；
- `data_quality_anomaly`：时间错位、过期、断连、缺口或身份冲突。

检测器输出原值、基线、异常程度和证据，不直接声称盈利。

## 6. 双榜

### 交易吸引力榜

只处理执行层面的研究优先级：

- 两种方向、多个规模下的可成交 spread；
- 深度/容量；
- 持续时间与出现频率；
- 已知费用、funding、退出成本；
- 数据新鲜度；
- 单腿失败和账户约束。

展示各组成值与限制。缺少成本时不填零；可显示区间或 `not computed`。

### 研究价值榜

衡量研究一次能产生多少信息和复用能力：

- 现象新颖度；
- 竞争解释是否真实存在；
- 是否有可执行的区分性实验；
- 实验能否明显改变判断；
- 是否补足工作台通用能力；
- 是否能迁移到其他资产/venue。

初版可使用透明规则和解释文本，不需要机器学习排序。Day14 的交易榜只使用当前快照可计算的价差、深度、状态和数据质量；连续性、完整成本和失败成本分别在 Day15、Day16、Day19 加入，未计算项不参与排序。

### 每日推荐

从双榜优先展示最多 3 个；不足 3 个时不凑数。候选充足时尽量保证：

- 至少一个交易吸引力较高候选；
- 至少一个研究价值较高候选；
- 第三个用于平衡新颖度、可验证性和系统路线；
- 不重复展示几乎相同的候选；
- 无合格候选时明确转入方法训练。

## 7. 候选研究流程

### 阶段 A：现象

页面展示图表、可成交盘口、规模、session、funding/OI/volume、数据质量和推荐原因。此时隐藏 Agent 机制解释。

用户提交一句或一段初步解释，也可以写“我不知道，先验证 X”。

### 阶段 B：竞争解释

解锁 Agent 的 2–4 个 Hypothesis：

```text
机制
支持证据
反对证据
若为真还应看到什么
可区分它的实验
```

Agent 明确指出与用户初步解释的差异，但不以“标准答案”覆盖。

### 阶段 C：实验

用户选择一个实验或质疑实验。Agent 负责实现和运行。实验必须预先写清不同结果如何改变各 Hypothesis，而不是“再收集更多数据”。

### 阶段 D：解释与系统改进

用户解释结果。Agent 给过程反馈，并将产出转为：

- 新 detector / feature；
- 新诊断图；
- 新 replay 场景；
- 新 radar adapter；
- 或已知无效解释的反例。

## 8. 存储

初版建议：

```text
data/raw/                  # Git 外，追加式压缩事件
state/workbench.sqlite     # 候选、会话、假设、实验、任务
research/fixtures/         # 小型脱敏可复现样本
research/exports/          # 人类可读导出
```

SQLite 用于可查询状态和异步实验任务；大体量事件使用压缩 JSONL/Parquet。Day18 回放实现前固定 NautilusTrader 版本并创建 Python `>=3.12,<3.15` 的独立环境；Lighter 与 Hyperliquid 只读数据适配器 smoke test 通过后，Day18–20 再逐步接入 `ParquetDataCatalog`、历史重放和实时影子运行。

## 9. 代码结构目标

```text
src/monte_arb/
  domain/          # identity, mapping, observation, candidate, hypothesis, experiment
  adapters/        # venue-specific REST/WS normalization
  collectors/      # public continuous ingestion
  features/        # spread, depth, funding, session, quality
  detectors/       # transparent anomaly detectors
  ranking/         # trade and research ranks
  experiments/     # discriminating experiments
  replay/          # executable paper replay and failure models
  radar/           # low-cost external venue/protocol probes
  web/             # browser workbench
  cli.py            # scan, collect, detect, experiment, replay, serve
```

现有 Day12–14 模块先作为可验证能力迁入，不做一次性大爆炸重写。

## 10. 后台运行

- 公开采集器独立于 Web UI；
- 每个连接有 heartbeat、last event、reconnect count、gap count；
- 任务有超时、重试和失败原因；
- 进程重启从新分段继续，不覆盖原始数据；
- 数据和日志设上限；
- 账户费率只读进程与公开采集器分离；
- 工作台没有 execution client 和真实下单路由。

## 11. 机会雷达

主工作台之外维护 RadarLead。第一批优先：

1. 全部 Hyperliquid HIP-3 RWA；
2. dYdX 第三 crypto perp 对照；
3. Architect/AX RWA 数据；
4. Ostium/Avantis RWA pricing/session；
5. CEX–DEX funding；
6. Aave/Morpho 清算与利率；
7. AMM/聚合器跨池 quote。

雷达先保存数据入口、限制和一种异象。只有达到 `research/design/opportunity-radar-primary-sources.md` 的最低标准才开发正式适配器。

## 12. Day14 初版完成条件

### 系统能力

- 浏览器工作台是单一持续应用，不再按天复制阅读页面；
- 自动扫描全部可映射 Lighter–Hyperliquid perp；
- 生成全量候选与透明双榜；
- 每次优先展示最多 3 个；不足 3 个时不凑数；
- 单候选页按“现象 → 用户解释 → Agent 假设 → 实验 → 结果”工作；
- 实验记录可回到候选并形成后续系统任务；
- 现有 WTI/Brent 时间和映射诊断成为内部模块。

### 训练能力

- 用户从真实 3 个候选中选择一个；
- 用户在看 Agent 解释前留下简短初步解释；
- 用户选择或质疑一个区分性实验；
- 用户解释实验结果与下一步；
- Agent 根据结果实现至少一项可复用改进。

两组条件都满足才完成 Day14。按钮点击、测试通过、文档完成和 Agent 分析不单独算完成。

## 13. 实施顺序

1. 定义工作台领域对象与 SQLite schema；
2. 将 Day12 市场发现与 Day14 当前快照接入扫描服务；
3. 自动生成可能映射及全量候选；
4. 实现初版 detectors 与双榜；
5. 建浏览器候选榜和候选页；
6. 实现用户解释解锁、Hypothesis 和 Experiment 记录；
7. 用真实扫描选择第一个候选并完成研究；
8. 再开始连续 WS 采集和 Day15。
