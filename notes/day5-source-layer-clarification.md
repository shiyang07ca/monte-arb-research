# Day 5 资料澄清｜交易所、交易者与 Lighter 的三层“展期”

## 结论先行

“展期”不是一个只有一个主体的规则。当前 WTI–BRENTOIL 研究里至少有三层含义：

1. **底层期货交易所的合约生命周期**：交易所发行当前月、下月等不同到期月份的期货合约，并规定交易时段、最后交易日、结算/交割规则。合约到期不是把两个合约自动拼成一个连续合约。
2. **交易者的 roll 操作**：如果交易者想继续保持期货敞口，通常要平掉临近到期合约、买入下一个月份，或交易 calendar spread。这是交易者的仓位管理动作，不是交易所替用户自动换仓。
3. **Lighter 的 RWA 永续价格机制**：Lighter 的 WTI/BRENTOIL 是永续市场；Lighter 不让用户持有一个会到期的 WTI 期货仓位，而是把期货价格作为底层参考，并按自己的文档把当前月价格逐步切换到下月价格。这是 Lighter 的**合成连续价格/指数构造规则**，不是交易所的一笔 roll 成交。

因此，Day 5 主要学习的是第 3 层，但必须理解它受到第 1 层合约到期的驱动；第 2 层用于解释为什么传统期货交易者会说“roll”。

## 一、Lighter 官方资料确认了什么

### 1. Lighter RWA 永续与底层市场不是同一个市场

Lighter 官方 RWA 总览说明：

- RWAs are tradeable 24/7；
- 交易时段之外杠杆不改变，但开市时波动可能增加；
- RWA 市场由 Lighter 的流动性/清算机制管理。

本地 Lighter API 快照也将两个市场标记为：

```text
WTI:      market_type = perp, status = active, market_id = 145
BRENTOIL: market_type = perp, status = active, market_id = 159
```

所以“底层期货市场关闭”不能直接翻译成“Lighter 永续不能交易”。

来源：

- [Lighter RWA 总览](https://docs.lighter.xyz/trading/real-world-assets-rwas)
- 本地第一方 API 快照：`lab/data/lighter_rwa_raw/145_orderBookDetails.json`、`159_orderBookDetails.json`

### 2. Lighter 自己规定价格如何从当前月过渡到下月

Lighter 的 [Futures Contract Price Rolling Mechanism](https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism) 明确写的是：

- WTI、BRENTOIL 等市场使用期货合约作为 underlying prices；
- 为处理 contract expirations，价格在第 5 到第 10 个工作日之间从当前月逐渐过渡到下月；
- WTI 每天美国东部时间 `17:30`，BRENTOIL 每天 `19:00`，每天有 `20%` 的价格从当前月移向下月；
- 文档给出 2026 年 8 月的 `80/20 → 60/40 → 40/60 → 20/80 → 0/100` 示例。

这段“每天 20%”是 **Lighter 的价格机制规则**。它不是在说 ICE/CME 交易所每天真的成交一笔“20% 换仓”。

### 3. Lighter 也明确写了底层关闭窗口

同一份 Lighter 文档说明：

```text
WTI/NATGAS 底层市场：17:00–18:00 ET 关闭
BRENTOIL 底层市场：18:00–20:00 ET 关闭
```

注意 WTI 的 `17:30` 和 BRENTOIL 的 `19:00` 都落在各自底层关闭窗口内。这个事实非常有用：它说明 Lighter 在关闭窗口中执行的是自己的价格参考权重切换，而不是声称底层交易所此刻正在进行一笔真实的 roll 成交。

## 二、交易所层：以 ICE Brent 官方资料为例

ICE 官方 [Brent Crude Futures](https://www.ice.com/products/219/Brent-Crude-Futures) 页面说明：

- 这是 ICE Futures Europe 的 Brent Crude **futures contract**；
- 合约是可交割的 EFP 合约，并可选择对最后交易日的 ICE Brent Index 现金结算；
- 交易在相关合约月份前第二个月的最后一个营业日的指定结算时段结束；
- 交易时段列为纽约时间 `20:00–18:00`（跨日），即纽约时间 `18:00–20:00` 关闭；伦敦时间为 `01:00–23:00`。

这描述的是：

```text
某一个 Brent 月份合约何时交易、何时停止交易、如何结算/交割
```

它没有说交易所把一张临近到期的合约自动变成下一张合约，也没有说所有持仓者都在某个时间自动换仓。

BRENTOIL 的底层关闭窗口与 ICE Brent 官方页面的 `18:00–20:00 ET` 交易时段缺口相互吻合；但 Lighter 的 `19:00 ET、20%` 过渡仍然是 Lighter 的价格机制。

## 三、三层规则对照表

| 层级 | 谁制定/执行 | 对象 | “展期”究竟改变什么 | 对 Lighter 用户的直接含义 |
|---|---|---|---|---|
| 交易所合约生命周期 | CME/NYMEX、ICE 等 | 月份期货合约 | 当前月接近最后交易日/结算日 | 底层参考合约会更换，交易所时间和价格可能出现断点 |
| 交易者 roll | 期货交易者 | 自己的期货仓位 | 卖前月、买下月，或做 calendar spread | 需要承担价差、手续费、流动性和执行风险；不是自动发生 |
| Lighter RWA 价格机制 | Lighter | WTI/BRENTOIL 永续的价格参考 | 按官方日程把价格权重从当前月逐日移到下月 | 用户的永续仓位不换合约，但 index/mark/可观察价格过程可能变化 |
| 底层交易时段 | 底层期货交易所 | 参考价格是否有实时交易 | 开市/关闭、结算时段 | 影响参考价更新和波动；不等于 Lighter 永续自动关闭 |

## 四、`2026-08-07T22:00:00Z` 应该怎样标记

2026 年 8 月美国东部是 EDT（UTC−4）：

```text
22:00 UTC = 18:00 ET
```

按 Lighter 公开日程解释：

### WTI

- 已经过 `17:30 ET` 的当日 Lighter 20% 过渡事件；
- 8 月 7 日示例的当日组成应标记为 `80% 当前月 / 20% 下月`；
- 底层 `17:00–18:00 ET` 关闭窗口刚结束；
- 不能写成“WTI 还没开始交易”。更准确是“WTI 仍处在五天展期窗口内，但当日切换事件已经发生”。

### BRENTOIL

- 已进入底层 `18:00–20:00 ET` 关闭窗口；
- 尚未到 Lighter 文档规定的 `19:00 ET` 当日过渡事件；
- 因而不能说底层此刻有正常连续成交；
- 但 Lighter RWA 官方规则是 24/7，不能据底层关闭直接断言 Lighter 永续不能交易。

### 重要边界

本地 candle 的 `timestamp` 到底代表一小时的开始还是结束，当前尚未被官方资料核实。因此对 `22:00Z` 的标签应保存：

```text
timestamp_utc = 2026-08-07T22:00:00Z
wti_lighter_roll_event = passed
brentoil_lighter_roll_event = not_yet
wti_underlying_closed = false_at_18:00_boundary
brentoil_underlying_closed = true
lighter_rwa_exchange_open = official_docs_say_24_7
candle_interval_semantics = unknown
```

## 五、研究上最重要的判断

看到 WTI–BRENTOIL 价差时，不能只问“展期了吗”，而要分层问：

1. 底层期货的当前月/下月合约生命周期处于什么阶段？
2. Lighter 自己的每日 20% 价格权重切换是否刚发生？
3. 两腿是否处于同一 Lighter 展期阶段？
4. 两腿的底层市场是否都开市？
5. Lighter 永续是否仍有盘口和真实成交？
6. 当前 candle 的时间戳边界是否清楚？

缺任何一项，都只能把价差作为“待解释的观测”，不能直接叫套利信号。

## 六、CME WTI 资料访问边界

本次尝试访问 CME 官方 WTI 合约规格/规则页面时，网页端返回 HTTP/2 错误，命令行访问返回 `403 Forbidden` 或超时。因此本笔记不把未经直接核验的 WTI 交易所最后交易日、具体交易时段或交割规则写成已确认事实。

Lighter 官方文档已经足以确认本课的关键层次：WTI 使用期货作为底层、Lighter 自己执行 20%/日的价格过渡、Lighter RWA 仍是 24/7；WTI 交易所层的精确规则后续应以 CME/NYMEX 当前官方 contract specifications/rulebook 补证。
