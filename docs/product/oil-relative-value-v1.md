# Brent–WTI 相对价值模块 v1 设计

> 对应规格：`.scratch/brent-wti-relative-value/spec.md`
>
> 状态：v1 已实现并验证

## 1. 研究问题

本模块不问“Brent 比 WTI 贵多少是否能立即套利”，而是依次回答：

1. 当前两种原油基准在各价格源中的关系是什么；
2. 这种关系相对同一价格源自身历史有多异常；
3. 变化主要来自哪条腿、时段、展期或价格机制；
4. 指定规模进入和退出时，盘口/RFQ 摩擦有多大；
5. 还缺什么证据，不能得出什么结论。

## 2. v1 价格源

| key | 场所/来源 | 数据 | 价格含义 | v1 状态 |
|---|---|---|---|---|
| `lighter` | Lighter | WTI/BRENTOIL 1h K 线、当前 L2、公开 funding | perp K 线收盘与订单簿 | 实时采集 |
| `hyperliquid` | Hyperliquid `xyz` | `xyz:CL`/`xyz:BRENTOIL` 1h K 线、当前 L2、上下文 | HIP-3 perp K 线收盘与订单簿 | 实时采集 |
| `variational_rfq` | Variational Omni | `monte-fox` 脱敏 `market_observation` | 指定数量指示性 RFQ 中点 | 有本地录制时导入 |
| `variational_index` | Variational Omni | 同一导入记录中的 `index_price` | 平台经济参考价格 | 有本地录制时导入 |
| `external_daily` | Yahoo Chart CL=F/BZ=F | 日线 | 长期外部期货背景 | 研究参考，不用于执行 |

Variational 匿名 API 请求会被 Cloudflare/认证拒绝，因此 v1 不绕过登录，也不复制 `monte-fox` 的钱包或订单能力。

## 3. 同步规则

- 每个价格源内部按时间戳精确配对；
- K 线按同一 interval 的开始时间配对；
- Variational 只使用同一 `market_observation` 中的两腿；
- 缺失一腿时删除该联合记录并计入数据健康；
- 不前向填充，不将日线与小时线拼成一条序列。

## 4. 指标

对每条同步观察：

```text
美元价差 = Brent - WTI
价格比值 = Brent / WTI
对数比值 = ln(Brent) - ln(WTI)
```

冻结模型在明确形成窗口拟合：

```text
ln(Brent) = alpha + beta × ln(WTI) + residual
```

页面展示 `alpha`、`beta`、形成窗口、形成数据 SHA-256、样本数、残差中心和稳健尺度。CLI 默认从已有投影复用冻结参数；只有显式传入 `--refit-models` 才重新形成模型。参考残差只描述该价格源中的相对偏离，不是指定数量可执行收益。

## 5. 机制诊断

v1 使用确定性规则输出：

- 当前残差相对形成样本的位置；
- 按时间戳回溯最近 24 小时的 Brent 与 WTI 对数变化贡献；日线长期参考不冒充“24 个交易日”；
- Lighter 与 Hyperliquid 最新对数比值差；
- underlying close 时段与正常时段的样本差；
- 已知展期窗口重叠；
- 指定规模冻结盘口进入和往返摩擦；
- 数据缺口、来源时间差和未知费用。

诊断必须附输入值和限制。它不替代因果研究，也不要求用户提交固定假设。

## 6. 执行比较

### v1 现状

Lighter 与 Hyperliquid 暂按两腿 `1:1` 场所数量和各自合法数量网格，分别计算：

- long Brent / short WTI；
- long WTI / short Brent；
- `$100`、`$500`、`$1,000` 与后续自定义规模；
- 进入对数比值相对中间价的 crossing；
- 同一冻结盘口反向关闭的往返摩擦；
- 进场/退出成交率、进场残余、未关闭数量、已知费用与未知项。

这只是 L2 摩擦基线，不是冻结模型 beta 对冲，也不证明经济中性。合约月份、乘数/权重和可执行对冲比率未经核验，因此 v1 不发布策略 PnL。

Variational 是指定数量 RFQ，不使用 L2 逐档模型；v1 从录制中展示已有 RFQ，不主动创建新的浏览器认证会话。

## 7. 数据产物

```text
research/raw/oil/<capture-id>/        # 原始响应和 manifest，Git 外
research/runs/oil-relative-value.json # 当前派生研究投影
```

CLI 必须能从原始来源重新生成派生投影。HTTP 提供完整 JSON 和按价格源导出的 CSV。

## 8. v1 限制

- 外部日线是背景，不证明 Lighter/Hyperliquid 合约与连续期货完全一致；
- 当前公开数据不能确认实时合约月份和实际展期权重；
- Lighter/Hyperliquid 费用仍可能缺少账户层级证据；
- 冻结盘口往返是交易摩擦基线，不是未来退出预测；
- Variational 没有本地录制时不可用；
- 冻结模型是描述工具，必须经过后续回放才能讨论均值回归质量。
