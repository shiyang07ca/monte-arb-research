# 10 天课程与第 11–21 天条件式计划（v5）

> 版本：2026-08-06
>
> 研究对象：Lighter `WTI`（`market_id=145`）与 `BRENTOIL`（`market_id=159`）。
>
> 当前阶段：第 2 天已完成；第 1–10 天是本阶段的详细学习与研究计划。第 11–20 天不预先承诺内容，必须由第 10 天的证据闸门选择分支；第 21 天用于总结和复盘。
>
> 时间预算：每天 30–90 分钟，默认 60 分钟。每一天只追求一个可以运行、解释、复查的产出。

## 1. 课程目标和边界

这不是“十天找到盈利策略”的计划，而是十天内建立一套能够拒绝伪机会、复现数据、解释代码和做出 `Go / No-Go / Blocked` 判断的研究能力。

WTI 与 BRENTOIL 是同一场所的不同商品 RWA 永续，不是严格的跨场所套利；不预设 1:1 对冲、固定美元价差、固定价格比率或动态 beta。官方资料显示，两者分别代表 WTI 和 Brent 桶价，使用 Pyth Lazer 价格源，并具有不同的期货展期窗口。[43][44][45]

研究顺序固定为：

```text
合约语义 → 数据审计 → 统计检验 → 执行回放 → 决策
```

未知字段不能默认为 0。研究阶段资金为 `$0`；不认证、不连接私钥、不发真实订单、不写无人值守发单。

## 2. 学习成功与策略成功分开

### 学习成功

学习者能够：

- 用自己的话解释经济对象、价格源、展期、funding、保证金和退出风险；
- 从官方 API 原始响应复现审计数字；
- 逐字段解释研究代码，修改一个小规则并重新运行；
- 在训练/验证/测试划分下说明什么可以结论、什么只能保持未知；
- 看到证据不足时主动输出 `Blocked`。

### 策略成功

只有在以下条件全部有证据时，候选才可从 `Blocked` 进入纸上 `Go`：

- 价格语义和展期状态可解释；
- 历史数据覆盖足够且没有未来信息泄漏；
- funding 现金流可映射到账本；
- 目标数量的开仓、持仓、平仓成本可回放；
- 权限、保证金、清算和单腿退出路径已核验；
- 保守样本外净现金 PnL 在压力条件下仍不被成本吞没。

前十天不承诺满足这些条件，也不以获得正收益作为课程通过标准。

## 3. 每日固定学习循环

每天按以下顺序进行：

1. **检索**：不看答案，写出今天问题的已有理解；
2. **输入**：只读官方来源和仓库原始证据；
3. **动作**：运行一个脚本、查询一个字段或完成一个纸上计算；
4. **回忆**：关闭资料后口头解释；
5. **记录**：写入产出、证据路径、未知项和明日唯一动作。

每个学习日的“通过”包含四类证据：

- 口头解释；
- 代码复现；
- 数据审计；
- 研究回放或纸上场景。

## 4. Day 1–10 详细计划

### Day 1｜定义候选与拒绝规则

**问题**：研究的到底是什么，什么不算机会？

**输入**：`MISSION.md`、`notes/research-charter.md`、ICL 原始课程记录、Lighter RWA 总览。[42]

**动作**：

- 写出“同场所跨品种相对价值”与“跨场所无风险套利”的区别；
- 列出结算、经济对象、数量、权限、价格、funding、深度、退出等检查项；
- 为 `Go / No-Go / Blocked` 写定义。

**产出**：`notes/research-charter.md`、`learning-records/0001-rwa-perpetual-relative-value-boundary.md`。

**通过标准**：不看资料，能说出至少 5 个未知字段；能解释为什么相关性或一次盈利不能代表策略成立。

**依赖**：无。

### Day 2｜运行现有只读采集和审计

**问题**：现有数据来自哪里，覆盖了什么，哪些数字只是描述性结果？

**输入**：`lab/capture_lighter_rwa.py`、`lab/audit_lighter_rwa.py`、原始 JSON、manifest、audit。

**动作**：

```bash
python3 lab/capture_lighter_rwa.py
python3 lab/audit_lighter_rwa.py
python3 -m json.tool lab/data/lighter_rwa_capture_manifest.json >/dev/null
python3 -m json.tool lab/data/lighter_rwa_data_audit.json >/dev/null
```

保存请求 URL、参数、HTTP 状态、请求/接收时间、延迟、原始文件和 SHA-256；不把 token 或 header 写入仓库。

**产出**：`lab/data/lighter_rwa_capture_manifest.json`、`lab/data/lighter_rwa_data_audit.json`、`lab/data/lighter_rwa_aligned_1h.jsonl`、`notes/day-1.md`。

**当前证据**：两腿共同 1h candles 为 500 行、约 21 天；1h funding 各 750 行、约 31 天；收益相关性约 `0.9707121232645127`。这些数字只支持“值得继续审计”，不支持协整或盈利结论。[47][48][49][50][53][54]

**通过标准**：能从 audit 的一条数字回到原始 JSON 和 manifest；能指出 `HISTORY_DEPTH_INSUFFICIENT`。

**依赖**：Day 1。

### Day 3｜建立 RWA 合约模型

**问题**：两腿各自代表什么，数量和保证金怎样解释？

**输入**：`notes/rwa-contract-model.md`、官方 RWA 市场规格、`orderBookDetails` 原始快照。[45][72]

**动作**：

- 手工填写 WTI/BRENTOIL 经济对象、market id、产品类型、最小基础数量、最小报价金额、数量/价格小数位、乘数和保证金字段；
- 用一个 `$10` 目标报价金额和各自最小数量做数量可行性检查；
- 区分动态快照与稳定规则。

**产出**：`notes/rwa-contract-model.md`、字段字典、一个数量检查记录。

**通过标准**：不看代码解释为什么价格相近不能决定数量相等；能指出至少 3 个字段仍需账户或成交回执核验。

**依赖**：Day 2。

### Day 4｜价格源、index、mark 和 EMA

**问题**：一个 API 返回的价格是否都代表同一过程？

**输入**：官方 RWA 定价、Fair Price Marking、PnL 文档。[43][75][76]

**动作**：画出：

```text
外部 oracle → index / mark 计算
订单簿 impact price → 内部 EMA（oracle stale 时）
成交价 / mid / candle close → 观察数据
```

为数据表设计：`trade_price`、`candle_close`、`index_price`、`mark_price`、`mid_price`、`oracle_state`、`source_timestamp`。

**产出**：`notes/price-semantics.md`。

**通过标准**：能解释 oracle stale 如何造成价格过程切换；没有字段时写 `unknown`，不插值伪造。

**依赖**：Day 3。

### Day 5｜展期和市场状态

**问题**：价差变化来自相对价值，还是来自两个期货合约的不同展期？

**输入**：`notes/rwa-roll-and-session-model.md`、官方展期文档。[44]

**动作**：

- 把 UTC 时间转换为美国东部时间；
- 给每个小时标记 `wti_roll_window`、`brentoil_roll_window`、`market_closed_window`；
- 设计“全样本 / 排除展期 / 按展期阶段分层”的比较；
- 不因异常直接删除样本。

**产出**：`notes/rwa-roll-and-session-model.md`、时间状态表。

**通过标准**：能说出 WTI 17:30 与 BRENTOIL 19:00 的时区含义；能解释为什么时间错位会产生结构断点；缺数据时输出 `roll_semantics_unknown`。

**依赖**：Day 4。

### Day 6｜Funding 现金流与纸上账本

**问题**：funding API 的字段怎样进入两腿现金流？

**输入**：官方 Funding 文档、fundings 原始响应。[46][48]

**动作**：

- 建立 `timestamp/rate/value/direction/position_sign/quantity/settlement_price/cash_flow` 字段表；
- 用多头 WTI、空头 WTI、多头 BRENTOIL、空头 BRENTOIL 四个场景手工判断现金流方向；
- 明确 `value` 不能直接相减。

**产出**：`notes/funding-ledger-model.md`、纸上 funding ledger。

**通过标准**：能从仓位方向推出付款/收款方向；能说明为什么当前仍有 `FUNDING_LEDGER_UNKNOWN`。

**依赖**：Day 3、Day 4。

### Day 7｜数据清洗和可复现规则

**问题**：哪些样本能进入统计，哪些只能保留为异常证据？

**输入**：原始 candles/fundings、现有审计脚本、API candles/fundings 文档。[47][48]

**动作**：

- 统一 UTC 时间；
- 检查重复 timestamp、缺失小时、零值、非正价格和异常跳点；
- 保存原始值与清洗状态，不覆盖原始 JSON；
- 设计训练/验证/测试的时间切分；
- 若官方窗口无法扩展，记录 `HISTORY_DEPTH_INSUFFICIENT`。

**产出**：`lab/data/lighter_rwa_clean_1h.csv`、`notes/data-quality-report.md`。

**通过标准**：清洗可重新运行；每条统计样本能回溯到原始响应；异常不会被静默删除。

**依赖**：Day 2、Day 5。

### Day 8｜价差定义与样本外统计闸门

**问题**：固定价差、价格比率和动态 beta 哪个定义有证据？

**输入**：清洗数据、研究章程、统计方法资料；当前只允许把相关性作为描述性结果。

**动作**：

- 先写检验计划，再运行统计；
- 比较固定美元差、对数差和训练集估计的 beta；
- 只在训练集选择窗口和阈值；
- 在验证/测试集记录触发次数、回归时间、最大偏离和结构断裂；
- 如样本长度不够做协整或半衰期检验，标记 `Blocked`，不靠换公式制造结论。

**产出**：`notes/spread-definition-decision.md`；若实现统计模块，再增加单元测试。

**通过标准**：能解释相关性不等于协整；能指出任何全样本拟合回看的地方；能报告样本外限制。

**依赖**：Day 7。

### Day 9｜目标数量开平仓回放

**问题**：理论价差扣除双腿真实进出成本后还剩多少？

**输入**：`orderBookDetails`、`orderBookOrders`、`trades`、交易费用、订单类型和撮合文档。[28][62][68][69][78][79]

**动作**：

- 对至少 `$10/$20/$50/$100` 目标名义分别走 bid/ask 档位；
- 计算 WTI/BRENTOIL 数量、步长、余量和未对冲名义；
- 分别模拟开仓和平仓；
- 加入 spread、冲击、延迟、部分成交、单腿失败和 reduce-only 退出；
- 不把 24h volume 或一刻盘口快照当作容量证明。

**产出**：执行回放表、`notes/execution-replay.md`；如实现模块，再增加回放测试。

**通过标准**：至少一个方向在开仓和退出都使用正确方向的盘口；能给出单腿失败后的状态和停止动作；不使用 midpoint 代替成交价。

**依赖**：Day 3、Day 6、Day 7。

### Day 10｜证据闸门和分支选择

**问题**：我们学会了什么，策略研究下一步是什么？

**动作**：填写下表，不用“感觉”代替证据：

| 闸门 | 状态 | 证据路径 | 未知项 |
|---|---|---|---|
| 经济对象和数量 | `confirmed/partial/blocked` | 规格表、原始 JSON | 账本/成交语义 |
| 价格源和状态 | `confirmed/partial/blocked` | RWA 定价、价格字段 | oracle freshness |
| 展期和市场时段 | `confirmed/partial/blocked` | 展期表 | 完整关闭/恢复记录 |
| funding 现金流 | `confirmed/partial/blocked` | 纸上 ledger | 账户账本 |
| 历史覆盖 | `confirmed/partial/blocked` | audit/manifest | 多状态样本 |
| 目标数量进出 | `confirmed/partial/blocked` | execution replay | 连续深度 |
| 权限/保证金/清算 | `confirmed/partial/blocked` | 官方规则/账户证据 | 当前账户状态 |

**产出**：`notes/day-10-gate.md`、第 11–20 天分支选择。

**通过标准**：能分别回答“我是否学会了”和“策略是否成立”；任何关键字段未知时保持 `Blocked`；不因为相关性高就进入真实交易。

**依赖**：Day 1–9。

## 5. 第 11–20 天：第 10 天后选择，不预先承诺

### 分支 A｜历史仍不足：继续数据采集

触发：`HISTORY_DEPTH_INSUFFICIENT` 或无法覆盖多个展期/市场状态。

内容：分页或连续定时采集、原始证据哈希、缺失/重复审计、状态字段、时间窗口报告。

禁止：长期协整结论、阈值优化、真实订单。

### 分支 B｜统计关系否定：`No-Go` 复盘

触发：训练/验证/测试关系不稳定，或压力假设下净现金必然为负。

内容：保存否定性结果、分析结构断裂、比较替代定义、写替代研究问题。

禁止：反复调参直到得到正收益；把一次样本外盈利当成证明。

### 分支 C｜统计可研究但执行未知：执行与账本深化

触发：关系有研究信号，但 funding、连续深度、退出或权限仍未知。

内容：连续盘口快照、目标数量走档、双腿异步、部分成交、funding paper ledger、保证金和清算压力。

禁止：真实下单；未知成本不填零。

### 分支 D｜关键字段闭合：严格纸上回放

触发：价格语义、展期、funding、历史、费用、进出、权限和风险路径均有证据。

内容：冻结训练参数，在完全未使用的测试区间做净现金回放；测试压力场景；人工复核后决定是否只做极小额监督实验评估。

注意：本分支也不自动授权交易。真实实验需要另行确认，且必须保留 kill switch 和单腿恢复方案。

## 6. Day 21｜总结和复盘

产出：

- 学习成果清单：能解释、能复现、能审计、能回放的内容；
- 策略结论：`Go / No-Go / Blocked`；
- 未解决问题及证据路径；
- 下一周期唯一研究问题；
- 失败记录，而不是只记录正向结果。

通过标准：第三方只看仓库文件，就能重建当前判断；策略没有因为计划结束而被强行升级为 `Go`。

## 7. 当前建议状态

基于当前仓库快照：

- 学习方向：`Go`；
- 数据和策略研究：`Blocked`；
- 真实执行：`No-Go`。

现有审计指出：历史约 21 天、funding 约 31 天，且 funding 账本、目标数量退出和权限仍未闭合。`0.9707121232645127` 只是 499 个收益变化的描述性相关性，不是长期协整或净收益证明。

## Sources

[28] https://docs.lighter.xyz/trading/trading-fees — Lighter: Trading Fees
[42] https://docs.lighter.xyz/trading/real-world-assets-rwas — Lighter Docs: Real World Assets (RWAs)
[43] https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism — Lighter Docs: RWA Pricing Mechanism
[44] https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism — Lighter Docs: Futures Contract Price Rolling Mechanism
[45] https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications — Lighter Docs: RWA Market Specifications
[46] https://docs.lighter.xyz/trading/funding — Lighter Docs: Funding
[47] https://apidocs.lighter.xyz/reference/candles — Lighter API: Candles
[48] https://apidocs.lighter.xyz/reference/fundings — Lighter API: Fundings
[49] https://mainnet.zklighter.elliot.ai/api/v1/candles?market_id=145&resolution=1h&count_back=500 — Lighter API snapshot: WTI 1h candles
[50] https://mainnet.zklighter.elliot.ai/api/v1/candles?market_id=159&resolution=1h&count_back=500 — Lighter API snapshot: BRENTOIL 1h candles
[53] https://mainnet.zklighter.elliot.ai/api/v1/fundings?market_id=145&resolution=1h&count_back=750 — Lighter API snapshot: WTI 1h funding
[54] https://mainnet.zklighter.elliot.ai/api/v1/fundings?market_id=159&resolution=1h&count_back=750 — Lighter API snapshot: BRENTOIL 1h funding
[61] https://docs.lighter.xyz/trading/liquidations-llp-insurance-fund — Lighter Docs: Liquidations and LLP Insurance Fund
[62] https://docs.lighter.xyz/trading/order-types-matching — Lighter Docs: Order Types & Matching
[68] https://mainnet.zklighter.elliot.ai/api/v1/orderBookOrders?market_id=145&limit=20 — Lighter API snapshot: WTI order book orders
[69] https://mainnet.zklighter.elliot.ai/api/v1/orderBookOrders?market_id=159&limit=20 — Lighter API snapshot: BRENTOIL order book orders
[72] https://docs.lighter.xyz/trading/contract-specifications — Lighter Docs: Contract Specifications
[75] https://docs.lighter.xyz/trading/fair-price-marking — Lighter Docs: Fair Price Marking
[76] https://docs.lighter.xyz/trading/pnl-and-total-account-value — Lighter Docs: PnL and Total Account Value
[78] https://apidocs.lighter.xyz/reference/orderbookorders — Lighter API: Order Book Orders
[79] https://apidocs.lighter.xyz/reference/trades — Lighter API: Trades
