# 21 天高密度永续套利研究课程（v6）

> 版本：2026-08-11
>
> 研究主线：Lighter `WTI`（`market_id=145`）与 `BRENTOIL`（`market_id=159`）RWA 永续相对价值；迁移到 Binance USDⓈ-M 和 Hyperliquid 的公共市场数据。
>
> 课程定位：不是“21 天找到盈利策略”，而是用一个深案例建立可迁移的研究、执行和风险能力，并在证据不足时能够明确拒绝交易。
>
> 时间预算：每天 30–90 分钟，默认 60 分钟。每个学习日只要求一个可运行、可解释、可复查的研究产出；连续两天无法完成时，缩小任务，不降低验收标准。

## 1. 为什么重排

用户已经具备 Python、REST、WebSocket、Git、依赖管理和基本金融/衍生品知识，因此课程不再把时间花在通用编程语法上。主要补齐四类能力：

1. **市场机制**：永续、RWA 期货展期、oracle、index、mark、funding、保证金、清算和订单类型；
2. **研究工程**：可复现采集、时间语义、原始证据、数据质量、限流、断线恢复和版本化；
3. **执行经济学**：bid/ask、盘口走档、VWAP、冲击、延迟、部分成交、单腿风险和净现金账本；
4. **跨场所迁移**：把 Lighter 的深度理解迁移到 CEX 和链上永续，而不是把 RWA 特有规则误认为所有市场都如此。

当前课程的问题不是内容完全错误，而是**能力出现顺序不合理**：前七天集中解释一个场所的字段，盘口、成交、延迟、持续采集和现金回放出现得太晚；选择题可以让人感觉“做过了”，却不能证明能运行、修改和迁移研究代码。

因此 v6 采用：

```text
一个深案例 + 两个迁移案例
机制与数据并行 + 执行尽早出现 + 每 2–3 天形成可复用组件
```

## 2. 学习、研究、交易三条状态线

三种状态必须分开记录：

```text
学习状态：能解释 → 能运行 → 能复现 → 能修改 → 能迁移
研究状态：资料足够继续验证 / 暂时不成立 / 关键资料缺失
交易状态：No-Go / Paper-only / Supervised experiment / Live
```

### 2.1 学习目标

课程结束时，用户应能：

- 读官方市场规格和 API 文档，给每个字段写出语义、单位、时间戳和证据等级；
- 从公开 API 采集并保存原始响应、参数、HTTP 状态、请求/接收时间和哈希；
- 处理分页、窗口上限、重复、缺失、零值、异常跳点和跨源时间对齐；
- 把盘口快照转换为目标数量的可执行价格、VWAP、滑点、余量和未对冲暴露；
- 把成交、手续费、funding、保证金和清算准备金进入逐笔现金账本；
- 在训练/验证/测试切分下预先写检验计划，避免全样本回看和阈值泄漏；
- 把同一任务迁移到另一个交易场所，并指出哪些字段不能直接类比；
- 面对正相关、正 funding 或一次漂亮回放时，仍能说明它不能证明什么。

### 2.2 研究目标

研究结论只有以下三种，不允许用“看起来不错”作为第四种：

- **资料足够继续验证**：语义、历史、执行和风险仍有可补齐路径；
- **暂时不成立**：样本外关系不稳定，或压力成本下净现金明确为负；
- **关键资料缺失**：无法把信号映射为可执行、可退出、可核验的净现金。

当前仓库的研究状态仍为 `Blocked / No-Go`。现有约 500 根 1h candle、约 750 条 funding 和描述性相关性只能支持继续审计，不能支持协整、盈利或实盘结论。

### 2.3 交易边界

前 21 天：

- 研究资金为 `$0`；
- 不连接私钥，不保存凭据，不签名，不发真实订单；
- EVM 只做 RPC、ABI、事件、余额、池子状态和报价的只读练习；
- 不把 HTML 课程完成、统计相关性、纸上 PnL 或平台打卡写成交易成果；
- 未知字段保留 `unknown`，不默认填零、不用插值伪造成交或价格。

## 3. 每日学习协议

每天固定执行以下五步，内容可以变，证据结构不变：

1. **闭卷起点（5 分钟）**：不看资料，用自己的话回答今天要解决的问题；
2. **一手输入（10–20 分钟）**：只读官方文档、原始 API 响应和仓库代码；
3. **真实动作（20–40 分钟）**：运行命令、改一个参数、注入一个故障或完成一次回放；
4. **迁移回忆（5–10 分钟）**：换市场、方向、时间状态或故障，重新解释；
5. **留证（5 分钟）**：保存产出路径、测试结果、未知项和下一步。

每一天的通过证据至少包括：

- 一段闭卷解释；
- 一个真实命令或测试输出；
- 一个可复查文件；
- 一个故障/边界或迁移场景；
- 一条“不能据此得出什么”的限制说明。

HTML 仅用于图示、模拟器和即时反馈。选择题不能替代命令运行、代码修改、数据审计和迁移验收。浏览器 lesson 必须同时有 DOM smoke test；Python 研究逻辑必须有单元测试。

## 4. 三阶段和四道闸门

```text
Day 1–7   深案例：研究边界、合约、价格、展期、funding、数据质量
Day 8–14  执行核心：跨场所 schema、盘口走档、成交、双腿状态、净现金、统计
Day 15–21 广度与基础设施：CEX/链上迁移、EVM 只读、库存、风险、采集、答辩
```

### Gate A｜Day 7：数据能不能进入研究

必须能回答：每一行来自哪里、代表哪个时间、为什么被保留/标记、是否可以回到原始响应。不能回答则不进入统计。

### Gate B｜Day 14：信号能不能变成净现金

必须能对目标规模完成双腿开仓和退出回放，包含盘口方向、手续费、funding、延迟、部分成交和单腿失败。不能回答则保持 `Paper-only / Blocked`。

### Gate C｜Day 19：方法能不能迁移和持续运行

必须至少在另一个 CEX 和一个链上永续场所完成只读采集，指出时间、精度、限流、market schema 和 funding 语义差异。

### Gate D｜Day 21：是否值得进入下一周期

只产生下一周期研究决策，不自动授权资金。决策必须附证据索引、已知未知项、压力结果和停止条件。

## 5. Day 1–7：Lighter 深案例

### Day 1｜把候选从“套利”改写成可证伪研究问题

**核心问题**：WTI/BRENTOIL 到底是什么关系？什么观察不算机会？

**输入**：`MISSION.md`、`notes/research-charter.md`、Lighter RWA 总览和市场规格。

**动作**：

- 区分同场所跨品种相对价值、跨场所 basis/funding carry 和无风险套利；
- 为两腿写出经济对象、结算、数量、价格、funding、深度、权限和退出字段；
- 写出至少 8 个当前未知项，并为每个未知项标注“会影响信号、执行还是风险”；
- 写下拒绝规则：历史不足、语义未知、成本未闭合、单腿无法退出时分别如何停止。

**产出**：`notes/research-charter.md`、`learning-records/0001-rwa-perpetual-relative-value-boundary.md`。

**通过**：不看资料能解释为什么“价格相关”不等于“可套利”；能说出一个正确信号也可能被什么成本吞掉。

### Day 2｜先建立可复现采集，而不是先看图

**核心问题**：现有数字来自哪里，窗口上限和响应缺失意味着什么？

**输入**：Lighter Candles/Fundings API、现有 `lab/capture_lighter_rwa.py`、原始 JSON。

**动作**：

```bash
python3 lab/capture_lighter_rwa.py
python3 lab/audit_lighter_rwa.py
python3 -m json.tool lab/data/lighter_rwa_capture_manifest.json >/dev/null
python3 -m json.tool lab/data/lighter_rwa_data_audit.json >/dev/null
```

保存 URL、参数、状态码、请求/接收时间、延迟、原始文件和 SHA-256；不要保存 token/header。

**产出**：manifest、audit、`lab/data/lighter_rwa_aligned_1h.jsonl`、`notes/day-1.md`。

**通过**：从 audit 任一数字回到原始响应和采集元数据；能解释单次 500 candle/750 funding 窗口为什么不能支持长期结论。

### Day 3｜合同和数量模型

**核心问题**：价格接近是否意味着数量、乘数和保证金可以 1:1？

**输入**：RWA Market Specifications、Contract Specifications、`orderBookDetails` 原始快照。

**动作**：

- 做 WTI/BRENTOIL 字段字典：market id、经济对象、最小基础数量、最小报价金额、价格/数量精度、乘数、保证金字段；
- 用 `$10/$20/$50/$100` 目标报价金额分别计算理论数量和余量；
- 区分静态规格、动态快照、账户成交三种证据；
- 给数量检查加测试，拒绝硬编码精度。

**产出**：`notes/rwa-contract-model.md`、字段字典、数量测试。

**通过**：能解释“名义金额相同”与“基础数量相同”的差别；至少指出 3 个必须通过账户/成交回执核验的字段。

### Day 4｜oracle、index、mark、mid 和成交价

**核心问题**：API 返回的每个价格是否代表同一过程？

**输入**：RWA Pricing Mechanism、Fair Price Marking、PnL 文档。

**动作**：画出并在代码字段中实现：

```text
外部 oracle → index / mark
订单簿 impact price → mark / EMA
trade price / candle close → 观察数据
best bid / best ask / mid → 估计可执行区间
```

增加 `source_timestamp`、`received_at`、`price_semantics`、`oracle_state`；构造 oracle stale 时的反例。

**产出**：`notes/price-semantics.md`、价格字段字典和一个反例 fixture。

**通过**：能解释 mark 用于估值/清算和 bid/ask 用于现金退出不是同一件事；缺失字段保持 `unknown`。

### Day 5｜展期、时区和市场状态

**核心问题**：价差变化来自相对价值，还是来自两个底层期货的不同展期/关闭窗口？

**输入**：Futures Contract Price Rolling Mechanism、RWA 规格和现有时间数据。

**动作**：

- 所有源数据内部统一 UTC，展示时转换为 America/New_York；
- 建立 `wti_roll_window`、`brentoil_roll_window`、`market_closed_window`、`oracle_state`；
- 比较全样本、排除展期、按展期阶段分层的结果；
- 不因异常直接删除样本，先保留并标记来源和状态。

**产出**：`notes/rwa-roll-and-session-model.md`、状态表和时间切分测试。

**通过**：能用一个具体小时解释状态标签如何改变研究含义；能指出时间错位会怎样制造结构断点。

### Day 6｜把 funding 变成现金账本

**核心问题**：公开 funding rate 如何、以及不能如何进入个人净收益？

**输入**：Lighter Funding 文档、Fundings API、现有 `lab/day6_funding_ledger.py`。

**动作**：

- 建立 `timestamp/rate/value/direction/position_sign/quantity/multiplier/settlement_price/cash_flow`；
- 分别演算 WTI/BRENTOIL 多空四种场景；
- 明确 `API value`、公开市场 funding 和账户 funding ledger 的证据等级；
- 为 `unknown` 单位、方向或结算状态写失败测试。

**产出**：`notes/funding-ledger-model.md`、纸上 ledger、测试。

**通过**：能由仓位方向推出付款/收款方向；能说明为什么不能直接相减两条 API `value` 当个人收益。

### Day 7｜数据清洗、异常和 Gate A

**核心问题**：哪些样本可以进入统计，哪些样本必须保留为异常证据？

**输入**：原始 candles/fundings、API 文档、现有 Day 7 lesson 和清洗脚本。

**动作**：

- 统一 UTC，检查重复 timestamp、缺失小时、零值、非正价格和跳点；
- 保存原始值、清洗状态、质量标记，不覆盖原始 JSON；
- 按时间顺序划分 train/validation/test；
- 在浏览器中完成交互验收，再运行 Python 实验和测试；
- 人为注入一条缺失、重复或异常记录，确认规则不会静默删除。

**产出**：`lab/data/lighter_rwa_clean_1h.csv`、`notes/data-quality-report.md`、Day 7 学习记录。

**通过**：5/5 迁移验收 + Python 测试通过；能从清洗表任意一行回到原始响应；能说明为什么“缺失=0”是危险的。

**当前状态**：Day 7 JavaScript 已修复并在浏览器回归验证；用户需要重新完成迁移验收，不能把 lesson 加载成功等同于 Day 7 学习完成。

## 6. Day 8–14：执行核心和样本外纪律

### Day 8｜统一跨场所数据结构

**核心问题**：怎样把 Lighter、Binance 和 Hyperliquid 的数据放进同一研究表，而不抹掉语义差异？

**输入**：Lighter API、Binance Exchange Information/Order Book、Hyperliquid Info 文档。

**动作**：设计最小 schema：

```text
venue, market, instrument_type, source_timestamp, received_at,
price_semantics, bid, ask, size, funding_rate, funding_timestamp,
precision, quality_flags, raw_ref
```

完成一份 Lighter → Binance 字段映射，并标出 `not_equivalent` 字段；禁止把不存在的字段补成 0。

**产出**：`notes/venue-schema.md`、schema 校验和两个 venue fixture。

**通过**：能指出至少 5 个“同名但不可直接类比”的字段或限制。

**当前状态**：Day 8 已于 2026-08-11 完成。真实抓取 13 个公开响应（含 2 个 400 失败样本）；`lab/venue_schema.py` 输出 333 行统一长表，7 个 not_equivalent 字段；验收 5/5、测试 29/29。用户需要完成浏览器迁移验收后进入 Day 9。

### Day 9｜盘口走档和目标数量执行成本

**核心问题**：屏幕价差扣除真实双腿进出成本后还剩多少？

**输入**：Order Book/Order Book Orders、Trading Fees、Order Types 文档。

**动作**：对 `$10/$20/$50/$100` 分别：

- 买入走 ask，卖出走 bid；
- 多档累计，计算 VWAP、spread、冲击、余量和未对冲名义；
- 分开开仓与平仓；
- 比较 midpoint、top-of-book 和走档结果；
- 将 maker/taker 显式费用和非显式排队/延迟成本分开。

**产出**：`lab/orderbook_walk.py`、`notes/execution-replay.md`、fixture 和测试。

**通过**：不能用 midpoint 冒充成交；能解释目标规模翻倍为何不一定只让成本翻倍。

### Day 10｜成交、延迟和报价是否真的可成交

**核心问题**：报价出现过，是否等于订单能以该价成交？

**输入**：公开 recent trades、账户 trades 文档、WebSocket 事件文档。

**动作**：将一段盘口快照和成交序列配对，记录：

```text
quote_time, receive_time, decision_time, submit_time,
fill_time, side, requested_qty, filled_qty, remaining_qty,
price, fee, stale_ms, reject_reason
```

对比“看见盘口”“市场发生成交”“我的订单成交”三个证据等级。

**产出**：`notes/quote-vs-fill.md`、延迟/成交 fixture。

**通过**：能给出一个 stale quote、部分成交和未成交的处理方式；不把 recent trades 当自己的 fill。

### Day 11｜双腿执行状态机和单腿失败

**核心问题**：两腿不同步时，系统的下一步是什么？

**输入**：订单类型、reduce-only、订单事件/失败状态文档。

**动作**：实现状态机：

```text
FLAT → LEG_A_SUBMITTED → LEG_A_FILLED
     → LEG_B_SUBMITTED → HEDGED
     → PARTIAL / STALE / REJECTED / EXITING
```

为每个状态写：允许动作、最大等待时间、取消/退出动作、残余暴露和日志字段。

**产出**：`notes/execution-state-machine.md`、状态转换测试、故障注入结果。

**通过**：模拟 B 腿拒单、A 腿部分成交、行情过期和退出失败；能说出 kill switch 触发条件。

### Day 12｜净现金账本、保证金和清算压力

**核心问题**：相对价值交易怎样从“价差”变成逐笔现金结果？

**输入**：Funding、PnL、Liquidations/LLP、Multi-Asset Margin、交易费用文档。

**动作**：建立逐事件账本：

```text
cash_pnl = trade_pnl + funding_cash - fees - slippage
           - transfer_or_borrow_cost - risk_reserve
```

分别记录 mark-to-market、可退出现金、保证金占用、单腿暴露和清算距离；未知项不填零。

**产出**：`lab/cash_ledger.py`、`notes/net-cash-model.md`、压力测试。

**通过**：能解释为什么两腿名义对冲仍可能因乘数、mark、保证金、资金转移或清算而亏损。

### Day 13｜价差定义：固定差、比率、log spread、beta

**核心问题**：研究对象是哪个可证伪的 spread，而不是哪个公式看起来最好？

**输入**：已清洗数据、研究章程、统计方法说明。

**动作**：先写计划再算结果：

- 固定美元差；
- 价格比率；
- 对数差；
- 仅用训练集估计 beta 的动态 spread；
- 记录每种定义的经济解释、单位、触发条件和失败条件。

**产出**：`notes/spread-definition-decision.md`、统计模块测试。

**通过**：能解释相关性、协整、可交易性三者的区别；不能因为一个定义结果最好就自动选它。

### Day 14｜时间切分、参数冻结和 Gate B

**核心问题**：怎样避免用未来信息选择过去的策略？

**输入**：Day 7 清洗数据、Day 9–12 执行模块。

**动作**：固定：

```text
train → 选择定义/窗口/阈值
validation → 检查稳定性和成本敏感性
test → 只做一次冻结参数的样本外回放
```

在测试区间只输出触发次数、持有时间、双腿成交、费用、funding、滑点、未对冲暴露和净现金，不再调参。

**产出**：`notes/gate-1-execution-statistics.md`、冻结参数文件、结果表。

**通过**：至少完成一个方向、一个目标规模的开仓/平仓回放；在延迟、滑点和部分成交压力下仍明确写出 `continue / reject / insufficient evidence`。

## 7. Day 15–21：广度、基础设施和研究答辩

### Day 15｜Binance 永续迁移

**核心问题**：同一研究动作换到高流动性 CEX 后，哪些东西能复用，哪些必须重写？

**输入**：Binance USDⓈ-M Exchange Information、Funding Rate History、Order Book、Recent Trades 官方文档。

**动作**：

- 只读采集 BTCUSDT 的市场规格、funding、盘口和成交；
- 将数据适配到 Day 8 schema；
- 比较 precision、rate limit、funding 时间、盘口字段和成交证据；
- 用同一 `$10/$20/$50/$100` 目标名义走档。

**产出**：`notes/binance-migration.md`、`lab/venue_adapters/binance_public.py` 或等价只读脚本、对比表。

**通过**：不改动执行核心逻辑就能替换数据源；能列出至少 3 个不能从 Lighter 直接复制的假设。

### Day 16｜Hyperliquid 永续迁移与 REST/WebSocket 一致性

**核心问题**：链上永续的公开信息接口与 CEX 接口有何不同？

**输入**：Hyperliquid Info Endpoint、WebSocket 官方文档。

**动作**：

- 只读获取 meta、盘口、成交、candle 或 funding 相关公开数据；
- 用 REST 快照和 WebSocket 事件做时间/字段一致性检查；
- 记录订阅、重连、消息顺序和数据缺口；
- 不写签名、下单或钱包连接代码。

**产出**：`notes/hyperliquid-migration.md`、只读采集脚本、原始响应和质量报告。

**通过**：能解释“链上场所”不自动等于“低风险”或“无需执行工程”；能指出数据延迟、资金、清算和跨场所转移风险。

### Day 17｜CEX–DEX inventory / basis 研究模型

**核心问题**：跨场所套利的真正成本除了交易费还包括什么？

**输入**：前 16 天净现金账本、公开 venue 规格、用户的风险预算约束。

**动作**：只做纸上场景，不转账：

- 预置库存与临时转移两种路径；
- 加入借贷/资金占用、转账确认、充值提现暂停、链上 gas、对手方和清算风险；
- 对“价差存在但库存位置不对”和“资金费反转”做情景树；
- 将 gross edge、net edge、capital at risk 分开。

**产出**：`notes/cex-dex-inventory-model.md`、至少两个库存场景、拒绝条件表。

**通过**：能说明为什么价差扫描器上的 APY 不能直接等于个人收益；能给出资金位置和退出路径。

### Day 18｜WebSocket 采集器的可靠性

**核心问题**：持续数据系统如何在断线、限流、重复和乱序下保持可审计？

**输入**：Lighter、Binance、Hyperliquid WebSocket/Rate Limits 官方文档。

**动作**：实现或补齐：

- 订阅确认和心跳；
- reconnect/backoff；
- 原始事件 append-only 落盘；
- source timestamp 与 received_at；
- 去重键、乱序检测、断点、每日 manifest 和哈希；
- 断线/限流/订阅失败故障注入。

**产出**：采集器日志、事件 fixture、`notes/collector-reliability.md`、重启演练报告。

**通过**：人为断开后能恢复且不静默丢失；能定位一个事件来自哪次连接、何时收到、是否重复。

### Day 19｜压力回放和风险故障演练

**核心问题**：策略在最不舒服的执行条件下是否仍然可退出？

**输入**：Day 11–18 所有模块和风险文档。

**动作**：至少演练：

1. bid/ask 扩大；
2. 盘口深度骤减；
3. B 腿拒单；
4. 一腿部分成交；
5. oracle stale / mark 过程切换；
6. funding 方向反转；
7. WebSocket 断线；
8. 保证金接近清算。

每个场景输出残余暴露、退出动作、最大损失假设、日志证据和是否停止研究。

**产出**：`notes/risk-and-operations.md`、故障注入测试、压力结果表。

**通过**：每个故障都有明确状态、动作、超时和人工介入点；不存在“继续等一等”这种无界处理。

### Day 20｜冻结参数的最终纸上回放和 Gate C/D 预审

**核心问题**：在没有新增调参的前提下，证据是否足以进入下一周期？

**动作**：

- 冻结所有训练参数、成本假设和目标规模；
- 在完全未使用的时间区间做一次最终回放；
- 输出 gross spread、显式费用、盘口成本、funding、延迟损失、风险准备金和 net cash；
- 对 Lighter、Binance、Hyperliquid 分别标出 `confirmed / partial / unknown`；
- 选择下一周期唯一研究问题。

**产出**：`notes/final-paper-replay.md`、结果 CSV、证据索引、`notes/next-cycle-decision.md`。

**通过**：第三方只看仓库即可重建输入、参数、结果和限制；若资料缺失，结论必须是 `Blocked / insufficient evidence`，不是正收益叙事。

### Day 21｜答辩、复盘和下一周期

**闭卷答辩**：

1. 为什么一个高相关性序列仍可能不可交易？
2. `mark price`、`mid price`、bid/ask 和退出现金分别用于什么？
3. 正 funding 对多空双方的现金流方向是什么？还缺什么才算个人收益？
4. 目标规模增加时，哪些成本非线性增长？
5. 双腿不同时成交，状态机如何处理？
6. Lighter 的 RWA 展期规则哪些不能迁移到 Binance/Hyperliquid？
7. 哪些证据会让你拒绝继续，哪些只会让你继续采集？
8. 当前交易状态为什么是 `No-Go`、`Paper-only` 或其他值？

**最终产出**：

- 学习能力清单：能解释、运行、复现、修改、迁移的内容；
- 研究结论：继续验证、暂时不成立或关键资料缺失；
- 证据索引：原始文件、脚本、测试、时间范围和版本；
- 失败记录：包括被否定的假设和未完成的路径；
- 下一周期唯一研究问题与停止条件。

**通过**：不要求得出盈利结论；要求能诚实、可复查地解释结论边界。

## 8. 练习和验收的重设计

### 保留的内容

- Lighter WTI/BRENTOIL 作为深案例；
- 合约规格、价格语义、展期、funding、清洗和时间切分；
- 研究、学习和交易状态分开；
- 真实数据、原始文件、测试和证据路径；
- HTML 的图示和即时反馈。

### 删除或降级的内容

- 只识别定义的连续选择题；
- 没有真实输入/输出的伪代码练习；
- 在短样本上反复计算相关性并暗示策略方向；
- 把 midpoint、24h volume、公开 funding value 或网页 APY 当作可交易收益；
- Day 10 之后完全空白、等证据再临时设计的课程安排。

### 新的验收权重

每个阶段按以下证据评估，而不是按看完页面评估：

| 证据 | 权重 | 说明 |
|---|---:|---|
| 机制解释 | 20% | 闭卷说明单位、方向、时间和限制 |
| 代码运行/修改 | 25% | 命令、测试、参数修改或故障注入 |
| 数据审计 | 20% | 原始响应、质量标记、时间对齐和可追溯性 |
| 执行/现金回放 | 25% | 盘口方向、双腿状态、费用、funding、净现金 |
| 迁移与拒绝结论 | 10% | 换场所/故障后仍能说明边界 |

权重不是“刷分”规则；关键安全错误（错误方向成交、静默删除数据、把未知填零、把纸上收益写成实盘收益）直接判该任务不通过，即使其他题答对。

## 9. 现有仓库映射

- 主计划：本文件 `resource/plan.md`；
- 研究依据：`notes/course-redesign-primary-sources.md`；
- 资源索引：`RESOURCES.md`；
- 课程状态：`notes/icl-course-outline.md`、`NOTES.md`；
- Day 1–7 lesson/reference/assets/lab：继续复用，但把每个 HTML 的唯一验收接到命令、测试和迁移任务；
- `notes/course-redesign-primary-sources.md`：已核验的官方文档/API 与学习科学原始研究映射；
- 下一项实际教学动作：用户完成 Day 8 浏览器迁移验收（验收题 5/5）后进入 Day 9 盘口走档；不重复讲 Day 1–7 的定义。

## 10. 主要一手资料

交易所和协议机制以其官方文档/API 为准：

- [Lighter RWA 总览](https://docs.lighter.xyz/trading/real-world-assets-rwas)
- [Lighter RWA Pricing Mechanism](https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism)
- [Lighter Futures Contract Price Rolling Mechanism](https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism)
- [Lighter RWA Market Specifications](https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications)
- [Lighter Funding](https://docs.lighter.xyz/trading/funding)
- [Lighter Trading Fees](https://docs.lighter.xyz/trading/trading-fees)
- [Lighter Fair Price Marking](https://docs.lighter.xyz/trading/fair-price-marking)
- [Lighter Order Types and Matching](https://docs.lighter.xyz/trading/order-types-and-matching)
- [Lighter Liquidations and LLP Insurance Fund](https://docs.lighter.xyz/trading/liquidations-and-llp-insurance-fund)
- [Lighter Candles API](https://apidocs.lighter.xyz/reference/candles)
- [Lighter Fundings API](https://apidocs.lighter.xyz/reference/fundings)
- [Lighter Order Book Orders API](https://apidocs.lighter.xyz/reference/orderbookorders)
- [Lighter Trades API](https://apidocs.lighter.xyz/reference/trades)
- [Binance USDⓈ-M Exchange Information](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information)
- [Binance USDⓈ-M Funding Rate History](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History)
- [Binance USDⓈ-M Order Book](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Order-Book)
- [Hyperliquid Info Endpoint](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint)
- [Hyperliquid WebSocket](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket)

学习方法依据原始研究记录：

- [Roediger & Karpicke, 2006, PubMed PMID 16507066](https://pubmed.ncbi.nlm.nih.gov/16507066/)
- [Karpicke & Roediger, 2008, PubMed PMID 18276894](https://pubmed.ncbi.nlm.nih.gov/18276894/)
- [Karpicke & Bauernschmidt, 2011, PubMed PMID 21574747](https://pubmed.ncbi.nlm.nih.gov/21574747/)
- [Cepeda et al., 2006, PubMed PMID 16719566](https://pubmed.ncbi.nlm.nih.gov/16719566/)

资料、事实与课程设计的逐项映射见 `notes/course-redesign-primary-sources.md`。动态行情数字必须附抓取时间和原始文件，不能写成稳定规则。
