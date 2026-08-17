# 永续套利研究与 NautilusTrader 资源

> 最近核验：2026-08-17。动态市场规则和 API 响应必须在使用当天重新获取。

## 一手知识资料

### 课程背景

- [链上套利残酷共学主页](https://intensivecolearn.ing/programs/b43d2e97-ed88-4ca3-b12f-7ef672b01205)
  用于理解 21 天共学的范围和提交节奏。课程提纲不是交易规则，也不决定本仓库的毕业标准。
- [ICL Agent API OpenAPI](https://intensivecolearn.ing/api/v1/openapi.json)
  用于取得当前参与者有权访问的课程提交。原始群友内容不写入仓库，只保存去标识化研究摘要。

### Lighter 官方资料

- [RWA 市场规格](https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications)
  用于核对经济对象、oracle 和当前市场说明。页面明确参数可能变更；原油月份文字需要与实时响应和公告再次验证。
- [RWA 定价机制](https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism)
  用于实现外部价格失效后的内部价格、EMA 和来源切换状态。
- [Funding](https://docs.lighter.xyz/trading/funding)
  用于计算当前资金费公式、方向和支付价格；账户现金结果仍需账户记录验证。
- [交易费用](https://docs.lighter.xyz/trading/trading-fees)
  用于读取账户层级的费用和延迟；零显式费用不代表零买卖价差、冲击或等待成本。
- [Order Books](https://apidocs.lighter.xyz/reference/orderbooks)
  用于核对 symbol、market id、最小基础数量、最小报价金额与价格/数量精度；这些字段必须共同验证。
- [WebSocket Reference](https://apidocs.lighter.xyz/docs/websocket-reference)
  用于订单簿快照/增量、nonce 连续性、heartbeat 和重连测试。
- [Order Book Orders](https://apidocs.lighter.xyz/reference/orderbookorders)
  用于 REST 盘口快照和目标数量走档；返回没有足够事件时间信息，不能代替持续 WebSocket 采集。
- [Rate Limits](https://apidocs.lighter.xyz/docs/rate-limits)
  用于设置读取和交易请求上限、退避与恢复测试。

### Hyperliquid 与 trade.xyz 官方资料

- [HIP-3 builder-deployed perpetuals](https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-3-builder-deployed-perpetuals)
  用于理解独立 DEX、部署者管理的市场定义和 oracle、隔离保证金及 HIP-3 费用差异。
- [Hyperliquid Info API](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint)
  用于获取 perp DEX 列表、instrument、L2、candle、funding 和持仓状态。
- [Hyperliquid Perpetuals Info API](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals)
  用于分别获取标准永续与指定 HIP-3 DEX 的 `metaAndAssetCtxs`；HIP-3 查询必须保留 DEX 命名空间。
- [Hyperliquid Asset IDs](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids)
  用于按当前 `perpDexs` 顺序和 `index_in_meta` 计算 HIP-3 资产编号，并保留 `{dex}:{coin}` 完整名称。
- [Hyperliquid 费用](https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees)
  用于按账户等级和 HIP-3 附加费用计算交易成本，不使用硬编码费率。
- [Hyperliquid 订单错误](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/error-responses)
  用于最小 `$10` 名义、保证金、reduce-only、流动性和持仓上限失败测试。
- [trade.xyz 商品规格](https://docs.trade.xyz/asset-directory/commodities)
  用于区分贵金属现货价格与能源商品期货价格，并核对外部交易时段。
- [trade.xyz Specification Index](https://docs.trade.xyz/consolidated-resources/specification-index)
  用于在同一张当前规格表中核对 GOLD、SILVER、CL 与 BRENTOIL 的单位、底层、时段、杠杆和价格发现边界。
- [trade.xyz Oracle Price](https://docs.trade.xyz/perp-mechanics/oracle-price)
  用于实现外部和内部价格状态及内部价格更新公式。
- [trade.xyz External Price](https://docs.trade.xyz/perp-mechanics/external-price)
  用于理解外部市场关闭后的固定外部价格、内部价格和 discovery bounds。
- [trade.xyz Roll Schedules](https://docs.trade.xyz/consolidated-resources/roll-schedules)
  用于原油等期货型候选的合约月份和展期权重。静态页面目前仍含旧月份，不能单独证明当前底层合约。

### NautilusTrader 官方资料

- [NautilusTrader PyPI](https://pypi.org/project/nautilus-trader/)
  用于核验稳定版本、Python 版本范围和发布产物；课程固定精确版本，不使用未锁定的 nightly/develop wheel。
- [Hyperliquid 集成](https://nautilustrader.io/docs/latest/integrations/hyperliquid/)
  用于 HIP-3 instrument、L2、funding、订单、账户状态、重连和对账实现。
- [Lighter 集成](https://nautilustrader.io/docs/latest/integrations/lighter/)
  用于 L2、bar、mark/index/funding、订单和账户状态；先运行官方 data tester，再接入课程代码。
- [Data](https://nautilustrader.io/docs/latest/concepts/data/)
  用于 `ParquetDataCatalog`、自定义数据和历史/实时数据语义。
- [Backtesting](https://nautilustrader.io/docs/latest/concepts/backtesting/)
  用于确定性历史重放和避免未来数据进入 Strategy。
- [Live trading](https://nautilustrader.io/docs/latest/concepts/live/)
  用于实时节点、缓存、启动与持续对账、重连和恢复。
- [Execution](https://nautilustrader.io/docs/latest/concepts/execution/)
  用于订单事件、风险检查和 `ACTIVE/HALTED/REDUCING` 运行状态。
- [AX Exchange 集成](https://nautilustrader.io/docs/latest/integrations/architect_ax/)
  用于 Day21 后的第三场所迁移评估。它覆盖黄金、白银、能源和股票等 RWA 永续，但使用整数合约，个人生产账户存在准入限制；当前课程不接入。

### 开源实现

- [NautilusTrader v1.231.0 Lighter adapter](https://github.com/nautechsystems/nautilus_trader/tree/v1.231.0/crates/adapters/lighter)
  用于核验课程锁定版本中实际存在的 Lighter 数据与执行实现；开发分支示例不能替代稳定标签检查。
- [NautilusTrader Hyperliquid data tester](https://github.com/nautechsystems/nautilus_trader/blob/v1.231.0/examples/live/hyperliquid/hyperliquid_data_tester.py)
  用于建立只读数据 smoke test；课程不配置 execution client。
- [Lighter 官方 Python SDK paper client](https://github.com/elliottech/lighter-python/tree/main/lighter/paper_client)
  用于审查本地撮合、账户和风险模拟的边界；不直接复制为跨场所执行模型。
- [Hummingbot cross-exchange market making](https://github.com/hummingbot/hummingbot/blob/master/hummingbot/strategy/cross_exchange_market_making/cross_exchange_market_making.py)
  用于参考成熟项目如何分离 maker 与 hedge 市场、订单追踪和未对冲风险；具体规则必须在本仓库用当前场所数据验证。
- [Hyperliquid 官方 Python SDK](https://github.com/hyperliquid-dex/hyperliquid-python-sdk)
  用于对照资产查询和请求编码；市场定义以 Info API 当前响应为准。
- [LI.FI SDK](https://github.com/lifinance/sdk)
  用于后续跨链 quote、transaction 和 status 的 dry-run 研究，不在当前 perp 主线中接入。

### 统计研究原始资料

- [Engle & Granger, 1987](https://doi.org/10.2307/1913236)
  协整与误差修正的原始论文。用于理解检验假设，不用于直接宣称可交易收益。
- [Gatev, Goetzmann & Rouwenhorst：Pairs Trading](https://www.nber.org/papers/w7032)
  经典 pairs trading 研究。用于比较研究设计、组合形成期和交易期，不照搬阈值。
- [White, 2000：Reality Check for Data Snooping](https://doi.org/10.1111/1468-0262.00152)
  用于处理多次尝试后只报告最好结果的问题。
- [Bailey et al.：Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)
  用于理解短样本、多参数和模型选择带来的回测过拟合风险。

### 学习方法原始资料

- [Roediger & Karpicke, 2006](https://pubmed.ncbi.nlm.nih.gov/16507066/)
  支持用延迟主动回忆检验保持，而不是把重复阅读产生的熟悉感当作掌握。
- [Cepeda et al., 2006](https://pubmed.ncbi.nlm.nih.gov/16719566/)
  支持把关键概念分散到后续执行、统计和迁移任务中重复使用。

## 社区经验

- [共学课程群组](https://intensivecolearn.ing/programs/b43d2e97-ed88-4ca3-b12f-7ef672b01205)
  用于收集其他学习者的失败经验、候选和实测问题。群友结论先记录为待验证假设，再用官方规则与可复现实验检查。
- [NautilusTrader GitHub Discussions](https://github.com/nautechsystems/nautilus_trader/discussions)
  用于确认适配器实践问题和运行经验；具体行为最终以当前版本代码、官方文档和本地测试为准。

## 动态证据

仓库中的 API 文件只描述抓取时刻：

- `lab/data/lighter_rwa_capture_manifest.json`
- `lab/data/day8_capture_manifest.json`
- `lab/data/day9_raw/day9_capture_manifest.json`
- `lab/data/day9_parameter_diff.json`

后续 XAU/GOLD、XAG/SILVER 与 BTC/ETH 数据必须保存获取时间、参数、HTTP/WS 状态、原始引用和内容哈希。

## 当前缺口

- 已审查最新 40 条群友笔记并写入去标识化摘要；这是短时间便利样本，原始内容不保存，群友结论仍需独立复现。
- Lighter 与 trade.xyz 的静态原油页面不足以证明当前合约月份和展期权重，原油候选暂不进入主研究。
- 两个平台没有可直接取得的长周期历史 L2 数据；执行研究依赖从 Day 13 开始的自建采集。
- 尚未验证当前账户费率、限流、保证金设置和真实 funding 账本。
- 尚未完成 NautilusTrader 两个适配器在本仓库锁定版本上的数据、重连和状态恢复测试。
