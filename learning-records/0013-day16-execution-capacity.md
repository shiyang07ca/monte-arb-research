# 0013 · Day16 可执行性与容量（v2 审查修订）

> 日期：2026-08-21
> 状态：已记录（工作台能力 v2 完成；用户研究动作待完成）
> 里程碑：Day16

## 背景

Day14 的首档候选不能回答“按我的规模，两腿能否以同一经济敞口成交，以及完成一轮进出后还剩什么”。Day16 初版加入 L2 走档和容量，但系统 review 发现其数量与 PnL 口径会改变研究结论，因此升级为 schema v2。

## 审查发现与修复

1. **双腿不能按相同 USD 独立取整。** 初版真实扫描有 521 行两腿目标数量不等，最大名义偏差约 $14.93（另一审查脚本按不同参考口径测得更大偏差）。v2 先求双方 `quantity_step × multiplier` 的共同网格，再取不超过预算的最大共同经济敞口；真实扫描不匹配归零。
2. **VWAP 价差不能再扣一次滑点。** 初版 `capture_bps` 已来自两腿 VWAP，却又减 `slippage_cost_bps`，重复计算盘口冲击。v2 将 `executable_spread_bps` 定义为目标共同敞口的 VWAP 价差，滑点只作 top-to-VWAP 分解。
3. **Hyperliquid 数量精度不能猜。** 适配器曾丢弃 metadata 的 `szDecimals`，执行层把 58 个市场全设为 2 位；v2 保留 metadata，真实市场分布恢复为 2–6 位。缺失时记录 `SIZE_PRECISION_UNKNOWN` 并排除。
4. **部分成交不能发布目标规模 PnL。** 两腿成交敞口不同，两个部分 VWAP 不代表目标规模执行。v2 保留 fill/unfilled/residual，但入场与费后 PnL 均为 null。
5. **退出必须关闭入场的同一敞口。** 初版往返按原 USD 在退出价重新算数量，价格变化时会少关或多关。v2 把入场 `common_exposure_units` 直接传给反向退出，并加回归测试。
6. **容量顶档是下界。** 最大测试档仍全成时显示 `≥ $1000`；只有出现首个失败档时才形成区间证据。
7. **刷新语义必须诚实且不能破坏最后成功数据。** 初版按钮只重读 JSON，却称“刷新”。当前默认 GET 当前快照；只有 `--live-refresh` 才真正运行市场扫描。成功结果通过临时文件、`fsync` 和原子替换发布；请求错误不会覆盖最后成功快照。全量采集约 100 秒，自动重扫默认关闭且使用 single-flight。
8. **运行模块按职责命名。** `execution_engine.py`、`candidate_workbench.py`、`workbench_app.py`、`workbench_views.py`、`market_event_*`、`depth_diagnostics.py` 与 `quote_collector.py` 替代 `dayX_*.py`；两个工作台页面固定为浅色模式。

## v2 真实证据

- 扫描 56 对 active pair / 112 本盘口 / 0 请求错误；inactive/delisted 市场在 discovery 阶段排除；
- 共同敞口不匹配：0；往返入场/退出敞口不匹配：0；部分成交伪 PnL：0；
- BRENTOIL：当前快照小规模入场接近 0，$500/$1000 转负；同盘口四次主动成交基线全档为负；
- AAPL、META、SPCX：某方向入场可成交价差为正，但同盘口往返仍为负；
- BOT：大规模方向部分成交，目标规模 PnL 为 null；
- HL 账户费率、持有期 funding、未来退出盘口和账户保证金仍缺失，因此研究状态为 No-Go。

## 证据路径

- `src/monte_arb/execution_engine.py`
- `src/monte_arb/adapters.py`
- `src/monte_arb/workbench_app.py`
- `tests/test_execution_engine.py`
- `research/runs/day16-execution-scan.json`
- `lessons/0012-day16-execution-capacity.html`
- `reference/day16-execution-capacity.html`

## 未完成

- 用户尚未选择 AAPL / META / SPCX 的方向和规模并解释入场与往返差异；
- 账户实际费率、指定持有期 funding、未来退出 L2 尚未接入；
- 在这些证据齐备前，不把任何正入场价差列为可交易机会。
