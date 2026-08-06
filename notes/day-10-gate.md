# Day 10 证据闸门模板

> 本文件是 Day 10 使用的填写模板。没有证据的格子必须写 `blocked` 或 `unknown`，不能用“看起来合理”代替。

## 闸门表

| 闸门 | 状态 | 证据路径 | 仍未知的内容 | 下一步 |
|---|---|---|---|---|
| 经济对象与数量 | `blocked` | `notes/rwa-contract-model.md`、`lab/data/lighter_rwa_instrument_matrix.json` | 成交/账户账本语义 | 补成交回放 |
| 价格源、index、mark | `blocked` | `notes/price-semantics.md`、官方 RWA/Fair Price 文档 | 历史 oracle freshness 和同一时点价格字段 | 补字段采集 |
| 展期与市场时段 | `blocked` | `notes/rwa-roll-and-session-model.md` | 完整关闭/恢复和逐日滚动状态 | 增加状态字段 |
| Funding 现金流 | `blocked` | `notes/funding-ledger-model.md`、funding 原始 JSON | API 字段到账户现金账本 | 纸上账本/受控核验 |
| 历史覆盖 | `blocked` | `lab/data/lighter_rwa_data_audit.json` | 多种市场状态和长期覆盖 | 连续补采 |
| 目标数量开平仓 | `blocked` | `lab/data/lighter_rwa_raw/` | 连续盘口、部分成交、退出滑点 | 执行回放 |
| 权限、保证金、清算 | `blocked` | 官方合约/清算/保证金文档 | 当前账户和地区资格 | 只读核验 |

## 当前决策

- 学习方向：`Go`；
- 统计/策略研究：`Blocked`；
- 真实执行：`No-Go`。

## Day 10 退出问题

### 学习问题

- 能否解释每个阻断项？
- 能否从原始证据复现一项数字？
- 能否指出代码中一个没有未来信息泄漏的地方？
- 能否写出一个单腿失败后的停止动作？

### 策略问题

- 价格语义是否闭合？
- funding 是否已进入现金账本？
- 目标数量开仓和平仓是否都有走档证据？
- 测试集结果是否在压力情景下仍为正？

任何一个关键问题回答为“未知”，策略不得进入 `Go`。

## 分支选择

- 历史不足：选分支 A，继续采集和审计；
- 统计关系不稳定：选分支 B，记录 `No-Go`；
- 统计关系有信号但执行未知：选分支 C；
- 关键字段全部有证据：选分支 D，做冻结参数的样本外纸上回放。

第 21 天只总结和复盘，不自动授权真实交易。
