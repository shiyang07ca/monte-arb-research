# 21 天链上套利研究训练计划

> 版本：2026-08-04
>
> 每日投入：40–90 分钟，默认 60 分钟
>
> 核心原则：先解释偏差，再测量偏差；先证明可执行净收益，再讨论自动交易。

## 结论

这 21 天只做一件事：

> **在 Arbitrum One 上，以 WETH/USDC 的两个 Uniswap v3 费率池为实验对象，完成“读取同一链上状态 → 计算不同规模的可执行报价 → 扣除成本 → 回放与证伪 → 输出继续或停止判断”的完整研究流程。**

最终目标不是做出一个赚钱 Bot，也不是学完所有 DeFi 主题，而是形成五种可复用能力：

1. 能解释价格偏差为什么出现，以及偏差由谁修复。
2. 能独立取得带区块信息的链上数据，并判断数据是否可比较。
3. 能区分网页价格、毛价差与可执行净收益。
4. 能用固定区块、真实交易和失败样本检验自己的判断。
5. 能让 AI 帮助查资料、写代码和复盘，但不让 AI 代替确定性计算与风险规则。

## 对当前背景的重新评估

### 已确认

- 已经使用 Claude Code 和 Codex，具备以代码仓库、任务和文档推进工作的习惯。
- 目标偏向独立研究、数据分析、机会发现和工程实现，不需要通用区块链入门课程。
- 每天只有 40–90 分钟，过重的基础设施建设会挤掉真正的数据实验。
- 希望探索 Hermes，但现有 Coding Agent 已能完成大多数近期任务。

### 尚未确认

当前资料没有证明以下能力已经熟练掌握：

- EVM 状态、区块标签、日志和交易回执；
- Uniswap v3 的 tick、流动性区间与规模相关报价；
- 固定区块回放、净收益模型和 MEV 排序约束；
- 从候选信号到 Paper Trading 的独立研究过程。

因此，本计划将你的起点定义为：

> **通用工程与 AI 工具能力较强，链上套利研究能力需要用实际产出校准。**

Day 1 不做问卷，而用一个最小任务测试起点。若 30 分钟内已能读取链、区块和池状态，就把余下时间用于增加测试或固定区块参数；不要因此增加第二条链或第二个策略。

## 第一性原理

### 套利成立的必要条件

```text
可执行净收益
= 最终收到资产的可执行价值
- 初始资产成本
- 协议费
- 价格冲击与滑点
- Gas 与 L1 数据费
- 排序或包含成本
- 失败与状态过期成本
- 资金占用与库存风险
```

任何候选机会都必须回答五个问题：

1. **偏差机制**：为什么两个池会出现不同报价？
2. **状态一致性**：报价是否来自同一 block number 和 block hash？
3. **交易规模**：在 100、500、1,000、5,000、10,000 USDC 等规模下，实际能收到多少？
4. **完整成本**：扣除手续费、Gas、安全余量和失败成本后还剩多少？
5. **捕获条件**：机会持续多久，普通交易是否可能在排序竞争中得到它？

如果第五个问题没有答案，结果只能标记为“研究信号”，不能标记为“可交易机会”。

## 本期范围

| 项目 | 本期选择 | 原因 |
| --- | --- | --- |
| 主链 | Arbitrum One | 费用较低，官方提供公开 RPC；Timeboost 使排序成本成为必须理解的变量 |
| 交易对 | WETH/USDC | 资产与地址容易从协议官方资料交叉核验，流动性池长期存在 |
| 比较对象 | Uniswap v3 0.05% 与 0.3% 两个池 | 只写一套协议适配代码，同时训练费率、流动性和规模对报价的影响 |
| 方法 | 只读查询、历史数据、固定区块回放、Paper 记录 | 先证明数据和计算正确，不承担真实资金风险 |
| 代码 | Python、少量 Pandas、pytest；需要回放时再装 Foundry | 避免提前建设数据库、服务和前端 |
| AI | Codex 或 Claude Code 负责实现，另一个只在复盘日审查；Hermes 限时评估一次 | 防止工具切换代替学习 |

### 已核验的实验常量

以下地址来自官方文档，并在 2026-08-04 通过 Arbitrum One 的 `eth_call` 再次检查。访问时区块为
`491017954`，两个目标池的 `liquidity()` 都不为零。开始实验时仍要重新查询 Factory，不能把本表当作永久状态。

| 对象 | 地址 |
| --- | --- |
| Arbitrum One 公共 RPC | `https://arb1.arbitrum.io/rpc` |
| Uniswap v3 Factory | `0x1F98431c8aD98523631AE4a59f267346ea31F984` |
| Uniswap v3 QuoterV2 | `0x61fFE014bA17989E743c5F6cB21bF9697530B21e` |
| WETH | `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1` |
| USDC | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` |
| WETH/USDC 0.05% 池 | `0xc6962004f452be9203591991d15f6b388e09e8d0` |
| WETH/USDC 0.3% 池 | `0xc473e2aee3441bf9240be85eb122abb059a3b57c` |

公共 RPC 适合低频学习查询，但 Arbitrum 官方明确说明它没有可用性、延迟或限流保证。它不能用于判断生产系统的延迟优势。

## 方向取舍

| 方向 | 21 天内的决定 | 理由 |
| --- | --- | --- |
| 同链、同区块、不同规模的可执行报价比较 | **唯一主线** | 同时训练 AMM、RPC、数据、成本、验证和工程实现 |
| MEV 与 Arbitrum Timeboost | **必须理解，不做竞速系统** | 排序决定理论机会能否被普通参与者捕获 |
| LI.FI 跨链报价 | **限时 1 天观察** | 用于理解桥费、时间和非原子风险，不把聚合器最佳报价误当成个人优势 |
| Hermes | **限时 1 天评估** | 只验证它是否比现有 Codex/Claude 工作方式多出长期记忆或定时任务价值 |
| Uniswap v4、Hooks | **暂缓** | 当前训练不需要增加协议状态和 Hook 行为复杂度；v3 仍有官方部署和文档 |
| CEX–DEX、跨链库存套利 | **暂缓** | 需要交易所数据、账户、库存和延迟模型，当前证据不足 |
| 三角套利、清算、闪电贷 | **暂缓** | 都是成熟且竞争激烈的主题；闪电贷只解决资金，不创造净优势 |
| Ethereum 主网公共 mempool Bot | **排除** | Ethereum 官方资料明确提示经典 DEX 套利对新 searcher 通常不再有直接盈利空间 |
| Sandwich 与 AI 自动发送真实交易 | **排除** | 前者损害用户；后者把不确定推理放进高风险执行过程 |
| Postgres、消息队列、微服务、监控大盘 | **排除** | 21 天内 CSV/Parquet、脚本和简短报告足够验证假设 |

这并不表示经典 DEX 套利“没有价值”。它仍是学习可执行价格、状态时效、成本和 MEV 的好实验，但不能把学习价值写成盈利承诺。若 21 天后要继续寻找更有希望的方向，应从协议特有机制、长尾事件和自身可验证的数据优势出发，而不是继续复制通用套利 Bot。

## 最终能力模型与产出

### Day 21 应具备的能力

| 能力 | 可观察证据 |
| --- | --- |
| 状态读取 | 能保存 chain ID、block number、block hash、timestamp、池地址和查询时间 |
| AMM 与报价 | 能解释 tick、活动流动性、费率和交易规模为何改变 `amountOut` |
| 数据分析 | 能比较两个池、两个方向和多个规模，并识别状态错配与异常值 |
| 净收益判断 | 能输出毛价差、协议费、Gas、安全余量和最终判断 |
| 证伪 | 至少否定一个原本看好的信号，并写清失败原因 |
| 回放 | 能在固定区块重复一次报价或候选判断 |
| 工程实现 | 一个命令可以完成“读取 → 报价 → 分析 → 输出报告” |
| AI 工作方式 | 有一个固定研究提示词和一份 agent 分工说明，不向 agent 提供钱包私钥 |

### 只要求五项最终产出

1. `research-charter.md`：一页研究范围、净收益模型、风险边界和停止条件。
2. `quotes.csv` 或 `quotes.parquet`：至少 20 个时间点、两个池、两个方向、五个规模的带区块报价。
3. `arb_lab.py` 或等价的小型模块：读取、报价、计算成本并给出 reason code。
4. `case-study.md`：一笔真实交易或一次价格变化的状态、日志、成本和失败条件分析。
5. `final-report.md`：两页以内的 Go / No-Go 结论，以及唯一一个下一阶段方向。

不要求执行合约、实时服务器、数据库、前端、监控大盘或真实收益。

## 每日节奏

默认 60 分钟：

- 5 分钟：写下今日唯一问题和完成条件。
- 15 分钟：阅读最多两份一手资料，只摘录实验需要的事实。
- 30 分钟：查询、编码、计算或回放。
- 10 分钟：保存证据、写结论和明日唯一动作。

时间不足时用 40 分钟版本：5 + 10 + 20 + 5。状态很好时最多延长到 90 分钟，只允许加深当天实验，不允许增加新主题。

### 防止过度思考的规则

- 同时只有一个活动假设；新想法写入 `parking-lot.md`。
- 每天最多读两份资料，连续阅读 20 分钟后必须开始操作。
- 卡住 15 分钟就让 Codex 或 Claude Code解释错误并给出最小修复。
- 同一个问题只选一个 agent 实现；另一个 agent 只在 Day 7、14、20 审查。
- 工具只有在同一阻碍出现两次后才允许新增。
- 到 90 分钟立即停止，保留失败状态也算有效证据。
- 漏一天不补双倍任务，直接继续下一天；Day 7 或 Day 14 再决定是否调整。

## 21 天大纲

### 第一周：从概念到第一次同区块比较

| Day | 时间 | 今日唯一问题 | 实操与完成条件 | 当日产出 |
| --- | --- | --- | --- | --- |
| 1 | 60 分钟 | 我现在能否独立读取链上状态？ | 固定主链、交易对和两个池；读取 chain ID、最新区块号、hash、timestamp；写明真实资金禁区 | `research-charter.md` 与第一条打卡 |
| 2 | 60 分钟 | 为什么交易规模会改变价格？ | 用公式或 Python 实现常数乘积基线，画出 `amountIn → executionPrice`；再写三句话说明 v3 与 v2 的差异 | 一张曲线与一个可运行函数 |
| 3 | 60 分钟 | 哪些数据必须绑定到同一状态？ | 连续读取 10 次区块，保存请求时间、block number、hash 和 timestamp；检查是否出现重复或状态变化 | `blocks.jsonl` 与字段说明 |
| 4 | 60–75 分钟 | 两个目标池是否真实且可读？ | 从官方部署地址和 Factory 重新取得池地址；在同一 blockTag 读取 `token0`、`token1`、`fee`、`liquidity`、`slot0` | `pools.json` 与地址核验记录 |
| 5 | 60–75 分钟 | 一个池在不同规模下能给出多少？ | 用 QuoterV2 对 100、500、1,000、5,000、10,000 USDC 报价；保存 amountOut、gasEstimate、block 和耗时 | 第一版 `quotes.csv` |
| 6 | 60–90 分钟 | 两个池在同一状态下是否存在可执行差异？ | 同一 blockTag、同一方向和同一规模查询两个池；计算 gross spread bps，状态不一致时拒绝比较 | `compare.py` 与一张报价表 |
| 7 | 40–60 分钟 | 第一周的流程能否重复？ | 从空输出目录重新运行 Day 3–6；记录三个最主要错误；删除一个不必要工具或任务 | 第一周复盘与更新后的下一周目标 |

第一周通过条件：无需手工改数据，能在同一 blockTag 下得到两个池、五个规模的可比较报价。

### 第二周：从毛价差到可证伪判断

| Day | 时间 | 今日唯一问题 | 实操与完成条件 | 当日产出 |
| --- | --- | --- | --- | --- |
| 8 | 60 分钟 | 数据是否足以复现？ | 为报价增加 block hash、请求/响应时间、方向、原始单位、decimals 和 error；写 3 个数据校验 | schema 说明与测试 |
| 9 | 60 分钟 | 毛价差扣完已知成本还剩多少？ | 加入两腿池费、Gas 估计和保守安全余量；输出乐观、基准、保守三种情景 | `cost-model.md` 与计算函数 |
| 10 | 60–90 分钟 | 系统应在何时拒绝候选？ | 为 block mismatch、quote stale、net edge ≤ 0、异常 decimals 和 RPC error 添加 reason code | 候选检测器与测试 |
| 11 | 60–75 分钟 | 真实 Swap 事件提供了哪些证据？ | 用 `eth_getLogs` 抓一个池的一小段 Swap 日志；解码区块、交易、amount、tick 和 liquidity | `swaps.csv`，不追求大样本 |
| 12 | 60–90 分钟 | 一笔真实交易为什么改变了池状态？ | 从 Day 11 选择一笔交易，核对交易、回执、日志和前后状态；区分观察事实与估算 | `case-study.md` 初稿 |
| 13 | 60–90 分钟 | 相同状态能否得到相同结论？ | 使用 Anvil 或支持历史状态的 RPC 固定区块，重跑一次报价与检测；若公共 RPC 不支持，记录限制并固定最近区块 | 回放命令、输入和输出 |
| 14 | 40–60 分钟 | 当前假设值得继续吗？ | 汇总错误、负样本和未计成本；明确否定或保留“两个费率池存在可捕获净差异”这一假设 | 一页 Go / No-Go 中期判断 |

第二周通过条件：至少有一个候选被明确拒绝，并能用数据说明拒绝原因；“没有机会”也是合格结果。

### 第三周：从实验到独立研究与 AI 工作方式

| Day | 时间 | 今日唯一问题 | 实操与完成条件 | 当日产出 |
| --- | --- | --- | --- | --- |
| 15 | 60–75 分钟 | 差异是偶然快照还是重复现象？ | 分时运行报价脚本，累计至少 20 个时间点；不要为了数量牺牲 block 和错误字段 | 完整 `quotes.csv/parquet` |
| 16 | 60–90 分钟 | 候选差异的频率、规模和持续性如何？ | 按规模和方向统计 gross/net edge 分布、正值比例和连续出现次数；不外推真实 PnL | 一张图、一张表、三条结论 |
| 17 | 60 分钟 | 即使净值为正，我有机会捕获吗？ | 阅读 Ethereum MEV 与 Arbitrum Timeboost 官方资料；把排序、200ms 延迟和竞争条件加入判断 | `execution-reality.md` |
| 18 | 60 分钟 | 跨链最佳报价是否等于套利机会？ | 用 LI.FI API 查询同一资产和规模的两个跨链 route；拆出桥、DEX、Gas、预计时间和最小到账，不发送交易 | 一页跨链反例笔记 |
| 19 | 60–75 分钟 | Hermes 是否解决现有工作方式没有解决的问题？ | 用同一任务比较 Hermes 与当前 agent：读取一个链接、生成研究卡、保存结论。安装或配置超过 60 分钟即停止 | `ai-workflow.md` 与保留/放弃结论 |
| 20 | 60–90 分钟 | 新环境能否一次运行全部研究步骤？ | 整理一个命令完成读取、报价、成本、检测和报告；让第二个 Coding Agent 只审查可复现性与风险 | README、命令和测试结果 |
| 21 | 60–90 分钟 | 下一阶段唯一值得继续的方向是什么？ | 演示完整流程；按能力模型逐项验收；写两页以内最终报告，只保留一个 30 天研究方向 | `final-report.md` 与最终打卡 |

第三周通过条件：最终报告能明确回答“发现了什么、为什么可能成立、为什么可能无法捕获、下一步做什么或为什么停止”。

## 未来五天的启动计划

### Day 1：范围与链状态

- 15 分钟：读共学说明与 Ethereum MEV 官方页面，写下“不以 21 天盈利为目标”。
- 15 分钟：调用公共 RPC，确认 `eth_chainId = 0xa4b1`（42161），读取最新区块。
- 20 分钟：完成 `research-charter.md`。
- 10 分钟：按打卡模板记录证据。

完成条件：文件中只有一条链、一个交易对、两个池和一个活动假设。

### Day 2：AMM 与规模

- 15 分钟：只读 Uniswap 集中流动性说明。
- 30 分钟：写常数乘积基线并生成五个规模的结果。
- 15 分钟：写出“为什么屏幕价格不能用于套利判断”。

完成条件：有可运行函数和一张规模—价格曲线。

### Day 3：状态与时间

- 10 分钟：确认 RPC 返回字段。
- 40 分钟：保存 10 次区块快照，并加入本地请求时间。
- 10 分钟：解释 block number、hash 和 timestamp 各自解决什么问题。

完成条件：每行数据都能定位到一个具体区块。

### Day 4：真实池状态

- 15 分钟：核对 Uniswap、Circle 和 Arbitrum 官方地址。
- 35 分钟：从 Factory 查询两个池，并以同一 blockTag 读取池状态。
- 10 分钟：检查 token 顺序与 decimals。

完成条件：地址不是从博客复制，且两个池的返回值可以追溯到区块。

### Day 5：第一张报价面

- 15 分钟：阅读 QuoterV2 官方示例。
- 35 分钟：查询一个池、一个方向、五个规模。
- 10 分钟：检查 amount 单位、耗时与异常。

完成条件：得到第一版 `quotes.csv`，即使查询失败也保存 error。

## 现在立刻开始：20 分钟

不要先安装 Hermes、数据库或完整 Foundry 环境。先验证链连接：

```bash
mkdir -p lab/data lab/notes

curl -s https://arb1.arbitrum.io/rpc \
  -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}'

curl -s https://arb1.arbitrum.io/rpc \
  -H 'content-type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}'
```

随后把下面这段任务交给今天选定的一个 Coding Agent：

```text
在当前仓库创建一个最小 Python 脚本，只读取 Arbitrum One。
要求：
1. 调用 eth_chainId 和 eth_getBlockByNumber；
2. 输出 chain_id、block_number、block_hash、block_timestamp、received_at；
3. 结果追加到 lab/data/blocks.jsonl；
4. RPC URL 从环境变量读取，但允许使用官方公共 RPC 作为开发默认值；
5. 不接收私钥，不发送交易，不增加数据库和 Web 服务；
6. 提供一个单元测试和一条运行命令。
完成后解释每个字段为什么是后续报价可比性的必要条件。
```

今天做到脚本能运行并产生一行数据就停止。

## 打卡模板

```markdown
# Day __ / 日期

今日唯一问题：
用时：

一手资料：
- 链接：
- 使用的事实：

实际动作：
- 命令、代码或查询：

证据：
- 文件、区块、交易哈希、图表或测试：

结论：
- 支持 / 否定 / 暂时无法判断：
- 原因：

卡点：

明日唯一动作：
```

一次有效打卡只要求四项：有问题、有动作、有证据、有下一步。不要用长篇笔记代替实验。

## 调整规则

| 现象 | 立即调整 |
| --- | --- |
| Day 5 仍无法取得报价 | Day 6–7 只检查地址、ABI、token 顺序、decimals 和 blockTag，不进入成本模型 |
| 超过 20% 的比较来自不同区块 | 暂停机会分析，先修复状态绑定和数据校验 |
| 加入保守成本后所有候选为负 | 保留代码和数据，将假设标记为 No-Go；Day 14 前不换交易对 |
| 无法固定区块重复结果 | 不讨论策略收益，先记录 RPC 或历史状态能力限制 |
| 连续两天只有阅读 | 下一天禁止读新资料，只完成一个查询、函数或图表 |
| Hermes 安装或配置超过 60 分钟 | 本期停止探索，继续使用 Codex/Claude Code |
| 漏打卡一天 | 不补双倍任务，继续下一个实验，并在周复盘说明缺口 |
| 想增加新链、协议或策略 | 写入 `parking-lot.md`，Day 21 后再评估 |

## 一手资料与可靠性

访问日期均为 2026-08-04。协议行为、部署地址和产品能力优先使用项目官方文档或官方代码；动态状态再用链上查询核验。

### 本地课程资料

- [链上套利残酷共学页面快照](./残酷共学｜链上套利残酷共学.pdf)：用于确认 21 天周期、课程目标、打卡方式和风险边界。
- [发起人的学习大纲](./套利共学｜为什么我在熊市发起链上套利残酷共学？顺便分享下我的学习大纲.pdf)：用于理解“先基础、再案例、最后选择方向”的原始意图。它是个人经验，不用于证明协议事实或盈利概率。
- [Hermes Agent Setup 与学习 Prompt](./套利共学｜从零配置一个链上套利辅助和学习的 Hermes Agent：我的 Setup、硬件、模型和学习 Prompt.pdf)：支持“已有 Codex/Claude 时先用现有工具、计划滚动调整、缺什么再装什么”的取舍。

### 在线一手资料

- [课程官方页面](https://intensivecolearn.ing/programs/b43d2e97-ed88-4ca3-b12f-7ef672b01205)：课程周期、面向人群和风险说明；报名人数等动态字段会变化。
- [Ethereum：MEV](https://ethereum.org/developers/docs/mev/)：说明 DEX 套利的原子性、searcher 竞争和新参与者面对的现实。
- [Arbitrum chain information](https://docs.arbitrum.io/for-devs/dev-tools-and-resources/chain-info)：官方 RPC、chain ID、sequencer endpoint 和公共 RPC 无 SLA 的限制。
- [Arbitrum：How Timeboost works](https://docs.arbitrum.io/how-arbitrum-works/timeboost/gentle-introduction)：说明 express lane、60 秒 round 和普通交易默认 200ms 延迟。
- [Uniswap：Concentrated Liquidity](https://developers.uniswap.org/docs/get-started/concepts/liquidity-providers/concentrated-liquidity)：理解活动流动性、tick 和规模相关成交价格。
- [Uniswap v3：Getting a Quote](https://developers.uniswap.org/docs/sdks/v3/guides/swapping/quoting)：Quoter/QuoterV2 的参数、返回值和只读模拟方式。
- [Uniswap v3 Arbitrum Deployments](https://developers.uniswap.org/docs/protocols/v3/deployments/v3-arbitrum-deployments)：Factory、QuoterV2、WETH 和其他官方部署地址。
- [Circle：USDC contract addresses](https://developers.circle.com/stablecoins/usdc-contract-addresses)：Arbitrum 原生 USDC 地址和主网资产风险提示。
- [Foundry：Anvil](https://www.getfoundry.sh/anvil/index.html)：固定 EVM 链状态、fork 和 trace；默认测试助记词绝不能用于真实资产。
- [LI.FI OpenAPI](https://docs.li.fi/api-reference/openapi-spec) 与 [Quote vs Route](https://docs.li.fi/introduction/user-flows-and-examples/difference-between-quote-and-route)：跨链报价、route 的多步骤性质和 API 能力。聚合器返回的最佳 route 不是个人套利优势。
- [Hermes Agent 官方仓库](https://github.com/NousResearch/hermes-agent) 与 [安全策略](https://github.com/NousResearch/hermes-agent/security)：Hermes 提供长期记忆、技能和定时任务；官方同时明确只有操作系统隔离才是真正的安全边界，因此本期不接入钱包私钥或无人值守交易。

## Day 21 的最终问题

最终报告只回答以下六个问题：

1. 两个池的可执行报价在什么规模和状态下出现差异？
2. 扣除已知成本后，候选是否仍为正？
3. 数据、成本或执行假设中，哪一项最容易让结果失效？
4. Timeboost 和竞争条件是否使普通参与者难以捕获该信号？
5. 这 21 天真正增加的是哪一种能力：数据、模型、研究判断还是工程可靠性？
6. 下一阶段唯一继续方向是什么；如果没有，为什么停止？

二十一天结束时，能够可靠地否定一个伪机会，比写出一个未经验证的 Bot 更有价值。
