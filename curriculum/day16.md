# Day16：可执行性与容量

> 状态：工作台能力 v2 已实现并验证（2026-08-21）；用户研究动作待完成
>
> 里程碑允许跨多个工作日

## 已实现

- 冻结 L2 走档：`walk_book`、`leg_execution`、`pair_execution`、`round_trip_execution`、容量下界与 CLI 扫描；
- 两腿使用共同合法经济敞口：数量精度、最小数量、最小名义和 contract multiplier 均进入约束；找不到共同数量时阻断，不留下隐藏 delta；
- Hyperliquid `szDecimals` 从 metadata 保留到执行规格，不再统一猜成 2；
- 口径拆分：首档价差、入场可成交 VWAP 价差、盘口冲击分解、四次主动成交基线、已知费用和缺失证据；VWAP 已包含盘口冲击，不重复扣减；
- 部分成交保留未成交量与残余敞口，但不发布目标规模 PnL；
- 容量最大测试档仍全成时显示 `≥ $X`，不冒充精确容量；
- 工作台 `/workbench/execution` 支持 pair/方向/规模、容量、冻结盘口自定义规模与显式市场重扫；默认只读，`--live-refresh` 才真正重新请求交易所；两个工作台页面固定使用浅色模式；
- 扫描快照使用临时文件、`fsync` 与原子替换发布；有请求错误时保留最后成功快照；前端重扫使用 single-flight，避免长扫描重入；
- 源码按职责命名为 `execution_engine.py`、`candidate_workbench.py`、`workbench_app.py`、`workbench_views.py`、`market_event_*`、`depth_diagnostics.py` 与 `quote_collector.py`，不再用课程日次命名运行模块；

## 真实扫描证据

- `research/runs/day16-execution-scan.json`：扫描 56 对 active pair、112 本盘口、0 请求错误；inactive/delisted 市场在 discovery 阶段排除；全市场顺序采集约 100 秒；
- v2 不变量检查：共同敞口不匹配 0；往返入场/退出敞口不匹配 0；部分成交仍输出目标 PnL 0；
- BRENTOIL 当前快照：小规模入场价差接近 0，$500/$1000 转负；同一冻结盘口四次主动成交基线全档为负；
- AAPL / META / SPCX 某方向入场可成交价差仍为正，但同盘口往返结果为负，因此“正入场价差”不是完整可交易利润；
- BOT 大规模一个方向部分成交，结果只保留 fill、unfilled 与 residual，不给目标规模 PnL；
- Hyperliquid HIP-3 账户实际费率、指定持有期 funding、未来退出盘口仍缺失，费后/完整现金结果保持未知。

## 用户研究动作（待完成）

- [ ] 从 AAPL / META / SPCX 中选择一个正入场方向与研究规模；
- [ ] 解释为什么同盘口往返结果仍为负，以及哪两个主动成交属于退出；
- [ ] 说明持有 1 天后需要重新取得的 funding、未来退出 L2、账户实际费率与保证金证据。

## 完成条件核对

- [x] 多个规模、两个方向可从冻结 L2 重算；
- [x] 两边共同合法数量、最小名义、精度和 multiplier；
- [x] 开仓与退出四次主动成交的冻结盘口基线；
- [x] 深度不足保留未成交数量，不发布伪目标规模 PnL；
- [x] mark/oracle/mid 不替代成交价；
- [x] 未知账户费率与 funding 不填 0；
- [x] 当前结果、容量下界与缺失证据分开；
- [ ] 用户完成真实候选解释与迁移验收；
- [ ] 账户实际费率、持有期 funding 和未来退出盘口接入后，才能形成完整现金区间与交易吸引力榜特征。

## 下一步

先完成本页用户研究动作。随后 Day17 做机制区分实验；Day19 再把第二腿延迟、拒单、撤单和补对冲建成事件回放，不在 Day16 的冻结盘口容量模型中伪装解决。
