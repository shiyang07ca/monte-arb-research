# 课程重设计资料与设计决策

> 研究目的：根据用户的学习目标、已有能力和当前仓库证据，重新安排 21 天衍生品套利研究课程。
>
> 研究原则：交易所机制只引用交易所官方文档/API；学习方法只引用论文原始摘要或 PubMed 记录；动态数字只作为抓取时刻的证据，不写成稳定规则。
>
> 研究日期：2026-08-11

## 1. 研究对象和用户约束

用户希望在 1–2 个月内判断真实可执行的套利方向，优先顺序是：

1. CEX–DEX 或不同永续场所之间的 funding / basis / 对冲；
2. 能用 Python、REST、WebSocket、Git 和依赖管理完成采集、回放和排错；
3. 当前不熟悉 EVM、DeFi、智能合约读取；
4. 每天可投入约 30–90 分钟；
5. 研究阶段默认 `$0`，未经单独确认不认证、不连接私钥、不发真实订单。

当前仓库的案例是 Lighter 同一场所内的 WTI（`market_id=145`）与 BRENTOIL（`market_id=159`）RWA 永续相对价值研究。它适合用来学习价格语义、展期、funding、数据审计和执行风险，但不能单独覆盖用户后续要掌握的 CEX–DEX / perp-perp 研究。

## 2. 当前课程的证据和问题

### 2.1 已有内容的优点

- 已经把“学习完成”和“策略成立”分开；
- 已经保留原始 API 响应、采集 manifest、SHA-256 和清洗输出；
- 已经覆盖 RWA 价格源、mark/index、展期、funding 方向、数据质量和时间切分；
- Python 测试目前覆盖 Day 2–7 的主要纯函数边界；全量测试曾实际得到 `22/22` 通过；
- 没有把约 21 天的 500 根小时 candle 或 `0.9709` 的描述性收益相关性写成盈利证明。

### 2.2 需要修正的地方

1. **顺序过于线性，前七天集中在一个 Lighter RWA 案例。** 用户真正要掌握的是可迁移的永续研究能力；当前课程在进入盘口、成交、延迟、连续采集和净现金回放前，已经花了大量时间解释单一案例的字段。
2. **数据采集应当更早成为课程主轴。** 当前 Lighter candle 单次返回最多 500 根，funding 最多 750 条；现有共同小时样本约 21 天。若不尽早构建分页/连续采集，后面的统计课只能在短快照上做示范。
3. **练习多数是识别规则或选择答案，而不是完成研究动作。** 学习者需要更早亲手做：拉取、分页、保存、哈希、回放、走盘口、记录双腿异步和输出拒绝结论。
4. **当前 HTML 验收缺少浏览器回归。** Day 7 的原始脚本把动态选择器写成普通字符串 `"[data-role=${role}]"`，页面初始化抛出 `SyntaxError`，所以分类器和验收按钮都没有绑定。修复后已在浏览器中验证分类器、按钮和得分反馈，并提交为 `55a18c4`；这说明课程组件本身也需要 DOM smoke test，而不能只测 Python。
5. **缺少系统的订单簿、成交、订单类型、延迟、部分成交和单腿失败训练。** 这些因素直接决定屏幕价差是否能变成净现金，而不是附加知识。
6. **统计内容应先建立研究问题和防泄漏纪律，再讲公式。** 相关性、价差、beta、协整和半衰期不能在同一份短样本上随意比较，然后挑一个看起来最好的结果。
7. **缺少跨场所迁移。** Lighter RWA 的展期和 oracle 语义很重要，但用户后续要研究的是 Binance/Hyperliquid 等永续场所；必须安排至少一个 CEX 公共 API 和一个链上永续场所的同一数据任务。

## 3. 一手资料与可确认事实

### 3.1 Lighter 官方机制和 API

| 资料 | 可确认事实 | 课程设计决策 |
|---|---|---|
| [RWA 总览](https://docs.lighter.xyz/trading/real-world-assets-rwas) | RWA 覆盖商品、股票和固定收益；RWA 仍受清算机制影响；文档说明市场结构和保证金模式。 | 先教“产品是什么、如何结算、风险在哪里”，再教信号；RWA 案例不能替代通用永续模型。 |
| [RWA Pricing Mechanism](https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism) | 外部 oracle 是主来源；oracle 失效时逐渐转向内部价格，并在外部价格恢复后收敛。 | 把 `oracle/index/mark/impact/candle/trade` 分成不同字段和不同研究用途；增加 oracle 状态切换的反例练习。 |
| [Futures Contract Price Rolling Mechanism](https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism) | WTI、BRENTOIL 等使用期货底层；价格在到期前从当前月逐步切到下月；两类底层市场关闭时间不同。 | 展期状态是价差研究的事件标签，不是读完规则后就可以忽略的背景；必须在样本和回放中分层。 |
| [Market Specifications](https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications) | RWA 市场规格可能由 Lighter 更新；市场代表的经济对象和字段需要以官方规格为准。 | 把静态规格快照和动态市场观察分开保存，课程验收要求指出字段的更新时间和来源。 |
| [Funding](https://docs.lighter.xyz/trading/funding) | Funding 每个整点发生；正 funding 时多头支付空头，负 funding 时方向相反；费率由 mark/index 和 impact 价格等机制形成。 | 先构建账户现金流账本，再谈 funding carry；`rate/value/direction` 不能直接相减当作个人收益。 |
| [Trading Fees](https://docs.lighter.xyz/trading/trading-fees) | 官方页面列出不同账户类型的 maker/taker 费用和延迟；标准账户的零手续费不等于零 spread、冲击、等待或失败成本。 | 成本模型必须分成显式费用、盘口冲击、延迟、部分成交、资金费和风险准备金。 |
| [Fair Price Marking](https://docs.lighter.xyz/trading/fair-price-marking) | Mark price 由 index 和订单簿 impact price 计算，用于公平估值和清算相关判断。 | 纸上 PnL 必须同时展示 mark 估值和按 bid/ask 退出的现金结果。 |
| [Liquidations and LLP Insurance Fund](https://docs.lighter.xyz/trading/liquidations-and-llp-insurance-fund) | 清算有不同账户健康状态；保证金不足时可能取消挂单、部分清算、全部清算或触发 ADL。 | 风险模块必须包含保证金、清算、单腿剩余暴露和 kill switch；不能把套利视为天然低风险。 |
| [Candles API](https://apidocs.lighter.xyz/reference/candles) | 单次最多返回 500 根 candle；响应中的零值可能被省略。 | 数据工程模块提前到课程前段，练习分页、缺字段与真实 0 的区分；禁止在单次快照上做长期结论。 |
| [Fundings API](https://apidocs.lighter.xyz/reference/fundings) | 每次最多返回 750 条 funding；`count_back`、开始时间等参数影响窗口。 | funding 采集器必须记录参数、源时间、接收时间、分页边界和原始哈希。 |
| [export](https://apidocs.lighter.xyz/reference/export) | 账户 trade/funding export 有 12 个月或 100 万笔等范围约束，且需要账户相关参数。 | 在课程中加入“公开 funding 观察 → 账户账本核验”的证据等级；没有账户回读时保持 `unknown`。 |
| [positionFunding](https://apidocs.lighter.xyz/reference/positionfunding) | 账户持仓 funding 查询涉及账户和认证边界。 | 通过文档解释为什么公开 market funding 不能替代个人账户现金账本；不在课程中索要或保存凭据。 |
| [orderBooks](https://apidocs.lighter.xyz/reference/orderbooks) / [orderBookOrders](https://apidocs.lighter.xyz/reference/orderbookorders) | 市场规格含最小基础数量、最小报价金额、小数位和费用等；盘口端点提供价格/数量档位。 | 练习必须按目标名义走档并记录 VWAP、余量和未对冲暴露，不能用 midpoint 冒充成交。 |
| [recentTrades](https://apidocs.lighter.xyz/reference/recenttrades) / [trades](https://apidocs.lighter.xyz/reference/trades) | 公共成交和账户成交是不同证据；账户成交查询有认证边界。 | 将“看见市场有人成交”和“我的订单成交”分开；成交回放与账户回读分开验收。 |
| [WebSocket Reference](https://apidocs.lighter.xyz/docs/websocket-reference) | WebSocket 支持实时订阅和订单/账户事件；订单状态包含流动性不足、过期、reduce-only、保证金不足等失败状态。 | 课程必须有实时数据订阅、断线重连、事件落盘和失败状态分类练习，而不是只用 REST 快照。 |
| [Rate Limits](https://apidocs.lighter.xyz/docs/rate-limits) | REST 和 WebSocket 都有限流；文档列出订阅数、客户端消息数和账户/地址限制。 | 数据采集脚本需要限流、退避、断点续采和可恢复日志；把限流当成交易基础设施的一部分。 |

### 3.2 其他场所官方公开接口

| 资料 | 可确认事实 | 课程设计决策 |
|---|---|---|
| [Binance USDⓈ-M Get Funding Rate History](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History) | 官方公开接口提供历史 funding rate 查询。 | 用 BTCUSDT 做一个通用 perp funding 采集任务，将方法从 RWA 案例迁移到高流动性永续。 |
| [Binance USDⓈ-M Order Book](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Order-Book) | 官方公开接口提供订单簿快照。 | 用同一目标名义比较盘口深度、价差和走档成本；不把 24h volume 当作可执行容量。 |
| [Binance USDⓈ-M Recent Trades](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Recent-Trades-List) | 官方公开接口提供近期成交。 | 让用户区分盘口报价、实际成交和自己订单的成交证据。 |
| [Binance USDⓈ-M Exchange Information](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information) | 官方接口提供交易规则、精度和限流等市场信息。 | 跨场所研究先读取规格和限制，数量/价格不能硬编码。 |
| [Hyperliquid Info Endpoint](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint) | 官方文档说明时间范围查询存在返回数量限制；永续市场通过 meta、盘口、成交和 candle 等接口读取。 | 选一个链上永续场所做迁移任务，重点比较数据语义和限制，不急于写下单代码。 |
| [Hyperliquid WebSocket](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket) | 官方文档提供实时 trades 等订阅方式。 | 第二个场所的验收包含 REST 与 WebSocket 的数据一致性检查。 |

### 3.3 学习科学的原始研究记录

| 资料 | 研究摘要支持的结论 | 课程设计决策 |
|---|---|---|
| [Roediger & Karpicke, 2006, PubMed PMID 16507066](https://pubmed.ncbi.nlm.nih.gov/16507066/) | 延迟测试中，主动回忆比重复阅读更能保持长期记忆；重复阅读会提高信心，但不等于延迟保持。 | HTML 阅读不再算通过；每次课程必须有闭卷解释、代码复现和新场景迁移。 |
| [Karpicke & Roediger, 2008, PubMed PMID 18276894](https://pubmed.ncbi.nlm.nih.gov/18276894/) | 重复检索对延迟保持有显著作用；学习者对自己的保持能力判断并不可靠。 | 每天开头和隔几天安排短回忆；不以“看过/觉得懂了”作为完成证据。 |
| [Karpicke & Bauernschmidt, 2011, PubMed PMID 21574747](https://pubmed.ncbi.nlm.nih.gov/21574747/) | 重复检索之间有更长的绝对间隔时，长期保持明显更好；研究摘要报告相对无间隔有约 200% 的保持提升。 | 将 Day 2–7 的关键概念在后续 funding、执行和统计场景中重新出现，而不是每个概念只验收一次。 |
| [Cepeda et al., 2006, PubMed PMID 16719566](https://pubmed.ncbi.nlm.nih.gov/16719566/) | 分布式练习对长期保持有系统性支持。 | 课程采用“当天建立模型、隔日迁移、周末综合回放”，而不是连续堆叠相似选择题。 |

## 4. 重设计的具体原则

### 原则 A：从“字段顺序”改成“能力流程”

新的主线是：

```text
研究问题
→ 市场/合约模型
→ 可复现数据
→ 盘口和成交
→ 现金账本
→ 统计检验
→ 净现金回放
→ 压力测试
→ 证据决策
```

Lighter WTI/BRENTOIL 仍然保留，但作为一个深度案例；Binance BTCUSDT 和 Hyperliquid BTC 永续作为迁移案例。这样既保留深度，又避免把 RWA 特有的展期/oracle 规则误认为所有永续的通用规则。

### 原则 B：每 2–3 天交付一个可复用组件

必须逐步形成：

1. 只读采集器：REST 分页、WebSocket、限流、断点续采、原始哈希；
2. **统一字段结构**：源时间、接收时间、市场、价格语义、质量标记；
3. 盘口走档器：bid/ask、VWAP、冲击、部分成交、异步双腿；
4. 现金账本：持仓、成交、费用、funding、保证金、清算准备金；
5. 样本外回放器：冻结参数、时间切分、成本压力、拒绝结论；
6. 证据报告：每个数字可回到原始响应和代码版本。

### 原则 C：互动 HTML 只做可视化，不做唯一验收

每个 HTML 最多保留一个可视化或模拟器。真正验收改为：

- 运行仓库命令并观察真实输出；
- 修改一个参数或故意注入一个异常；
- 不看答案解释原因；
- 在另一个市场/场景中迁移；
- Python 单元测试 + 浏览器 DOM smoke test。

选择题只能作为即时反馈，不能作为通过的唯一证据。

### 原则 D：策略结论和学习结论使用不同闸门

- **学习通过**：能解释、能运行、能复现、能迁移；
- **研究继续**：数据、语义、执行和风险证据足够；
- **可交易**：还需要冻结参数的样本外净现金结果、持续运行、权限核验、监督实验和独立风险确认。

这三个状态不得合并成“课程学完 = 可以交易”。

## 5. 资料局限

- 本资料只验证了官方文档/API 的接口和机制描述，没有证明任何策略盈利；
- Binance/Hyperliquid 的公开市场数据可用于课程迁移，但跨场所资金费收益仍需处理资金占用、转账、借贷、保证金、延迟和执行风险；
- 学习科学资料说明检索和间隔练习的方向，不能替代针对本用户的学习结果测量；
- 当前 Lighter 动态快照仍然只有有限历史，后续必须通过连续采集补齐多种市场状态。
