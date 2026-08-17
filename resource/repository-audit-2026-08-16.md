# 仓库现状审查与清理建议（2026-08-16）

> 状态：已于 2026-08-17 执行
>
> 本文记录重构前发现的问题。用户确认新目标后，旧网页课程、错误 Day6 路径、打卡响应和重复规划已删除；当前计划见 [`resource/plan.md`](./plan.md)。

## 1. 结论

仓库已经积累了市场规则、快照、课程页面和 36 个通过的单元测试，但还没有形成目标系统的最短可运行路径：

```text
当前可交易市场清单
→ 可比较候选
→ 同时段 L2 原始事件
→ 可执行净收益
→ 双腿故障重放
→ NautilusTrader 确定性重放
→ 实时行情下的模拟运行
```

更严重的是，现有绿灯测试保护了至少一个已知错误公式和一个会把未知 symbol 静默映射到
`BRENTOIL` 的实现。测试通过目前只能证明程序按旧假设运行，不能证明研究结果正确。

## 2. 已核验事实

- `python3 -m unittest discover -s lab -p 'test_*.py' -v`：36 个测试通过。
- 仓库没有 `pyproject.toml`、依赖锁文件或已安装的 `nautilus_trader`。
- 没有连续 WebSocket 采集器、确定性 L2 双腿重放器、双腿状态机或实时模拟程序。
- `lab/audit_lighter_rwa.py` 对除 `WTI` 外的任意 symbol 都选择
  `159_orderBookDetails.json`；请求 `XAG` 会得到 `BRENTOIL`。
- `lab/day6_funding_ledger.py` 使用 `index_price`，而学习记录已经说明当前 Lighter 规则使用
  mark；示例价格还没有与 funding 时刻匹配。
- `lab/test_venue_schema.py` 和 `lab/test_day7_data_cleaning.py` 会直接改写已跟踪的数据产物，
  不是隔离测试。
- `lab/data/` 中有 29 个 `icl_*.json` 响应文件，共约 128 KiB；这些是打卡操作痕迹，
  不是套利研究输入。
- `resource/` 约 6 MiB，主要是 3 份 PDF 和两版旧课程规划；`lessons/`、`reference/` 与
  `assets/` 中存在重复的 HTML/JavaScript 教学表面。
- 当前工作区已有多项未提交修改；后续清理必须逐项复核，不能覆盖与本次重构无关的内容。

## 3. 最高优先级问题

### P0：绿灯测试掩盖错误研究语义

影响：未知 symbol 可以被当成另一个市场；错误结算价可以生成看似精确的 funding PnL。两者都会制造假机会。

建议：新课程开始前先删除或隔离已知错误的可执行路径。重新实现时从失败测试开始：

- 未知 symbol 必须显式失败；
- 返回的 venue、完整 symbol、market/instrument id 必须与请求一致；
- funding 结算价格缺失或时点不一致时返回 `unknown`，不得产生数值现金流；
- 测试只能写临时目录。

### P0：没有端到端的真实研究路径

影响：当前材料能解释许多概念，却不能用同一份输入重算一个候选，更不能说明实时运行发生了什么。

建议：Day12–20 只建设一条路径，每天增加一个可运行能力。研究对象先用 BTC/ETH 验证程序，再用
XAU/GOLD 检验 RWA 特有问题。Day21 才换到未教学的候选。

### P0：助手产物被误当成用户掌握

影响：HTML 页面、参考卡、脚本和测试可能主要由助手生成；学习记录中的“已完成”不能证明用户能独立实现或诊断。

建议：以后每个学习日只在以下四项同时存在时记为通过：

1. 用户先给出决定和理由；
2. 用户亲自写或修改核心代码；
3. 用户亲自写至少一个会先失败的测试；
4. 换一个市场或故障后仍能得到正确决定。

### P1：动态市场事实与历史快照混用

影响：CRWD 已经下架，而近期笔记仍把它列为候选；旧参数文件也可能继续通过测试。

建议：所有候选判断保存 `observed_at`、接口参数、完整 symbol、状态和输入哈希。历史快照只作为测试 fixture，
文件名和 manifest 必须说明它不是当前市场事实。

### P1：框架版本与示例版本没有锁定

影响：NautilusTrader 当前稳定版为 `1.231.0`，Python 需要 `>=3.12,<3.15`；Lighter 的 Python
data tester 示例当前存在于开发分支，而稳定标签中的实现结构不同。直接照抄网页示例可能无法在锁定版本运行。

建议：先锁定稳定版本并做 import/build-only smoke test，再写课程代码。只配置 data client，不配置 execution client；
没有单独的显式授权，不读取交易密钥。

### P2：教学文件过多，真实程序过少

影响：同一个概念分散在 lesson、reference、notes、learning-records 和 JavaScript 中，修改时容易互相矛盾。

建议：重构后只保留四类文件：

- `curriculum/`：当天真实任务与通过条件；
- `src/monte_arb/`：可复用研究和模拟逻辑；
- `tests/`：隔离的单元、fixture 和重放测试；
- `research/`：输入 manifest、运行结果和决定记录。

## 4. 文件处理建议

| 处理 | 对象 | 理由 | 执行时机 |
|---|---|---|---|
| 保留 | `MISSION.md`、`NOTES.md`、`RESOURCES.md` | 保存目标、教学偏好和来源；新目标确认后再修订 | 用户回答诊断问题后 |
| 保留 | `learning-records/` | 作为历史记录，但把“生成过材料”和“用户掌握”分开 | 重构时统一加状态说明 |
| 保留并迁移 | Day7 数据质量、Day8 场所字段解析、Day9 参数快照逻辑 | 有可复用原则，但要改成纯函数和临时目录测试 | 新数据层建立时 |
| 保留少量 fixture | 有时间、来源和 manifest 的原始公开响应 | 用于回归测试和故障重放，不再代表当前市场 | 每个 fixture 加状态字段后 |
| 重写 | `resource/plan.md`、`lessons/README.md`、`lab/README.md` | 当前计划仍以概念日和大量助手产物组织 | 新目标确认后 |
| 删除 | Day6 错误公式的可执行脚本、测试、快照、HTML 和参考卡 | 已知与当前官方规则冲突，继续保留会误导后续实现 | 新 funding 实现有失败测试后 |
| 删除 | `lab/data/icl_*.json` | 打卡操作痕迹不属于研究数据，且增加隐私和凭据处理风险 | 确认不再被学习记录引用后 |
| 删除 | Day3–11 的交互 HTML 和配套 JavaScript | 网页测验不再作为学习或验收方式 | 新课程 Markdown 任务就位后 |
| 删除或归档 | `resource/day9-21-redesign.md`、旧版 `resource/plan.md` | 多个“当前计划”会产生冲突 | 新计划确认并写入后 |
| 复核后删除 | 3 份 PDF 与其图片资源 | 只保留已被可靠摘要覆盖且可重新取得的资料 | 逐份核对来源和摘要后 |

建议直接删除可由 Git 历史恢复的旧代码，不再建立庞大的 `archive/`。尚未跟踪且只有本地一份的用户内容，必须先确认或保留。

## 5. 推荐的最小工程形态

```text
curriculum/
  day12.md ... day21.md
src/monte_arb/
  candidate.py       # 当前状态、身份、阻断原因
  books.py           # L2 校验、共同数量和 VWAP
  economics.py       # 四次成交、费用、funding、失败损失
  execution.py       # 双腿状态和允许动作
  decision.py        # Reject / Continue collecting / Paper-only
  strategy.py        # NautilusTrader 适配层
tests/
  fixtures/          # 带 manifest 的冻结输入
  replay/            # 确定性事件序列
research/
  manifests/
  runs/
  decisions/
```

不要新增数据库服务、消息队列、Web UI 或通用插件系统。SQLite 只在连续采集确实需要游标和查询时引入；
Parquet 只服务 NautilusTrader 重放。两个存储都不能代替不可变原始事件和 manifest。

## 6. 清理前的阻断条件

在执行破坏性修改前，需要先确认：

1. Day12–21 的主成果是 perp/RWA 实时模拟，还是要把 on-chain fork 重放改为主成果；
2. 用户是否愿意亲自编写核心实现，助手只提供 review、测试建议和局部提示；
3. 新目标确认后，旧未跟踪课程文件是否允许直接删除而不归档。

## 7. 2026-08-17 执行结果

用户逐项确认了主成果、学习分工、研究范围、服务器与只读账户权限，并选择直接清理旧材料。已经完成：

- 重写 `MISSION.md` 与 `resource/plan.md`；新增 `curriculum/day12.md` 至 `curriculum/day21.md`。
- 删除全部旧交互 HTML、配套 JavaScript 和打印参考页。
- 删除会错误映射未知交易标识的旧审计程序，以及使用错误 funding 结算价格的 Day6 程序、测试和快照。
- 删除 29 个打卡 API 响应、旧课程空模板、重复规划和过时研究章程。
- 保留有来源的公开原始数据、仍可复现的研究程序、研究笔记、历史学习记录和三份原始 PDF。
- 修正三个历史测试，使其只写系统临时目录；27 个保留测试通过，运行前后六个研究产物的 SHA-256 完全一致。
- 仓库未发现残酷共学访问凭据。

服务器尚未修改；公开行情采集器在 Day14 实施。
