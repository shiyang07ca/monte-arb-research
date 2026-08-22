# 研究操作台详细设计

> 版本：2026-08-22
>
> 状态：当前实现依据
>
> 真实订单：禁止

## 1. 产品目标

构建一个持续运行、可扩展、可二次开发的只读市场机会研究操作台：

```text
查看数据健康与市场版图
→ Screener 发现异常关系
→ 进入专题分析历史与机制
→ 验证指定规模执行摩擦
→ 导出可复现数据
→ 把结论转化为下一轮扫描、诊断或回放能力
```

产品不按课程 Day 拆页，不要求用户先填写解释再解锁功能。共学内容来自真实模块中的经济对象、统计方法、执行机制和证据边界。

## 2. 路由与职责

```text
/workbench
  Dashboard：模块导航、主研究摘要、数据健康

/workbench/markets
  全市场 Screener：发现与筛选

/workbench/oil
  Brent–WTI 专题：历史、冻结模型、机制诊断、执行摩擦

/workbench/funding
  Funding 矩阵、历史与持有成本

/workbench/execution
  跨场所执行成本与深度

/workbench/tools/spread
  任意两腿研究工具

/workbench/data
  数据覆盖、schema、来源、任务和导出
```

Dashboard 负责发现和导航；专题模块负责深入验证。原始 JSON 不是主页面内容，只作为稳定 API 和下载产物。

## 3. 领域对象

### MarketIdentity

```text
venue + product_type + namespace + full_symbol + local_id
```

### PriceSource

场所、产品、价格含义、采样方法和时间语义相同的一组观察。K 线收盘、指数、mark、L2 和 RFQ 必须分开。

### SynchronizedObservation

同一价格源内按明确时间规则组成的双腿记录。缺一腿即保持缺失；不使用未来值或无声明前值填充。

### PairDefinition

描述两腿、方向、权重、经济关系和当前证据。Brent–WTI 是跨标的相对价值，不能复用“同经济对象完全对冲”的语义。

### FrozenModel

只在形成窗口估计并保存参数的数据版本化模型；验证窗口不参与重拟合。

### Diagnostic

确定性证据摘要，包含：

```text
code
severity
evidence
counter_evidence
limitations
next_check
```

诊断缩小研究范围，不是因果或交易结论。

### ExecutionEstimate

指定场所、方向、数量和执行机制下的进入/退出摩擦。L2、RFQ 和公式模型必须分别标识。

### ResearchProjection

计算模块与 HTTP/UI 之间的稳定接口。页面不解析场所原始响应，也不重新实现分析逻辑。

## 4. 数据分层

```text
官方 REST/WS 或明确授权的只读导入
        ↓
Raw Capture（Git 外、追加式、带 SHA-256）
        ↓
保留场所语义的 PriceSource
        ↓
同步观察与数据健康
        ↓
分析模块与机制诊断
        ↓
ResearchProjection
        ↓
HTTP、浏览器、JSON/CSV、CLI
```

约束：

- 每个数据源独立记录最新时间、覆盖、缺口和错误；
- 大型运行时投影可重算且不提交 Git；
- 日线缺口必须接入交易所日历后才能判断；
- 失败源不会使其他价格源被丢弃或替换成零；
- Variational 仅导入 `monte-fox` 的 `market_observation`，忽略账户和执行事件。

## 5. Brent–WTI v1

当前价格源：

- Lighter WTI/BRENTOIL 1h K 线与当前 L2；
- Hyperliquid `xyz:CL`/`xyz:BRENTOIL` 1h K 线与当前 L2；
- Variational index/RFQ 的本地只读录制导入；
- 外部连续期货日线长期背景。

核心指标：

```text
spread_usd = Brent − WTI
ratio = Brent / WTI
log_ratio = ln(Brent) − ln(WTI)
residual = ln(Brent) − alpha − beta × ln(WTI)
```

机制诊断至少覆盖：

- 当前残差和按时间验证窗口；
- 最近 24 个同步点的两腿贡献；
- UTC 小时时段代理；
- venue 对数比值分歧；
- roll、funding 和数据健康的已知结果或证据缺口；
- 指定规模执行摩擦和未知费用。

执行表当前只提供 1:1 场所数量的 L2 摩擦基线。冻结模型 beta、合约乘数或经济权重未经核验时，不能称为 beta 对冲、经济中性或策略 PnL。

## 6. 后续模块

### 全市场 Screener

三个独立研究视图：

1. 同标的跨场所；
2. 跨标的相对价值；
3. 跨场所 funding。

Screener 展示原值、数据质量和排除原因，不以单一黑箱分数给出交易信号。

### Funding

保留每个 venue 的原生费率、结算间隔和下次边界；统一时间单位只用于比较。历史模块累计真实现金流，而不是只展示夸张 APY。

### Spread Grapher

从 Brent–WTI 专题抽出成熟的 `PairDefinition`、同步器、冻结模型和图表后，再允许任意两腿配置，避免先做一个经济语义错误的画图壳。

### Replay

历史入场、退出、机会寿命、部分成交、第二腿延迟和补对冲属于 Day18–19 的独立回放模块，不伪装在冻结盘口模型中解决。

## 7. 安全边界

- Web 应用不注册 execution client；
- 没有 order/trade/execute HTTP 路由；
- 不读取钱包、签名或 API 密钥；
- 账户只读核验必须独立运行并默认脱敏；
- 当前研究结果不自动发送真实订单。

## 8. 验证

每项纵向功能至少验证：

1. 研究投影的确定性行为；
2. HTTP 页面和 JSON/CSV；
3. 真实公开数据采集；
4. 浏览器桌面和窄屏；
5. 控制台无 JavaScript 错误；
6. 数据新鲜度、未知项和只读边界；
7. 全仓回归和两轴代码审查。

更完整的产品路线见 `docs/product/research-console.md`，油专题参数见 `docs/product/oil-relative-value-v1.md`。
