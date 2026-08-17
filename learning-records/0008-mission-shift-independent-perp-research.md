# 使命转向独立永续套利研究与真实系统能力

> Status: superseded by the 2026-08-17 `MISSION.md`

用户确认不再以 Lighter WTI–BRENTOIL 单一相对价值案例作为最终目标，而以独立发现、审查和否定 perp 套利候选，并使用 NautilusTrader 完成确定性历史重放和实时模拟为当前使命。BTC/ETH 用于验证工程实现，XAU/GOLD 是首个 RWA 主研究，XAG/SILVER 用于迁移验证，原油候选在能证明当前合约月份和展期权重后再研究。

## Evidence

用户确认每天投入 30–90 分钟，21 天只做到历史重放和实时模拟，后续真实运行采用人工值守；用户能独立使用 Python 和 SQL、会使用 Linux/Docker，能看懂 WebSocket 与测试代码。后续实验资金上限可提高到 `$150`，但真实下单仍需单独授权。

## Implications

后续不再重复通用 Python 或 SQL 教学；重点补齐 WebSocket 独立实现、失败测试、双腿执行、NautilusTrader 和候选迁移。Day 1–9 仅作为先修材料和历史证据，课程从 Day 10 的正确性修复接续。
