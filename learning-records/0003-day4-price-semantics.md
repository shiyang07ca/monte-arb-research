# Day 4 学习记录 / 价格语义

## 学习主题

区分 `oracle_price`、`index_price`、`mark_price`、`candle_close`、`mid_price`、`trade_price`、`bid` 和 `ask` 的来源与用途；理解 RWA oracle stale 后内部 impact price 与 EMA 的转换；避免把估值价格当作可实现现金 PnL。

## 今天实际完成

- 阅读并核验 Lighter 官方 RWA Pricing Mechanism、Fair Price Marking、PnL And Total Account Value 和 RWA Market Specifications 文档。
- 创建并打开互动课程：`lessons/0003-day4-price-semantics.html`。
- 创建打印版参考卡：`reference/day4-price-semantics.html`。
- 创建可复用交互组件：`assets/day4-price-semantics.js`，包含 EMA 计算、快照差异、mark 估值 PnL 与 bid/ask 平仓 PnL 对比、5 题验收。
- 从真实本地 `orderBookDetails` 快照提取价格字段：WTI mark `74.692`、index `74.670`、last trade `74.677`；BRENTOIL mark `79.03`、index `79.04`、last trade `79.01`。
- 明确当前 raw 快照没有直接提供 `oracle_price`、`mid_price`、`bid`、`ask`、`oracle_state` 和 `source_timestamp`，这些字段保持 `unknown`。
- 在浏览器中完成交互验证：切换到 BRENTOIL、将 EMA 的 τ 改为 2 分钟、切换空头 PnL 场景，并将价格语义验收答为 `5/5`。
- 实际运行 `python3 lab/day4_price_semantics.py`，输出快照字段、EMA index/mark 示例和 mark/盘口平仓 PnL 对比。
- 实际运行 `python3 -m unittest lab.test_day4_price_semantics -v`，4 个测试通过；同时运行 Day 3 的 4 个测试，全部通过。

## 关键理解

- 立即买入用 ask 方向估算，立即卖出用 bid 方向估算；目标数量还必须沿盘口走档，不能只拿 top-of-book 一个数字。
- `mark_price` 用于公平估值、未实现 PnL 和清算相关语义；不等于立即平仓的现金结果。
- 当前课程纸上例子：entry `75.00`、mark `75.03`、bid `74.90`、ask `75.10`、多头数量 `1` 时，mark 未实现 PnL 为 `+$0.03`，按 bid 立即卖出为 `-$0.10`。
- oracle stale 时，外部 oracle 权重衰减，内部订单簿 impact price 权重上升，并使用时间加权 EMA；当前官方页面列出的来源权重切换时间常数 `τ_mark=1` 分钟、`τ_index=1` 分钟。内部 EMA 平滑时间常数为 index `τ=30` 分钟、mark `τ=2` 分钟。外部价格恢复时内部价格会即时向其收敛。
- 两组时间常数回答不同问题：来源切换的 τ 决定“信谁”，EMA 的 τ 决定“内部价格反应多快”；它们不是成交延迟或市场关闭时间。
- 字段不存在时写 `unknown`，不能用 mark、last trade 或插值伪造 oracle/bid/ask/mid。

## 主动回忆验收

用户能够复述：

1. `oracle stale` 表示外部价格源没有及时更新，不表示资产没有价格。
2. stale 后需要逐步调整价格来源并平滑内部价格，避免参考价格突然跳变；这可能降低突发估值/清算冲击，但不等于保证绝对公平。
3. 观察到价差时，必须先排除两边价格机制状态不同的可能性。

关键纠正：在“WTI fresh、BRENTOIL stale”的例子中，核心原因是两边的 oracle 新鲜度和价格来源权重不同，不应直接归因于不同交易窗口或不同 EMA 公式。相同价格类型的 EMA 参数可能相同；不同的内部 impact 输入和 oracle/internal 权重也足以造成不同价格。交易窗口是另一个需要独立证据的时间问题。

## 证据位置

- `lessons/0003-day4-price-semantics.html`
- `reference/day4-price-semantics.html`
- `assets/day4-price-semantics.js`
- `notes/price-semantics.md`
- `lab/data/day4_price_semantics_snapshot.json`
- `lab/day4_price_semantics.py`
- `lab/test_day4_price_semantics.py`
- `lab/data/lighter_rwa_raw/145_orderBookDetails.json`
- `lab/data/lighter_rwa_raw/159_orderBookDetails.json`
- `RESOURCES.md`

## 研究边界与未完成项

- 本地一次市场详情快照不提供连续 oracle freshness/state、完整 bid/ask 深度、mid、成交历史语义或实际成交结果。
- mark/index 差异只能作为描述性快照事实，不能直接写成可交易价差或策略 PnL。
- funding 现金流、展期状态、历史覆盖、目标数量进出和权限/清算仍未闭合。
- 本阶段没有连接账户、私钥或发送真实订单。

## 下一步

Day 5：建立 WTI/BRENTOIL 的展期与市场时段模型，把 UTC 时间转换为美国东部时间，标记不同 roll window 和 market-closed window，避免把时间错位误判为相对价值信号。
