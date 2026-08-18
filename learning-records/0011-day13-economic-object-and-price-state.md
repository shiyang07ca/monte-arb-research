# Day13 学习记录：经济对象与价格状态

- 日期：2026-08-18
- 状态：学习完成
- 课程：`curriculum/day13.md`
- 互动页面：`lessons/0009-day13-economic-object.html`
- 打印参考卡：`reference/day13-economic-object.html`
- 研究状态：`unknown / exclude`，不是可交易结论

## 今日目标

判断 Lighter 与 Hyperliquid `xyz` 的四个原油永续市场是否代表可跨场比较的同一经济对象，并把静态经济对象与报价时刻的动态价格状态分开。

```text
Lighter WTI              local_id=145
Lighter BRENTOIL         local_id=159
Hyperliquid xyz:CL       asset_id=110029
Hyperliquid xyz:BRENTOIL asset_id=110049
```

## 已完成动作与证据

1. 从官方规则核对 WTI/Brent 基准、每桶单位、当前规格页、期货展期规则、外部交易时段，以及 external/internal oracle 转换机制。
2. 修正了最初错误的阻断原因：`Q6/U6/V6/X6` 已包含 2026 年和月份代码；真正缺少的是观察时刻实际生效的合约月份与权重，而不是合约年份。
3. 实现失败关闭的经济对象映射器：`src/monte_arb/economic.py`。
4. 保存当前映射输出：`research/runs/day13-economic-map.json`。
5. 创建互动课程和参考卡，并在浏览器中实际打开、测试映射按钮、价格状态分类和综合反馈。
6. 核对结算与异常状态：四个研究对象是永续合约；底层月度期货到期通过参考价格展期处理。oracle stale、内部定价、展期、停市、空/单边盘口、清算与 mark/oracle/可成交价混用都会阻断报价样本，但不会自动改变经济对象定义。
7. 运行验证：Day12–13 测试 20/20，通过；历史课程回归 27/27，通过；Ruff、JavaScript 语法、HTML 解析和引用检查通过。

## 理解证据

用户先正确判断：

```text
oraclePx 字段相同，但价格来源不同
→ 不能直接比较
```

用户在页面冲突且缺少观察时刻实际权重时选择：

```text
unknown
```

在最终综合场景中，两边的基准、单位、报价/结算币和合约权重相同，但 oracle 状态不同。用户回答：

```text
economic_object = same
quote_sample = 不可用，因为oracle_state 不同
```

该回答证明用户已经掌握 Day13 最关键的两层判断：

```text
经济对象相同
≠
当前报价样本可用
```

一次需要修正的理由是：两份规则在观察时点分别为 `100% V6` 与 `100% U6` 时，结论为 `different` 的原因是有效规则内容不同，不是两条规则的开始生效时间不同。修正后，用户通过最终综合迁移证明已理解该区别。

## 当前研究决定

```text
Lighter WTI ↔ xyz:CL
status = unknown
reason = CONTRACT_REFERENCE_STATUS_UNKNOWN

Lighter BRENTOIL ↔ xyz:BRENTOIL
status = unknown
reason = CONTRACT_REFERENCE_STATUS_UNKNOWN

Lighter WTI ↔ xyz:BRENTOIL
status = not_comparable
reason = BENCHMARK_MISMATCH + CONTRACT_MONTH_MISMATCH

current_quote_sample
status = exclude
reason = actual contract weights and oracle states were not captured at the same observation time
```

Day13 学习完成不等于映射已证明，也不等于套利可交易。当前没有计算利润、费用、滑点或资金费，没有连接任何下单接口。

## 未完成或阻断项

- 尚未取得 Lighter 与 trade.xyz 在同一观察时刻实际使用的合约月份和权重。
- 尚未同步采集两边 external price 可用性、oracle freshness 与 external/internal 状态。
- 静态规格页和带日期的展期页仍存在当前参考合约文字冲突；不能自行选边。
- 未证明两边异常市场与清算状态可在同一时间轴上可靠分类。

## 下一步

Day14 只读同步采集：为每条报价保存完整市场身份、来源时间、接收时间、bid/ask、oracle/mark/external 价格（可用时）、展期权重证据和市场状态。先证明哪些时间窗口可以比较，再研究价差；仍不下单。
