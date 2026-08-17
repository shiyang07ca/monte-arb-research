# Day12：当前市场扫描与失效候选

> 状态：可开始
>
> 时间：60–90 分钟
>
> 当日成果：一个从官方市场清单开始、先淘汰无效候选的命令行扫描器。

## 真实事故

近期群友笔记曾报告 `CRWD` 跨场所价差可能为正，但当前 Hyperliquid 官方响应已经显示
`xyz:CRWD` 下架、零持仓量、零成交量且无盘口。继续计算手续费和价差只会浪费时间。

## 必须理解

- 候选首先是“此刻可交易的两个市场”，不是两个相似名称。
- 完整交易标识（`symbol`）、场所、产品命名空间和市场编号共同确定市场身份。
- 下架、停牌、没有双边盘口或未知交易标识必须在成本计算前停止。
- 旧截图、旧清单和群友结论只能生成线索。

## 助手实现

- 查询 Lighter `orderBooks` 与 Hyperliquid `perpDexs/metaAndAssetCtxs`。
- 保存带获取时间和内容哈希的原始响应。
- 生成统一市场状态，不把未知交易标识映射为默认市场。
- 实现 `scan` 命令，列出通过、拒绝和资料未知的市场。
- 为下架、缺少盘口、重复身份和未知交易标识写测试。

## 用户任务

1. 运行前写下 `xyz:CRWD` 的预期决定及最便宜的决定性证据。
2. 审查交易标识查找与拒绝原因两个关键函数。
3. 亲自修改一条规则：例如把“只有单边盘口”从继续采集改为拒绝，并预测候选数量怎样变化。
4. 诊断一个注入故障：返回顺序变化后，程序把资产上下文配给了错误交易标识。

## 通过条件

- `xyz:CRWD` 在任何价差计算前被拒绝。
- 可交易状态（`active`）只表示允许进入下一项检查，不会自动成为机会。
- 未知交易标识显式失败。
- 相同冻结输入两次产生相同决定和原因。
- 用户能说明这个检查没有证明流动性、成本或盈利。

## 保存证据

```text
research/manifests/day12-universe.json
research/runs/day12-scan.json
research/decisions/day12-crwd.md
```

## 一手资料

- [Lighter Order Books](https://apidocs.lighter.xyz/reference/orderbooks)
- [Hyperliquid 永续市场接口](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals)
- [Hyperliquid 资产编号](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids)
