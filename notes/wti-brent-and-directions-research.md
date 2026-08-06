# WTI–Brent 与替代研究方向评估

- 研究日期：2026-08-05
- 研究对象：Lighter `WTI`（`market_id=145`）与 `BRENTOIL`（`market_id=159`）
- 研究性质：只读研究，不构成交易建议；所有动态数字均是带抓取时间的快照
- 本报告只新增本文件，不修改 `MISSION.md`、`resource/plan.md` 或其他课程文件

## 1. 执行摘要

### 结论

1. **WTI–BRENTOIL 值得继续作为主学习案例，但目前不是可交易结论。** Lighter 官方资料确认两者是同一场所的两个 RWA 永续市场：分别追踪 WTI 和 Brent 桶价，使用 Pyth Lazer 价格源，并使用期货价格滚动机制。[42][43][44][45]
2. **短样本只证明“值得审计”，不证明协整或盈利。** 本地保存的 Lighter 1h 快照两腿各为 500 根，共同覆盖约 21 天；共同小时收盘对数收益相关性为 `0.9707121232645127`。这是相关性与描述性统计，不是协整检验，也不是费用后收益证明。[47][48][49][50]
3. **当前阻断项是历史深度、展期状态、funding 账本、目标数量成交与退出。** 因此当前状态仍是 `Blocked / No-Go`，不写真实下单代码。[44][46][68][69]
4. **替代方向中，最适合接下来的学习顺序是：**
   - 第一优先：Lighter WTI–BRENTOIL，作为“合约语义 + 数据工程 + 统计检验 + 执行审计”的主案例；
   - 第二优先：Binance–Hyperliquid 的 BTC/ETH funding/basis，作为数据更成熟的基准案例；
   - 第三优先：Hyperliquid `xyz:CL`–`xyz:BRENTOIL`，作为 RWA 跨场所/跨市场对照，但不是当前主线；
   - 条件性第四优先：Lighter–Hyperliquid 的同名/相近 RWA 价格观察，先做只读同步，暂不视为可对冲；
   - 暂缓：CEX–DEX、清算/MEV/跨链等需要更多权限、链上状态和实时执行基础设施的方向。

## 2. 证据分层与时间边界

### 2.1 官方规则资料

以下内容来自平台官方文档，描述相对稳定的产品规则：RWA 经济对象、价格源、EMA/index/mark、期货展期、funding 公式、API 返回限制和交易费用。[42][43][44][45][46][57][72]

### 2.2 动态 API 快照

本仓库的动态证据来自 Lighter 官方公共 API、Hyperliquid 官方 `info` API 和本地保存的原始响应。它们只能说明抓取时状态，不能代表长期平均状态，也不能直接当作盈利证明。

- Lighter K 线、funding 和 `orderBookDetails` 快照抓取时间：`2026-08-05T14:45:01Z`–`14:45:04Z`；所有 8 个请求 HTTP `200`，原始响应及 SHA-256 见 `lab/data/lighter_rwa_capture_manifest.json`。[49][50][51][52][53][54]
- Lighter `orderBookOrders`、`recentTrades` 与 `funding-rates` 查询约在 `2026-08-05T16:10:30Z` 运行；它们仍是一刻快照，不能把订单数、24 小时成交量或最优档位直接解释为可持续容量。[20][68][69][70][71]
- Hyperliquid `info` API 快照抓取于本研究运行时；当前 `perpDexs` 返回包含 `xyz`，其资产列表包含 `xyz:CL` 与 `xyz:BRENTOIL`；`metaAndAssetCtxs` 返回两者的市场上下文。[22][55][56]

## 3. Lighter WTI–BRENTOIL：已确认事实

### 3.1 市场身份与经济对象

| 字段 | WTI | BRENTOIL | 证据/状态 |
|---|---:|---:|---|
| 平台 | Lighter | Lighter | 官方 API 快照 |
| market id | `145` | `159` | `orderBookDetails` 快照 |
| 产品 | perp | perp | 官方 API 快照 |
| 经济对象 | 1 桶 WTI | 1 桶 Brent | Lighter RWA 市场规格 |
| 价格源 | Pyth Lazer | Pyth Lazer | Lighter RWA 市场规格 |
| 期货展期 | 有 | 有 | Lighter 展期文档 |
| 市场状态（抓取时） | active | active | 动态 API 快照 |
| RFQ 开关（抓取时） | true | true | 动态 API 快照 |

结论：两腿在单位上都表现为每桶美元价格，但它们不是同一标的；“价差”需要表达 Brent–WTI 的相对价值假设，而不能称为同一资产的跨场所无风险价差。[45]

### 3.2 当前规格快照

抓取到的 `orderBookDetails` 字段显示：

- WTI：最小基础数量 `0.100`，数量精度 3 位，价格精度 3 位；默认初始保证金分数 `500`，维护保证金 `300`，close-out `200`；
- BRENTOIL：最小基础数量 `0.0800`，数量精度 4 位，价格精度 2 位；默认初始保证金分数 `666`，维护保证金 `300`，close-out `200`；
- 两腿快照中的 `multiplier=1`、`quote_multiplier=1`，但最终名义金额仍需结合 API 的数量语义、账户账本与实际成交回放核验；不要只凭 ticker 推断合约乘数；
- 两腿快照中的 maker/taker fee 字段为 `0.0000`，而当前 Lighter 费用页说明 Standard Account 为 0 maker/0 taker；Premium Account 有阶梯费率，且 Plus Account 有不同费用与延迟配置。[28][45][72]

这些数字都是抓取时动态状态；原始响应保存在 `lab/data/lighter_rwa_raw/145_orderBookDetails.json` 和 `159_orderBookDetails.json`。费用字段不能替代对账户等级、积分/质押状态、RFQ 路径和成交回执的核验。

### 3.3 定价、展期与市场时段

Lighter 官方资料说明，RWA 价格机制可能在外部 oracle 价格与内部订单簿 impact price 的 EMA 之间切换；因此历史 close、index、mark 和成交价不一定代表同一价格过程。[43]

官方展期资料说明，WTI 与 BRENTOIL 使用期货合约价格，并按不同窗口进行展期：WTI/NATGAS 窗口从美国东部时间 `17:30` 开始，BRENTOIL 窗口从美国东部时间 `19:00` 开始；滚动采用每日 `20%` 的当前月到下一月权重迁移。[44]

这意味着：

- 不能把 WTI–BRENTOIL 的变化完全解释为现货 Brent–WTI 基差；
- 展期窗口差异可能制造确定性的日内结构断点；
- 需要记录每条价格观测是否处在各自展期窗口、市场关闭/数据陈旧窗口或 oracle 切换阶段；
- 未找到足够官方证据确认两个 RWA 市场的全部交易时段、周末暂停、陈旧 oracle 的精确阈值和所有异常暂停行为，暂标为 `UNKNOWN`。[unverified]

### 3.4 Funding

Lighter 官方 funding 文档提供 funding rate、premium、index 等计算语义；但原始 API 还包含 `value`、`rate`、`direction` 等字段。不能把 WTI 和 BRENTOIL 两个 `value` 字符串直接相减并称为收益。[46]

本地 1h funding 快照：

- WTI：750 条；`value` 均值 `0.0013530334533333333`；方向 `long=679`、`short=71`；
- BRENTOIL：750 条；`value` 均值 `0.00166616968`；方向相同；
- 原始 `value` 差的均值为 `-0.00031313622666666666`。

以上只是 API 字段的描述统计。要进入回测，必须完成：

```text
funding cash flow
= position sign
× base quantity
× contract / quote multiplier
× funding price
× settled funding rate
```

并核对方向、周期、结算时点、预测/已结算状态以及账户实际 ledger。当前仍为 `FUNDING_LEDGER_UNKNOWN`。[46][53][54]

### 3.5 订单簿与成交可得性

Lighter 官方 API 公开了 `orderBookDetails`、`orderBookOrders`、`recentTrades` 等端点；本次查询能够拿到两腿的买卖档和最近成交。[16][20][68][69][70][71]

- Lighter top-of-book 与最近成交快照是在上述 `2026-08-05T16:10:30Z` 左右的查询中观察到的：[68][69][70][71]

- WTI top ask/bid 约为 `75.698 / 75.677`，价差约 `0.021` 美元；
- BRENTOIL top ask/bid 约为 `79.65 / 79.64`，价差约 `0.01` 美元；
- WTI 最近成交样本包含 `0.011`、`0.257` 基础数量；BRENTOIL 最近成交样本包含 `0.0008`、`0.0094`、`1.8460` 基础数量；
- WTI 与 BRENTOIL 的动态日名义成交量和盘口深度差异很大，不能用 24 小时总量代表目标数量容量。

这些值只能作为带时间戳的微观结构快照。对策略研究必须按目标数量分别走 ask/bid 档位，模拟开仓和反向平仓，并计算部分成交、延迟、撤单和单腿暴露。[68][69]

## 4. WTI–BRENTOIL 统计套利：什么需要证明

### 4.1 相关性不等于协整

相关性主要描述收益或水平变化的同步程度。两个价格序列可以高度相关但各自带趋势，从而没有稳定的线性组合；也可以在短样本中看起来相关，长期却因展期、供需或市场状态变化而断裂。

协整研究需要检验：是否存在参数 `β` 和截距 `α`，使得：

```text
z_t = log(P_Brent,t) - α - β × log(P_WTI,t)
```

在合理样本和稳定定义下，`z_t` 近似平稳，并且该关系在滚动窗口、不同子样本及样本外仍有支持。这里的 `β` 不是默认的 1，也不是因为两个价格都以美元/桶表示就可以省略估计。

### 4.2 所需数据

至少需要：

1. 两腿同一价格语义的高频序列：close、index、mark、mid、成交价要分开保存；
2. 足够长的历史，覆盖不同原油行情、展期阶段、交易时段和波动状态；
3. 展期窗口、oracle 来源/状态、市场暂停与陈旧数据标记；
4. 两腿 funding 的原始字段与可解释的现金结算账本；
5. 每个时间点可成交的 bid/ask、深度、报价更新时间和目标数量执行价格；
6. 费用等级、保证金、清算和账户限制；
7. 失败恢复字段：一腿成交、另一腿失败、撤单、断线、暂停、强平和退出不可用。

当前 500 小时共同样本不足以支持长期协整结论。即使增大样本，也必须先解决两腿的价格过程不完全同质问题。

### 4.3 建议的检验顺序

1. 用 UTC 时间戳清洗重复值、缺失值、非交易时段和陈旧值；
2. 分别检查 `log(price)` 的单位根特征与价格语义；
3. 对固定窗口估计 Engle–Granger 残差，并用滚动窗口检查 β、半衰期、残差波动和 ADF 结果；
4. 做结构断裂和展期窗口前后分组比较；
5. 比较固定美元差、对数差和动态 β 残差，但不能先看哪个回测赚钱再选择定义；
6. 只在训练集内确定阈值、持仓上限和退出规则；
7. 在完全未使用的样本外做纸上成交回放；
8. 扣除双腿开平仓冲击、funding、手续费、保证金机会成本和失败恢复成本；
9. 做压力情景：价差继续扩大、某一腿停牌、oracle 陈旧、单腿成交、退出深度减半、funding 突变。

任何一个关键成本或退出字段未知，都只能标为 `Blocked`，不能填零。

## 5. 当前可行性判断

| 维度 | 当前判断 | 原因 |
|---|---|---|
| 经济关系 | `research_signal` | Brent/WTI 有经济联系，但两腿是不同 RWA 永续，且期货展期不同 |
| 历史统计 | `Blocked` | 当前共同 1h 历史约 21 天，不能证明长期协整 |
| 定价稳定性 | `Blocked` | oracle/EMA/index/mark 与展期窗口需建模 |
| funding 收益 | `Blocked` | API 字段到实际账户现金流尚未核对 |
| 目标数量执行 | `research_signal` | 有公开盘口和成交端点，但还没有双腿进出回放 |
| 费用 | `research_signal` | Standard 账户文档为 0 maker/taker，但账户等级、RFQ 和其他延迟/费用配置需确认 |
| 保证金/清算 | `Blocked` | 有市场快照保证金字段，但账户组合保证金、清算路径和异常状态未完成审计 |
| 交易权限 | `Blocked` | 只读公共 API 不证明账户、地区或实时交易权限 |
| 综合结论 | `Blocked / No-Go` | 不能承诺收益，不进入真实下单 |

## 6. 替代研究方向比较

评分含义：`高` 表示对当前学习目标/研究价值较高，`低` 表示当前不值得优先投入；不是收益预测。

| 方向 | 机会价值 | 数据可得性 | 学习收益 | 实现难度 | 资金/权限 | 主要风险 | 优先级 |
|---|---|---|---|---|---|---|---|
| Lighter WTI–BRENTOIL 同场所 RWA 相对价值 | 中–高（待验证） | 中：官方 candles/funding/orderbook 可读，但历史深度和语义存在阻断 | 很高：RWA、oracle、展期、统计、执行和风险 | 中–高 | 研究阶段 `$0`；只读公共 API；实盘需账户、权限和保证金 | 展期断点、oracle/EMA、单腿、流动性、funding、清算 | **1** |
| Binance–Hyperliquid BTC/ETH funding/basis | 中–高（基准研究） | 高：两边公开市场数据/API；Binance 官方提供 order-book 与 funding 历史端点，Hyperliquid 官方提供 info API 与历史市场数据说明，具体历史深度仍需实测。[1][56][57][58][63][73] | 高：时间对齐、资金费、跨场所转账和执行回放 | 中 | 只读阶段可 `$0`；实盘需要两边账户、KYC/地区、资产和 API 权限 | 资金转移、不同标记价、手续费、拥堵、腿间延迟、交易所风险 | **2** |
| Hyperliquid `xyz:CL`–`xyz:BRENTOIL` RWA 相对价值 | 中（对照研究） | 中–高：官方 `perpDexs`、`metaAndAssetCtxs`、`allMids` 可读；官方历史数据页说明 API 可自行记录，但没有直接提供 candles 历史数据集 | 高：HIP-3 builder-deployed perp、oracle、保证金、流动性和 RWA 语义 | 中–高 | 研究阶段 `$0`；需 Hyperliquid 账户/权限才能验证真实成交 | builder/oracle 治理、不同 OI 上限、价格源、流动性、市场暂停 | **3** |
| Lighter–Hyperliquid 同名/相近 RWA 跨场所观察 | 中（只有在合约同质性成立时） | 中：两边都有当前公共 API，但历史、时间戳和合约语义需要另建 | 很高：合约映射、跨场所 basis、oracle、转移和失败恢复 | 高 | 只读 `$0`；真实实验需两边账户、保证金和权限 | 相近 ticker 不是同一合约；展期、oracle、交易时段和结算不一致 | **4（条件性）** |
| CEX–DEX 现货/永续价差 | 中–高（更接近执行型套利） | 中：CEX API + 链上 RPC/DEX quoter 可读；Uniswap 官方 quoting 文档给出报价与 price impact 路径，Ethereum 官方 JSON-RPC 文档给出链上读取接口 | 很高：RPC、AMM、gas、nonce、滑点、交易确认、失败恢复 | 高 | 只读可 `$0`；测试/实盘需钱包、gas、RPC、代币批准和安全边界 | gas、MEV、价格冲击、交易失败、桥和资金延迟、智能合约风险 | **5（基础补齐后）** |
| 清算/MEV/跨链机会 | 理论上高，当前不可评估 | 低–中：需实时 mempool/节点/协议事件、私有 relay 或多链基础设施 | 很高但偏工程与安全 | 很高 | 需要节点/relay/钱包/资金和更强权限；不适合当前 `$0` 研究边界 | 竞争、抢跑、私钥、合约、链重组、gas、不可逆损失 | **暂缓** |

### 6.1 为什么 Binance–Hyperliquid BTC/ETH 适合作为基准

这是一个“数据和产品语义相对成熟”的对照组，而不是直接替换当前主线。Binance 官方文档公开 order-book 和 funding history 接口，Hyperliquid 官方 API 公开市场元数据与实时上下文；两边都更适合练习统一时间轴、资金费现金流和目标数量成交回放。[1][56][57][58][63]

需要明确：公开历史端点不自动保证足够的逐笔深度、完整成交回执或资金转移速度；跨场所套利还要把充值/提现、链确认和单腿风险算进生命周期。

### 6.2 为什么 Hyperliquid RWA 是有价值但不应立即切换的对照

当前官方 `perpDexs` 快照确认 `xyz` deployer 下存在 `xyz:CL` 与 `xyz:BRENTOIL`；`meta` 显示两者都为 `maxLeverage=20`、`marginTableId=20`，但这是一个动态配置快照，不代表与 Lighter 的经济对象、展期和价格源相同。[22][55][56]

Hyperliquid 官方历史数据页说明，S3 主要提供 L2 book snapshots 和 asset contexts，不提供 candles 等全部历史数据集；研究者可以用 API 自己持续记录。因此它适合建立新的只读采集器，但不适合把短期当前快照直接拼接到 Lighter 历史序列。[63]

### 6.3 为什么 CEX–DEX 与 MEV 暂缓

Uniswap 官方文档中的 quoting 流程和 Ethereum 官方 JSON-RPC 文档确实提供了学习 AMM 报价、链上状态与交易构造的入口。[59][60] 但当前用户的目标是先理解现有研究代码、建立可复现数据和纸上回放；CEX–DEX 需要增加钱包、gas、交易确认、RPC 可靠性和智能合约失败路径。MEV/跨链还会进一步引入竞争和不可逆损失。因此它们是后续学习方向，不是本月的交易候选。

## 7. 推荐研究顺序与停止条件

### 7.1 接下来 1–2 周

1. 继续 Lighter WTI/BRENTOIL 只读采集，按分页、重复抓取和 UTC 时间戳保存历史；
2. 建立合约状态表：price semantic、oracle/EMA、展期窗口、市场关闭、funding 字段、保证金和未知项；
3. 收集逐小时/逐分钟 order-book snapshots，至少支持两个目标名义规模的入场和退出走档；
4. 用一个明确的模拟账户 ledger 验证 funding `direction/value/rate` 到现金流的映射；
5. 暂不做真实交易，也不把当前 0.971 相关性写成策略信号。

### 7.2 之后的基准实验

当 Lighter 状态表和数据审计完成后，再并行采集 Binance–Hyperliquid BTC/ETH 的只读数据。目标不是马上寻找收益，而是用一个语义更清楚、历史更容易获得的案例检验：

- 时间对齐是否正确；
- funding 是否按实际结算周期入账；
- 目标数量开平仓后的净现金是否仍为正；
- 策略是否能处理单腿、退出和断线。

### 7.3 Go / No-Go / Blocked 规则

- `Go to paper replay`：合约语义、历史数据、资金费、目标数量入口与退出、费用、保证金和失败路径均有证据，并且样本外净现金 PnL 在压力假设下仍非负；
- `No-Go`：确认结构关系不存在、目标数量执行成本压过价差，或压力测试净现金必然为负；
- `Blocked`：关键字段未知，尤其是结算、展期、funding 账本、权限、退出或目标数量成交。

当前 WTI–BRENTOIL 仍是 `Blocked`，但作为学习和研究案例的优先级为 **1**；这不是对未来收益的判断。

## 8. 参考资料

- Lighter RWA 与市场机制：[42][43][44][45][46]
- Lighter API 与动态快照：[16][20][47][48][49][50][51][52][53][54][68][69][70][71][72]
- Hyperliquid HIP-3、Info API、费用、funding 与历史数据：[22][31][55][56][57][63]
- Binance 官方市场数据与 funding API：[1][58][73][74]
- Variational 官方只读 API 文档：[17]
- Uniswap 官方 quoting、Ethereum 官方 JSON-RPC：[59][60]

## 9. 未验证项清单

以下项目在本报告中没有被无证据填补：

- Lighter 与 Hyperliquid WTI/Brent 的精确 Pyth feed、指数构成和更新时间是否相同；
- 两个平台 RWA 期货展期所使用的具体合约月份、权重和展期边界在所有日期上的完整记录；
- Lighter funding API `value/rate/direction` 到实际账户资金变化的完整映射；
- 两腿市场全部交易时段、周末规则、陈旧 oracle 阈值和暂停后的恢复行为；
- RFQ 是否适用于目标数量、报价有效期、部分成交和退出路径；
- Lighter 账户/地区/产品权限与当前用户资格；
- 任何策略的样本外收益、净现金 PnL 或未来盈利能力。

## Sources

[1] https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History — Binance USDS-Margined Futures: Get Funding Rate History
[16] https://apidocs.lighter.xyz/reference/orderbookdetails — Lighter API: Order Book Details
[17] https://docs.variational.io/technical-documentation/api — Variational Docs: API
[20] https://mainnet.zklighter.elliot.ai/api/v1/funding-rates — Lighter Public Funding Rates API
[22] https://api.hyperliquid.xyz/info — Hyperliquid Public Info API
[28] https://docs.lighter.xyz/trading/trading-fees — Lighter: Trading Fees
[31] https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding — Hyperliquid: Funding
[42] https://docs.lighter.xyz/trading/real-world-assets-rwas — Lighter Docs: Real World Assets (RWAs)
[43] https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism — Lighter Docs: RWA Pricing Mechanism
[44] https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism — Lighter Docs: Futures Contract Price Rolling Mechanism
[45] https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications — Lighter Docs: RWA Market Specifications
[46] https://docs.lighter.xyz/trading/funding — Lighter Docs: Funding
[47] https://apidocs.lighter.xyz/reference/candles — Lighter API: Candles
[48] https://apidocs.lighter.xyz/reference/fundings — Lighter API: Fundings
[49] https://mainnet.zklighter.elliot.ai/api/v1/candles?market_id=145&resolution=1h&count_back=500 — Lighter API snapshot: WTI 1h candles
[50] https://mainnet.zklighter.elliot.ai/api/v1/candles?market_id=159&resolution=1h&count_back=500 — Lighter API snapshot: BRENTOIL 1h candles
[51] https://mainnet.zklighter.elliot.ai/api/v1/candles?market_id=145&resolution=1d&count_back=500 — Lighter API snapshot: WTI 1d candles
[52] https://mainnet.zklighter.elliot.ai/api/v1/candles?market_id=159&resolution=1d&count_back=500 — Lighter API snapshot: BRENTOIL 1d candles
[53] https://mainnet.zklighter.elliot.ai/api/v1/fundings?market_id=145&resolution=1h&count_back=750 — Lighter API snapshot: WTI 1h funding
[54] https://mainnet.zklighter.elliot.ai/api/v1/fundings?market_id=159&resolution=1h&count_back=750 — Lighter API snapshot: BRENTOIL 1h funding
[55] https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-3-builder-deployed-perpetuals
[56] https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
[57] https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees
[58] https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data
[59] https://developers.uniswap.org/docs/sdks/v3/guides/swapping/quoting
[60] https://ethereum.org/developers/docs/apis/json-rpc
[63] https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data
[68] https://mainnet.zklighter.elliot.ai/api/v1/orderBookOrders?market_id=145&limit=20
[69] https://mainnet.zklighter.elliot.ai/api/v1/orderBookOrders?market_id=159&limit=20
[70] https://mainnet.zklighter.elliot.ai/api/v1/recentTrades?market_id=145&limit=10
[71] https://mainnet.zklighter.elliot.ai/api/v1/recentTrades?market_id=159&limit=10
[72] https://docs.lighter.xyz/trading/contract-specifications
[73] https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Order-Book
[74] https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information
