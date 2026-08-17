# Day13：经济对象与 RWA 价格状态

> 状态：待学习
>
> 时间：60–90 分钟
>
> 当日成果：跨场所经济对象映射和 RWA 价格状态分类器。

## 真实问题

两个市场都叫黄金、价格也接近，仍可能处于不同价格状态。外部黄金市场关闭后，一边可能冻结外部价格并使用内部规则，另一边可能继续使用不同价格源。此时持续 70 个基点的差异不自动构成套利。

## 必须理解

- 比较对象包括单位、乘数、报价币、结算币、外部基准和结算方式。
- 指数价、标记价和可成交价用途不同。
- RWA 必须区分外部价格有效、转入内部定价、内部定价、恢复外部价格和未知状态。
- 不能证明处于相同状态的两条记录不得进入价差样本。

## 助手实现

- 从 Day12 的全部市场中生成可映射候选，不只处理固定列表。
- 为每个映射保存证据来源、规则版本和未知项。
- 实现价格状态分类器；未知输入保持未知，不使用默认时段。
- 用 XAU/`xyz:GOLD` 构造休市反例，用 BTC/ETH 构造全天候控制样本。

## 用户任务

1. 在看分类结果前判断一段黄金休市价差是否可比较。
2. 审查市场映射和价格状态两个函数。
3. 修改一个市场的交易时段或状态规则，预测哪些样本会被排除。
4. 诊断一个注入故障：程序使用接收时间代替外部市场时区，错误地把休市样本标为开放。

## 通过条件

- 名称相同但单位或结算不同的市场不会自动配对。
- XAU/GOLD 的休市状态差异明确阻止比较。
- 夏令时、节假日和状态未知不会静默按正常开市处理。
- 用户能解释需要哪些重新开市数据才能研究收敛。

## 保存证据

```text
research/manifests/day13-market-map.json
research/runs/day13-price-states.jsonl
research/decisions/day13-rwa-comparability.md
```

## 一手资料

- [Lighter RWA 市场规格](https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications)
- [Lighter RWA 定价机制](https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism)
- [Hyperliquid HIP-3](https://hyperliquid.gitbook.io/hyperliquid-docs/hyperliquid-improvement-proposals-hips/hip-3-builder-deployed-perpetuals)
- [trade.xyz 规格索引](https://docs.trade.xyz/consolidated-resources/specification-index)
