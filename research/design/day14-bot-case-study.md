# Day14 第一课：BOT 候选案例分析（真实数据）

日期：2026-08-19
状态：已完结（候选标记为可疑）

## 现象

工作台候选 `BOT__xyz:BOT`，快照价差 −40.5 bps：

| 项目 | Lighter (market 185) | Hyperliquid xyz:BOT |
|---|---|---|
| bid | 28.573 | 28.667 |
| ask | 29.036 | 28.689 |
| bid size | 7.0 | 1.74 |
| ask size | 95.9 | 1.4 |
| 来源时间 | 无 | 有 (1787096484082) |

## 三个假设与实验结果

### H1：两个 "BOT" 不是同一个标的 —— 否决

- Lighter tokenlist：`BOT = RoboStrategy`（RWA/STOCK）
- CoinGecko 确认存在两个 BOT：
  - 加密货币 BOT（Binance/Bybit 参考源）：$9.62，+2.46%
  - RoboStrategy 股票（Backpack Securities）：$28.44，−11.37%
- HL xyz:BOT mark 28.630 / oracle 28.422 / 24h −11.52% → 与股票吻合
- 两边都是 RoboStrategy 股票 → 标的相同

### H2：时间差导致错位 —— 否决

- 494ms 内同时采样两边盘口，错位反而扩大：
  - 方向A（买Lighter ask/卖HL bid）：−103.1 bps
  - 方向B（买HL ask/卖Lighter bid）：−23.0 bps
- 不是旧报价问题，是持续错位

### H3：深度太薄报价不真实 —— 部分否决

- Lighter ask 逐档（实时）：
  - 28.9140 × 97.067
  - 28.9140 × 3.479
  - 28.9750 × 138.051
  - 29.0360 × 137.761 ...
- 深度真实（每档 97–138 单位），但第一档价格在 10 分钟内从 29.036 移到 28.914（−0.42%）
- Lighter 自身价差 118.6 bps，HL 仅 8.7 bps → Lighter 报价结构本身异常

## 最终诊断

- 两个市场跟踪同一 RoboStrategy 股票
- HL 报价紧贴真实价（28.62）
- Lighter ask 虚高 0.95%，报价陈旧/做市不活跃
- 候选标记：**可疑（拒绝交易）**，表面价差不代表可成交

## 🚨 附带发现：oracle 一致性红旗

Lighter `funding-rates` 对 market 185（BOT）的参考源：

| exchange | symbol | rate |
|---|---|---|
| binance | BOT | 0.00014499（加密货币 BOT，$9.62）|
| bybit | BOT | 0.00015555（加密货币 BOT，$9.62）|
| lighter | BOT | 3.2e-05（本所）|

而 Lighter tokenlist 说 BOT = RoboStrategy 股票（$28.44）。

**同一交易所内部：价格 oracle 指向股票，funding oracle 参考加密货币。**
这是数据质量红旗：按 Lighter funding 做资金费率套利会基于错误参考源计算。

## 第二循环：检测器本身的误报审查（2026-08-19）

检测器上线后第一次真实扫描报出 **148 个 oracle 红旗**（AAPL/TSLA/NVDA 等全被标为"价格 oracle 说股票、funding 参考币圈交易所"）。随即审查：

- Binance 上 AAPL 对应 **AAPLBUSDT（代币化股票）**，现价 $310.57 ≈ 苹果股价 → funding 参考源合理，是 Lighter 的设计
- Binance 上 BOT 只有 BOTBTC/BOTBUSD（加密货币，BREAK 状态），BOTUSDT 不存在 → **BOT 才是唯一真异常**
- 结论：147 个 VERIFY（需人工确认）+ 1 个 CONFIRMED（BOT）

检测器已改为两档：`CONFIRMED_MISMATCHES = {"BOT"}`（硬错误）与其他（VERIFY 提示）。教训：**检测器报错也要被审查——第一次跑出 148 个红旗本身就该怀疑是检测器过严，而不是数据全错。**

## 学习验收（用户回答）

1. 候选状态：可疑 ✅（但理由需修正：已实证报价陈旧，而非未验证）
2. 表面价差不代表可成交 ✅（核心教训）
3. oracle 不一致是否值得检查：用户原答"不值得（数据就是错的）"，**修正为：数据错恰恰必须检查**——发现错误正是检查系统的价值

## 工作台改进（下一步）

- [ ] 增加 `ORACLE_SOURCE_MISMATCH` 数据质量标记（对比 tokenlist 资产类型与 funding-rates 参考源）
- [ ] 候选标记区分"可疑（报价陈旧）"与"可交易"，可疑候选不进入交易榜
- [ ] funding oracle 参考源核验进数据质量检查

## 证据文件

- research/runs/day14-workbench-scan.json（快照）
- research/design/day14-live-api-check-2026-08-19.md（一手 API 核对）
- tokenlist API 输出（BOT=RoboStrategy, GEV=GE Verona, AAOI=RWA/NEW）
- funding-rates API 输出（binance/bybit/lighter 参考源）
- CoinGecko：BOT 加密货币 $9.62 / RoboStrategy $28.44
