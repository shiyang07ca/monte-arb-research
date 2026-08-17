# Day12：当前市场身份与盘口配对

## 学习主题

从 Lighter 与 Hyperliquid `xyz` 的当前官方目录发现市场，保存完整市场身份，并证明目录记录、盘口请求与盘口响应属于同一市场。

## 实际完成

- 阅读并操作互动课程：`lessons/0008-day12-market-identity.html`。
- 使用真实只读扫描结果观察 341 个市场，其中 300 个保持 `catalog_only`、37 个因目录状态停止、4 个原油市场进入 `ready_for_market_mapping`。
- 理解 Lighter 的盘口响应本身不足以证明 symbol；必须把请求时的完整市场身份、`market_id`、请求参数和响应绑定，不能按并发返回顺序分配市场。
- 理解 Hyperliquid `metaAndAssetCtxs` 的 `universe` 与 contexts 按原始位置对应：先验证数组长度，再按原始 index 配对，最后才能过滤下架市场。
- 完成新场景迁移：当两个 Lighter 请求乱序返回且响应没有 symbol 时，仍选择在请求前构造完整身份，并与参数和响应绑定。
- 口头说明“如果先删除 `universe` 中的下架市场，两个数组就无法对齐”，正确指出静默错配的根因。
- Day12 冻结响应测试 14/14 通过；历史 `lab` 回归测试 27/27 通过。

## 关键理解

1. `ticker ↔ market_id` 是必要映射，但跨场所研究还必须保留：场所、产品类型、场所命名空间、完整交易标识和场所本地编号。
2. 位置数组的配对关系属于数据语义。只过滤其中一个数组会改变 index 含义，使后续市场获得相邻市场的上下文；价格仍可能合理，因此不能依赖肉眼发现。
3. `active + two_sided` 只允许进入 Day13 的市场映射，不证明两个场所的合约是同一经济对象，也不证明存在套利利润。

## 证据

- 课程：`lessons/0008-day12-market-identity.html`
- 参考卡：`reference/day12-market-identity.html`
- 扫描结果：`research/runs/day12-scan.json`
- 请求及原始响应清单：`research/manifests/day12-universe.json`
- 实现：`src/monte_arb/market.py`、`src/monte_arb/adapters.py`、`src/monte_arb/cli.py`
- 测试：`tests/test_day12_scan.py`

## 尚未证明

- `WTI` 与 `xyz:CL` 是否为同一经济对象；
- 两个 `BRENTOIL` 的单位、基准、月份、定价和结算是否一致；
- 目标数量能否成交以及扣除滑点、费用和资金费后是否盈利；
- 任何真实下单或资金安全结论。

## 下一步

Day13 核验四个原油市场的经济对象：单位、底层基准、合约月份、价格来源、交易时段和结算方式。只有确认可比性后，才能讨论跨场所价差。
