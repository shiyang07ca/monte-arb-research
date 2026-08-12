# Day 9–21 课程重构设计（v7）

> 版本：2026-08-12
> 状态：Day 9–14 定稿；Day 15–21 在执行核心完成后细化。
> 依据：用户 19 问访谈 + Lighter/NautilusTrader 官方一手资料。

## 设计原则（用户访谈结论）

1. 每天一个 30–45 分钟单元；以真实市场现象开头，用户先提出解释，再验证。
2. 主线：Lighter WTI–BRENTOIL；先建立“提出+否定机会”的筛选流程，不预设机会。
3. 最终交付：桌面纸上交易回放系统（真实盘口数据模拟成交，不连接任何下单接口）。
4. 切换备用场景唯一条件：完成否定报告 + 至少一个不可修复的执行障碍。
5. 否定结论只作中间检查，不单独计成果。
6. 测试组织：单元测试 + 回放验收测试，结果必须可复现（同一输入同一输出）。
7. Lighter 账户只读使用；不执行真实交易。

## 一手资料事实（2026-08-12 已核验）

### Lighter 官方机制

- WTI（market_id=145）：commodity RWA 永续，OI 上限 25M；BRENTOIL（159）：OI 上限 100M。
- 价格参考逐日滚动：WTI 每天 17:30 ET、BRENTOIL 19:00 ET；每天 20% 从前月切到次月。
- 官方 2026 滚动映射：WTI `Q6→U6→V6→X6→Z6→F7→G7`；BRENTOIL `U6→V6→X6→Z6→F7→G7→H7`。
- Funding：每小时结算；`fundingRate = clamp(premium, −4%, +4%) / 8`；|premium|≤5bp 时按利率 1bp/8h 兜底；支付 = −position × index × fundingRate。
- Mark：Impact Notional=500 USDC/IMR；Mark=Median(ImpactPrice, index+EMA₈ₘᵢₙ(clamp(impact−index, ±0.5%)), median(CEX marks))。
- 2026-07-10 起 WTI/BRENTOIL 等 29 个市场取消 mark 上限，仅保留跨场所一致性校验。
- 保证金：IMR > MMR > CMR；清算瀑布：Pre-liquidation → Partial → Full → ADL；零价公式公开。
- 费率：Standard 账户 0 费用（taker 300ms）；Premium/Plus 按质押分档。
- 只读接口：orderBookDetails / orderBookOrders（limit 1–250 必填）/ orderBooks / candles（≤500 根）/ fundings（≤750 条）/ trades / market_stats / export（需鉴权，12 个月）。
- WebSocket：`wss://mainnet.zklighter.elliot.ai/stream`；order_book 频道订阅即全量快照+增量（50ms 批，begin_nonce↔nonce 连续性校验）；2 分钟无帧断连。
- 官方 SDK：github.com/elliottech/lighter-python 含 `paper_client/`（纸上交易实现）。

### 参数事实（2026-08-05 快照，Day 9 需重新核验）

- WTI：multiplier=1，min_base_amount=0.100，size_decimals=3，price_decimals=3，IMR=500（5x），MMR=300，CMR=200，maker/taker fee=0。
- BRENTOIL：multiplier=1，min_base_amount=0.0800，size_decimals=4，price_decimals=2，IMR=666，MMR=300，CMR=200，maker/taker fee=0。
- 两腿 funding_premium_multiplier=50、clamp_small=0.05、clamp_big=4.0、base_interest_rate=0.0032。

### 关键缺口（阻止交易结论，不阻止纸上回放）

- 无历史盘口深度存档（REST 仅实时快照，WS 需自建采集）→ 回放只能基于自建采集数据。
- 无历史 index 序列导出端点 → index 历史需自采 market_stats。
- funding 的账户账本语义未与真实账户核验。
- candle timestamp 是区间开始还是结束未知。

### NautilusTrader（Day 18 起引入）

- 事件驱动 + 确定性时间模型；backtest / sandbox / live 共用同一核心与策略代码。
- 回放用 BacktestEngine + 内置数据管线 + 订单/成交语义；sandbox 仅作演示，不连接真实下单。
- 只采用最小子集；不替代交易经济学研究。注意 Python 版本与 v1/v2 迁移风险。

## Day 9–14 执行核心（定稿）

### Day 9｜参数重新核验

- 现象：官方文档未公布 WTI/BRENTOIL 杠杆/保证金，旧矩阵是 2026-08-05 快照。
- 你的问题：为什么不能直接相信旧的 instrument matrix？
- 动作：重新抓取 `GET /api/v1/orderBooks` 与 `orderBookDetails?market_id=145/159`，核对参数，更新 `lab/data/lighter_rwa_instrument_matrix.json`。
- 产出：新矩阵 + 参数差异表 + `notes/day9-parameter-recheck.md`。

### Day 10｜实时盘口采集

- 现象：REST 盘口快照没有公共时间戳；历史盘口深度不存在。
- 你的问题：Lighter 盘口时间应该怎么处理？
- 动作：WebSocket 订阅 `order_book/145`、`order_book/159`，保存全量快照+增量，用 begin_nonce↔nonce 校验连续性；落盘原始帧。
- 产出：`lab/data/live_order_book/` 原始帧 + 连续性检查脚本。

### Day 11｜目标数量走档

- 现象：同一价格档 Lighter 显示剩余数量（订单级），Binance/Hyperliquid 是聚合档。
- 你的问题：0.635 代表什么？为什么不能当聚合总量？
- 动作：`$10/$20/$50/$100` 名义双腿走档：VWAP、未成交数量、冲击、开仓/平仓分开。
- 产出：`lab/replay/walk_book.py` + 走档结果 CSV。

### Day 12｜funding 与 mark 公式验证

- 现象：官方公式 funding = clamp(premium, ±4%) / 8；mark 钳制 ±0.5%。
- 你的问题：premium 只有 3bp 时 funding 是多少？为什么“看起来的价差”不能直接当收益？
- 动作：实现公式，与 `market_stats` 实际值对照；写出“机制钳制”否定案例。
- 产出：`lab/formulas/funding_mark.py` + 对照表。

### Day 13｜完整现金账本

- 现象：展期期间价格参考每天换 20%。
- 你的问题：展期窗口里价差变化是机会还是噪音？
- 动作：开仓+持仓+平仓+费用+资金费+失败预留的完整现金账本；按目标名义计算净现金。
- 产出：`lab/replay/cash_ledger.py` + `notes/day13-cash-ledger.md`。

### Day 14｜双腿状态机与单腿失败

- 现象：两腿一个成交一个没成交。
- 你的问题：系统下一步应该做什么？
- 动作：双腿状态机（开仓/部分/失败/退出）+ kill switch 条件写死；单腿失败演练。
- 产出：`lab/replay/leg_state_machine.py` + 失败场景测试。

### Gate B（Day 14 末）

- 目标规模净现金回放必须完整，否则保持 `Paper-only / Blocked`。
- 结论写入 `notes/day-14-gate.md`，与学习完成状态分开报告。

## Day 15–21（执行核心完成后细化）

- Day 15–17：候选机会筛选流程（提出→否定→容量检查）。
- Day 18：NautilusTrader 最小回测引入（安装 + 首个确定性回放）。
- Day 19：筛选流程接入回放流水线。
- Day 20：可复现性验收（换范围/换参数重跑 + 结果哈希一致）。
- Day 21：最终答辩 `final-paper-replay.md` + `next-cycle-decision.md`。

## 学习单元统一结构

```text
01 现象（真实数据/截图）
02 你先回答："你认为为什么？"（不查资料）
03 必要最小知识（只讲验证所需）
04 你改一处参数/规则并运行
05 对照结果验证
06 一句话结论：今天证明了什么、不能证明什么
```

## 边界

- 课程只做桌面纸上回放；不连接任何下单接口；不发送真实订单。
- Lighter 账户仅只读核验（资金费/成交语义），凭据不入仓库。
- 任何未知字段保持 unknown，不填零、不插值、不冒充。
- 平台打卡完成 ≠ 研究结论成立；两者分开报告。
