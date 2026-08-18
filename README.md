# Monte Arb Research

这是一个持续迭代的市场机会研究工作台与训练仓库。Agent 负责实现和运行；用户使用真实候选训练发现现象、提出机制、选择实验和解释结果。当前系统不发送真实订单。

## 从这里开始

1. [`MISSION.md`](./MISSION.md)：系统目标、用户能力与边界。
2. [`resource/plan.md`](./resource/plan.md)：Day14–21 工作台里程碑。
3. [`research/design/workbench-design.md`](./research/design/workbench-design.md)：工作台详细设计。
4. [`curriculum/day14.md`](./curriculum/day14.md)：当前里程碑。

## 核心循环

```text
自动扫描
→ 交易吸引力榜 + 研究价值榜
→ 优先展示最多 3 个真实候选
→ 用户先解释现象
→ Agent 提供竞争假设
→ 运行区分性实验
→ 用户解释结果
→ 系统获得新的可复用能力
```

## 目录

- `src/monte_arb/`：可复用研究系统代码；
- `research/design/`：一手资料、训练方法和工作台设计；
- `research/`：运行结果、实验和研究证据；
- `curriculum/`：Day14–21 系统里程碑，不是每日阅读模板；
- `learning-records/`：历史学习记录，不等于掌握证明；
- `resource/`：总计划与外部参考资料；
- `lab/`：仍有复现价值的旧实验。

## 当前边界

- 主扫描：Lighter–Hyperliquid 全部可映射永续；
- WTI/Brent：RWA 基准案例，而非唯一范围；
- 机会雷达：其他 perp venue、RWA/TradeFi、funding 和链上方向；
- 浏览器为主界面，Telegram 为研究对话层；
- Python、CLI、脚本和 Jupyter 均可复用；
- 不注册执行客户端，不真实下单。
