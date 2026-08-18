# Day20：实时影子研究与机会雷达

> 状态：待实现
>
> 里程碑允许跨多个工作日

## 目标

让同一个工作台在真实行情中持续推荐候选并做本地纸上运行，同时用机会雷达低成本探索新 venue、RWA/TradeFi、funding 和链上方向。

## 工作台新增能力

- 实时只读扫描、候选刷新和本地 paper；
- 数据延迟、盘口年龄、断连、任务和存储健康；
- 历史研究逻辑与实时逻辑复用；
- 工作台重启后恢复候选与实验状态；
- RadarLead：数据入口、产品语义、限制、异象、下一验证和升级状态；
- 新方向探针不需要 execution client 或私钥。

## 第一批雷达

- 全部 Hyperliquid HIP-3 RWA；
- dYdX perpetuals；
- Architect/AX RWA marketdata；
- Ostium/Avantis RWA；
- CEX–DEX funding；
- Aave/Morpho 借贷与清算；
- AMM/聚合器跨池 quote。

依据：`research/design/opportunity-radar-primary-sources.md`。

## 用户研究动作

用户从主工作台候选和雷达线索中选择一个方向，判断：

- 现象是否值得研究；
- 下一项最低成本验证是什么；
- 正式适配器能带来什么新能力；
- 数据、账户、地域、资金或机制限制是否值得维护成本。

Agent 执行低成本探针或实现最小适配，用户解释是否升级、继续观察或暂缓。

## 完成条件

- 实时 paper 与历史研究调用同一核心逻辑；
- 系统健康和数据中断可见；
- 停止状态不产生新 paper 开仓；
- 至少一个新方向完成一手资料、公开数据和异象核对；
- 用户作出正式接入/继续雷达/暂缓决定并解释成本收益；
- 没有真实订单路径。
