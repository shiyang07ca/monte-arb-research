# Day12–21 跨场所永续研究系统课程

> 版本：2026-08-17
>
> 状态：当前唯一课程规划
>
> 真实订单：禁止

## 1. 最终成果

Day21 交付一个命令行研究系统，提供四个主要动作：

```text
扫描市场 → 淘汰并排名候选 → 重放执行 → 实时模拟
```

系统从 Lighter 与 Hyperliquid 的当前市场清单开始，不依赖群聊提供交易标识（`symbol`）。它保存原始输入、时间、版本和决定原因，使相同输入可以重新得到相同结果。

## 2. 不可省略的判断顺序

```text
当前可交易？
→ 两腿是否代表可比较的经济对象？
→ 当时是否处于可比较的价格状态？
→ 是否存在共同且账户可承受的数量？
→ 完整进出场后的保守净收益是否为正？
→ 机会寿命是否足以完成两腿？
→ 单腿失败是否可以在停止金额内处理？
→ 数据、仓位和现金能否重新计算？
```

任一条件为 false，决定为“拒绝”；关键条件未知，决定最多为“继续采集”。

## 3. 系统范围

### 场所

- 当前实现：Lighter、Hyperliquid。
- 市场范围：两边全部当前永续市场。
- 第三场所：Day21 后优先测试 AX Exchange 模拟环境。
- 参考价格：记录每个场所的指数价、标记价和外部价格状态，但不可成交的参考价不进入成交收益。

两个执行场所足以完成本期系统。第三个场所能把每个资产的配对从 1 个增加到 3 个，也能提供备用执行选择；代价是额外账户、资金、规则、费率和故障组合。当前 `$150` 资金不适合分散到三个执行账户。

### 策略范围

- 两腿主动成交：作为保守、可核验的基线。
- 一腿挂单、另一腿主动补对冲：基线完成后增加；必须使用真实排队、成交和逆向选择数据，不假定挂单必然成交。
- 主时间尺度：5 秒至 30 分钟。
- 当前跨场所永续默认按相对价值候选处理，不宣称严格无风险套利。

## 4. 学习验收

每天围绕一个核心能力验收，不机械重复“预测、审查、改规则、诊断故障”四个动作。当天至少需要：

1. 助手实现的关键代码与行为测试；
2. 与当天问题直接相关的真实输入和实际运行结果；
3. 一个能暴露理解差异的用户动作，由解释结果、审查关键函数、修改规则或诊断故障中择一；
4. 代码和当前证据仍不能证明的事实。

助手生成代码、测试或研究记录不等于用户掌握；反过来，用户已经能在新数据或新故障中正确使用当天知识时，不再追加模板练习。

## 5. Day12–21

| 日程 | 真实问题 | 当日唯一成果 | 通过条件 |
|---|---|---|---|
| Day12 | 怎样从两家官方目录取得原油市场，又不把目录、状态和盘口串错？ | 官方目录驱动的当前市场扫描器 | 保留完整市场身份；位置数组不会错配；活跃且有双边盘口只进入 Day13 |
| Day13 | 同名 RWA 为什么仍可能不可比较？ | 经济对象映射与价格状态分类器 | XAU/GOLD 休市定价差异不会被当成机会 |
| Day14 | 怎样连续取得可追溯的双场所行情？ | 锁定环境、两个只读数据客户端和服务器采集器 | 不配置执行客户端；重启后继续写新分段且不覆盖旧数据 |
| Day15 | 两边报价何时才属于同一可比较窗口？ | 时间、顺序、缺口和过期判断 | 断连、坏快照和超时会阻止比较，不靠插值制造同步报价 |
| Day16 | 屏幕价差扣除完整进出场后还剩多少？ | 两腿主动成交的共同数量、盘口成交均价和现金账本 | 两个方向、四次成交、费率、资金费和未成交数量全部可解释 |
| Day17 | 挂单未成交或两腿成交不同步时实际持有什么？ | 双腿状态机与挂单/补对冲模型 | 订单确认不等于成交；剩余敞口、超时和允许动作可以重放 |
| Day18 | 扫描很多候选后怎样避免只留下幸运赢家？ | 自动排名、人工选择和预先登记的研究方案 | 按时间切分、封存最终样本、保存全部尝试；不足时继续采集 |
| Day19 | 研究脚本怎样进入最终运行框架而不重写规则？ | NautilusTrader 确定性历史重放 | 相同输入两次得到相同事件、仓位、现金和决定 |
| Day20 | 实时数据中断或进程重启时系统是否仍可信？ | 实时行情、本地模拟成交和故障恢复报告 | 监督运行、四类故障注入；无法解释的差异进入停止状态 |
| Day21 | 没有分步提示时能否处理一个新候选？ | 闭卷迁移报告和最终决定 | 用户独立完成扫描、审查、规则修改、故障诊断与决定 |

每日详细任务见 `curriculum/day12.md` 至 `curriculum/day21.md`。

## 6. 四个阶段检查

### Day13：候选可以定义

- 完整交易标识、场所、产品类型和市场编号明确。
- 经济单位、价格来源、交易时段和当前价格状态可解释。
- 无法证明的字段保持未知。

### Day15：数据可以比较

- 原始事件不可变并有内容哈希。
- 源时间、接收时间、顺序和缺口分开记录。
- 断线两侧的数据不会被拼成一个报价。

### Day18：研究决定可信

- 所有扫描候选和参数尝试均被记录。
- 训练、选择和最终检验按时间发生，最终样本不会反复查看。
- 主动成交与挂单方案分开报告。

### Day20：系统可以实时模拟

- 历史重放与实时模拟调用同一套市场、成本和执行规则。
- 重连、过期、坏快照和重启都有明确停止或恢复结果。
- 没有执行客户端和真实订单调用路径。

## 7. 最小工程结构

只有重复使用且经过测试的逻辑进入正式包：

```text
src/monte_arb/
  market.py       # 市场身份、价格状态和共同数量
  candidate.py    # 淘汰原因、成本和排名
  execution.py    # 盘口成交、双腿状态和现金事件
  runtime.py      # 数据源与 NautilusTrader 接入
  cli.py          # scan / collect / replay / shadow
tests/
  fixtures/       # 固定测试数据：冻结的官方响应和事件序列
  replay/         # 确定性与故障场景
research/
  manifests/      # 清单：来源、参数、时间、版本和哈希
  runs/           # 每次运行结果
  decisions/      # 人工决定与未知项
```

不新增网页、消息队列、PostgreSQL 或微服务。采集先使用压缩 JSONL 保存原始事件，NautilusTrader 重放再写入 `ParquetDataCatalog`。只有恢复游标确实需要查询时才增加 SQLite。

## 8. 服务器与密钥

- 服务器使用独立非特权用户和独立数据目录；部署前先检查磁盘、时间同步和 Python/容器环境。
- 公开采集器不需要账户密钥。
- 账户只读核验在单独进程运行；输出只保存费率和必要的脱敏字段。
- 禁止在命令参数、Git、容器镜像、结构化日志和异常堆栈中出现密钥。
- 每个数据文件分段写入并设置总磁盘上限；删除策略只影响可重新采集的数据。

## 9. Day21 后的顺序

1. AX Exchange 模拟环境作为第三场所迁移测试。
2. 连续至少 7 天实时模拟，覆盖 RWA 外部市场关闭和恢复。
3. 测试环境验证下单、撤单、部分成交与账户恢复。
4. 用户再次明确授权后，才设计 `$150` 以内的人工值守主网实验。
5. 链上资产负债重构和本地 fork 重放另设课程。

## 10. 主要一手资料

- [Lighter RWA 市场规格](https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications)
- [Lighter RWA 定价机制](https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism)
- [Lighter WebSocket](https://apidocs.lighter.xyz/docs/websocket-reference)
- [Hyperliquid 永续市场接口](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals)
- [Hyperliquid HIP-3](https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-3-builder-deployed-perpetuals)
- [trade.xyz 规格索引](https://docs.trade.xyz/consolidated-resources/specification-index)
- [NautilusTrader 适配器列表](https://nautilustrader.io/docs/latest/integrations/)
- [NautilusTrader Lighter](https://nautilustrader.io/docs/latest/integrations/lighter/)
- [NautilusTrader Hyperliquid](https://nautilustrader.io/docs/latest/integrations/hyperliquid/)
- [NautilusTrader AX Exchange](https://nautilustrader.io/docs/latest/integrations/architect_ax/)

完整来源与用途见 `RESOURCES.md`。
