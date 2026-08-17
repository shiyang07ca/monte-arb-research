# 近期共学笔记研究摘要（2026-08-16）

> 状态：研究摘要
>
> 用途：从近期群友实践中提取可验证的研究方法和候选线索，不把群友结论当成交易证据。

## 1. 样本与处理方法

- 来源：残酷共学 Agent API 的课程提交列表，课程 ID 为
  `b43d2e97-ed88-4ca3-b12f-7ef672b01205`。
- 抓取范围：最新 2 页，共 40 条；平台当时返回总计 2,979 条。
- 时间窗口：`2026-08-16T13:28:17Z` 至 `2026-08-16T15:03:33Z`。
- 原始响应 SHA-256：
  `feb127e679aed91e560d133a4f315228fc84191dd98164747464e293fad2ff20`。
- 限制：这是约 95 分钟内的便利样本，不代表全部参与者，也不能据此估计某种策略的成功率。
- 隐私处理：仓库只保存去标识化摘要；原始笔记和访问凭据不写入仓库。

一条笔记只有同时回答下列至少三个问题，才作为高价值研究素材：

1. 输入来自哪里，取得时间是什么？
2. 做了什么计算、查询或故障实验？
3. 什么观察会淘汰原假设？
4. 结果文件或交易记录能否重新计算？
5. 作者明确承认了哪些未知项？

没有输入文件的收益数字、没有复现方法的策略结论、代码量和测试数量，只能生成待验证线索。

## 2. 最值得吸收的内容

| 主题 | 笔记中的观察 | 可以迁移的方法 | 当前证据等级 | 对本课程的改变 |
|---|---|---|---|---|
| 先做最便宜的证伪 | 有研究先核验地区/API 可用性、市场是否存在和成本上界，再决定是否建设长时间采集器 | 把上市状态、访问能力、最小订单和成本上界放在数据工程之前 | 方法可信；具体收益数字未复现 | Day12 先运行候选淘汰程序，不先搭采集平台 |
| 不合理结果反查测量 | 多个市场的 markout 都异常漂亮，作者回查后发现稀疏成交和 bid-ask bounce 会制造假象 | 与常识冲突的统一好结果首先是测量错误候选，不是策略突破 | 方法可信 | 每个统计结果都要运行时间错位、方向反转或不相干市场的负面对照 |
| Leg risk | 两腿不可能原子成交；Order ACK 也不等于 fill；部分成交会留下净敞口 | 记录 signal/send/ack/first fill/full fill、实际 VWAP、剩余数量和补对冲成本 | 原理可信；笔记未提供可复现实现 | Day16 用确定性故障场景实现状态机，不再做概念问答 |
| 概率加权收益 | 正的静态净价差仍可能被低成交概率、报价陈旧和失败损失推翻 | 用 `P(fill) × success_pnl - P(fail) × fail_loss` 比较执行方案，并报告估计误差 | 研究假设，需要本地数据校准 | 将延迟、成交概率和失败损失放入执行重放，不使用静态 spread 排名 |
| 监控与恢复 | 公共 RPC 出现 403、SSL 中断和 rate limit；另一笔记把有效市场列表做成“全量校验后再替换”，失败时保留上一份有效状态 | 每个数据源独立记录失败和退避；新快照先完整验证，再替换当前状态 | 实践经验可信，具体实现未审查 | Day20 必须注入断连、过期数据和坏快照，恢复失败时进入 `HALTED` |
| 交易重构 | 一笔 Morpho/Lulo/sNUSD 交易表面上有 USDC 余额增加，但完整资产负债表显示仍有债务和抵押品，不能称为闭合套利 | 从交易前后净资产、债务、抵押品、gas 和未定价资产判断收益，不看单个 token 余额 | 结论来自自报重构，需用公开交易重新做一遍 | 作为后续链上方向的首个迁移任务，而不是复制策略 |
| 批量交易普查 | 解析器改成增量、可恢复后，对数千笔交易分类，成功样本呈时间聚集 | 保存游标、输入块范围、失败记录和分类规则；聚集现象只生成进一步假设 | 数量为自报，尚未复算 | 后续链上研究采用可恢复普查，但不会把命中率直接当利润率 |
| Quote 到状态追踪 | LI.FI 笔记把 quote、allowance、签名、可选广播和 status 分开 | 每一步都有明确输入、输出和停止条件；默认 dry-run | 官方接口可核验；笔记实现未审查 | 可作为后续跨链库存模拟方向，当前 21 天不同时建设 |

## 3. 一个已经被当前数据淘汰的群友候选

样本中有一条笔记报告 `CRWD` 在某次 Binance 与 Hyperliquid 采集中可能仍有正的深度后价差，
同时承认方向符号曾写错、费用、退出和做空条件尚未完全核验。这条信息可以作为线索，但不能作为机会。

`2026-08-16T15:12:22Z` 重新查询 Hyperliquid 官方 `metaAndAssetCtxs` 后得到：

```json
{
  "index_in_meta": 111,
  "name": "xyz:CRWD",
  "isDelisted": true,
  "funding": "0.0",
  "openInterest": "0.0",
  "dayNtlVlm": "0.0",
  "midPx": null,
  "impactPxs": null
}
```

因此当前决定是 `Reject`。不需要继续计算 spread、手续费或建立 CRWD 采集器。这个案例说明：

```text
市场仍可交易
  先于 市场定义可比较
  先于 共同数量可成交
  先于 扣费后收益为正
  先于 统计与策略参数研究
```

Hyperliquid 的 HIP-3 市场由部署者定义和管理；市场状态和资产编号必须在每次研究时通过当前
`perpDexs`、`metaAndAssetCtxs` 与完整 `{dex}:{coin}` 名称重新取得，不能依赖群聊截图或旧 symbol 表。

## 4. 当前可继续观察的方向

以下只是研究优先级，不是收益排序：

### A. XAU / `xyz:GOLD`（推荐主线）

- 两边当前均为 active。
- `2026-08-16` 的公开状态中，Lighter XAU 24 小时名义成交额约 `$4.96M`，Hyperliquid
  `xyz:GOLD` 约 `$3.80M`；成交量不能代替目标数量的 L2 深度。
- 经济单位相对直接，但两边的 oracle、外部市场关闭状态、内部价格恢复方式和费用仍可能不同。
- 当前抓取发生在外部市场关闭时段附近，价格差尤其不能直接解释为可执行利润。

这个方向适合同时训练市场身份、交易时段、盘口执行和数据过期判断。

### B. XAG / `xyz:SILVER`（迁移考试）

- 两边当前均为 active，最小名义约 `$10`。
- 与黄金相似但价格精度、最小基础数量、深度和资金分配不同。
- 不在主课中逐步提示，适合检验方法能否迁移。

### C. WTI / `xyz:CL` 与 BRENTOIL（规则变化案例）

- 当前公开状态显示这些市场有交易，但“原油”名称不足以证明两腿跟踪同一月份和同一价格来源。
- 合约月份、展期权重、交易时段和部署者规则会制造结构性价差。
- 在实时证明当前底层合约之前，只做市场定义研究，不做统计套利结论。

### D. HIP-3 股票永续（候选扫描练习）

- `xyz:CRWD` 的下架证明股票永续市场集合会变化。
- `xyz:NVDA`、`xyz:AAPL` 当次查询仍为 active，但这只允许进入下一项核验，不代表存在价差。
- 适合训练“状态变化使旧研究失效”，不应预先选定某只股票作为长期主线。

### E. 链上与跨链（后续迁移方向）

- 链上：选择一笔公开交易，重建完整资产负债变化，再用本地 fork 重放；余额增加但仍有债务时必须拒绝“盈利”结论。
- 跨链：使用 LI.FI 的 quote、transaction 和 status 接口做不广播的库存与失败模拟；桥接时延、目标链 gas 和库存占用必须入账。
- 这两条线各自都需要独立的一组数据、故障和结算模型。剩余 10 天同时深入会牺牲 perp/RWA 的可运行成果。

## 5. 明确不采用的做法

- 不把群友报告的 bps、PnL、命中率或测试数复制进策略参数。
- 不因市场名称、mid price 接近或相关性高就称为同一风险敞口。
- 不在上市状态、访问能力和最小订单未通过前建设长时间采集器。
- 不把开仓瞬间的价差当成利润；退出四次成交、费用、funding 和失败损失都要出现。
- 不因没有候选通过而降低淘汰条件；`Reject` 是有效研究结果。
- 不再用网页按钮或多道微型算术题作为能力证明。

## 6. 一手资料与开源实现

- [残酷共学课程主页](https://intensivecolearn.ing/programs/b43d2e97-ed88-4ca3-b12f-7ef672b01205)
- [ICL Agent API OpenAPI](https://intensivecolearn.ing/api/v1/openapi.json)
- [Hyperliquid Perpetuals Info API](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals)
- [Hyperliquid Asset IDs](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids)
- [Hyperliquid HIP-3](https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-3-builder-deployed-perpetuals)
- [trade.xyz Specification Index](https://docs.trade.xyz/consolidated-resources/specification-index)
- [Lighter Order Books](https://apidocs.lighter.xyz/reference/orderbooks)
- [LI.FI Endpoint Specifications](https://docs.li.fi/agents/reference/endpoint-specs)
