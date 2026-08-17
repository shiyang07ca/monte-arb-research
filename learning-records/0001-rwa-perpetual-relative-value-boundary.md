# 研究记录：RWA 永续与统计套利边界

## Status

superseded by LR-0009

## Lesson

同一场所中的 WTI 与 BRENTOIL 是不同商品 RWA 永续，不是同一标的的跨场所价差；即使两者价格都以每桶美元表示，也不能默认两腿 1:1 对冲或价差必然均值回归。Lighter 官方规则还要求分别处理外部 oracle、内部 EMA、index/mark price、不同的期货展期时间和不同的市场关闭窗口，因此第一步应是合约模型和数据审计，而不是直接选择价差公式或拟合协整。[43][44][45]

## Evidence

用户明确选择研究 Lighter 内部 WTI–BRENTOIL，并明确暂不选择固定美元价差、价格比率或动态 beta；随后完成了两市场官方只读 API 采集与审计。当前共同小时样本为 500 行，描述性收益相关性约 `0.971`，但历史深度、funding 账本和目标数量退出尚未通过验证，因此暂时不能判断策略是否成立。

## Implications

后续课程先教 RWA 永续的经济对象、价格和时间机制，再教数据清洗与样本外检验。任何只展示相关性、价差图或一次正收益的内容，都不能被当作策略已成立。

## Sources

[43] https://docs.lighter.xyz/trading/real-world-assets-rwas/rwa-pricing-mechanism — Lighter Docs: RWA Pricing Mechanism
[44] https://docs.lighter.xyz/trading/real-world-assets-rwas/futures-contract-price-rolling-mechanism — Lighter Docs: Futures Contract Price Rolling Mechanism
[45] https://docs.lighter.xyz/trading/real-world-assets-rwas/market-specifications — Lighter Docs: RWA Market Specifications
