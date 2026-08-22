# 教学与研究工作区备注

## 用户能力与偏好

- 用户能独立处理 Python、REST/WebSocket、Git 与常见排错；Agent 负责本仓库的编码、运行和维护。
- 默认中文；接口字段、代码标识符和无准确中文替代的术语保留英文。
- 浏览器研究操作台展示真实数据、图表、诊断与执行摩擦；Telegram 用于讨论和下研究指令。
- 不使用浅选择题、固定解释模板、页面完成状态或测试通过证明掌握。
- 每次共学优先积累可复用数据集、脚本、CLI、分析模块、测试 fixture、页面或方法文档。

## 已确认的产品目标

- 产品是长期运行、可扩展、可二次开发的只读套利研究操作台，不是课程状态机或交易下单 UI。
- Dashboard 负责模块导航、摘要和数据健康；Screener 负责发现；专题模块负责历史、机制和执行验证。
- 第一主模块是 Brent–WTI 跨标的相对价值；同标的跨 venue 和 funding 是独立研究视图。
- Lighter、Hyperliquid 和 Variational 是主要 venue；Variational 只从 `monte-fox` 导入脱敏 `market_observation`。
- 工作台保持浅色模式，不以大 JSON 作为主要页面；JSON/CSV 用于下载和二次开发。
- 产品不注册 execution client，不发送真实订单。

## 当前能力

- Day16 v2：共同经济敞口、冻结 L2 走档、部分成交阻断、往返摩擦和容量下界。
- Day17 v1：Lighter/Hyperliquid/外部日线多价格源同步；Variational index/RFQ 只读导入；美元价差、比值、对数比值、冻结参考残差；按时间形成/验证窗口；腿贡献、UTC 时段、venue 分歧、roll/funding/数据健康诊断；JSON/CSV、Dashboard、油专题和数据目录。
- 真实运行时投影和原始油数据位于 Git 外并可用 CLI 重算。

## 当前关键边界

- Brent 与 WTI 是不同基准，美元价差不是套利利润。
- K 线、指数、mark、L2 和 RFQ 不能混用。
- 当前油执行表按 1:1 场所数量给出摩擦基线，不是 beta 对冲或经济中性仓位。
- 合约月份/权重、执行对冲比率、账户实际费率、持有期 funding、未来退出 L2 和保证金仍需证据。
- 日线缺口需要交易所日历；周末或节假日不能直接标为 feed failure。
- 机制诊断缩小研究范围，不证明因果、均值回归或盈利。

## 下一步

1. 接入经核验的 CL/BZ 合约月份、权重、roll 和 session 日历；
2. 持续采集 venue-native funding；
3. 抽出通用 PairDefinition、同步器、图表和执行比较；
4. 建设全市场 Screener、Funding 和通用 Spread Grapher；
5. Day18–19 加入机会回放和执行失败路径。

## 当前入口

- 产品目标：`MISSION.md`
- 当前计划：`resource/plan.md`
- 产品架构：`docs/product/research-console.md`
- 油专题：`docs/product/oil-relative-value-v1.md`
- 领域词汇：`CONTEXT.md`
- 当前里程碑：`curriculum/day17.md`
- 详细设计：`research/design/workbench-design.md`

## 安全授权

- 公开行情采集器可以独立运行；长期原始数据不进 Git。
- 若未来核验账户费率，必须在独立只读进程中从运行环境读取凭据并默认脱敏。
- 不发送订单、不签署交易；服务器、账户和密钥不写入研究材料。
