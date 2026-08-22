# 0014 · Day17 Brent–WTI 机制诊断能力

> 日期：2026-08-22
> 状态：工作台能力 v1 已实现、测试并运行；用户概念迁移待后续真实研究检验
> 里程碑：Day17

## 背景

旧工作台把候选和执行对象的大段 JSON 直接展示在页面上，不能回答日常研究最关键的问题：当前 Brent–WTI 关系相对自身历史是否异常、变化由哪条腿或哪种市场机制推动、不同价格源是否一致，以及真实盘口摩擦会吞掉多少观察到的偏离。

本轮重新确认产品目标：建设长期可运行、可扩展、可二次开发的只读套利研究操作台。每日共学用于增加真实数据、工具、分析能力和心智模型，不把产品做成强制解释或假设表单。

## 新增可复用能力

1. **多价格源数据集与 CLI**
   - Lighter WTI/BRENTOIL 1h K 线和当前 L2；
   - Hyperliquid `xyz:CL`/`xyz:BRENTOIL` 1h K 线和当前 L2；
   - 外部 CL/BZ 连续期货长期日线；
   - Variational `monte-fox` 市场观察的 index/RFQ 只读导入；未配置时明确不可用。
2. **指标分层**
   - 美元价差、价格比值、对数比值；
   - 按时间形成窗口估计并冻结的 log-linear 参考残差；
   - 验证窗口不参与重新拟合。
3. **机制诊断**
   - 当前参考残差与验证窗口分布迁移；
   - 按时间戳回溯最近 24 小时的 Brent/WTI 变化贡献；
   - UTC 小时时段代理；
   - Lighter–Hyperliquid 最新对数比值分歧；
   - roll、funding 和数据健康的已知结果或证据缺口；
   - 每项均包含证据、相反/无关证据、限制和下一项验证。
4. **执行摩擦**
   - 两个方向、`$100/$500/$1,000`、L2 走档、进场 crossing、进场/退出成交率、未关闭数量和冻结盘口往返摩擦；
   - 明确当前是 1:1 场所数量基线，不是 beta 对冲或经济中性策略 PnL；
   - 账户费率、持有期 funding、未来退出、合约权重和执行对冲比率未知时保持未知。
5. **产品页面与二次开发接口**
   - Dashboard、Brent–WTI 专题和数据目录；
   - 浅色、图表/筛选/诊断/执行表为主，不在主页面展示大 JSON；
   - 稳定 JSON、单价格源 CSV、来源 manifest、原始响应 SHA-256 和冻结形成数据 SHA-256；
   - 旧候选和执行路由保持兼容。

## 真实运行证据

最近一次实时采集：

- Lighter：500 个同步 1h 点；
- Hyperliquid：721 个同步 1h 点；
- 外部连续期货：4,743 个同步日线点；
- Variational index/RFQ：本机没有 `monte-fox` 录制，明确 `unavailable`，没有生成示例值；
- 两个 venue 的当前 L2 均生成 6 行方向/规模组合；
- 真实投影包含 13 项机制与边界诊断。

最近一次真实值（`2026-08-22T05:30:04Z`）：

- Lighter：WTI `86.923`、Brent `92.440`、美元价差 `5.517`、价格比值 `1.06347`、冻结残差 z `+1.96`；
- Hyperliquid：WTI `86.941`、Brent `92.515`、美元价差 `5.574`、价格比值 `1.06411`、冻结残差 z `+2.91`；
- 外部连续期货日线：冻结残差 z `+0.30`，只用于长期背景；
- `$500` 冻结盘口往返摩擦：Lighter 约 `5.70 bps`，Hyperliquid 约 `1.75 bps`，但 Hyperliquid 账户费率未知；
- 两个 venue 在 `$100/$500/$1,000` 和两个方向下均显示进场/退出成交率 `100%`、未关闭数量 `0`；这只证明当前冻结盘口深度，不证明未来退出。

冻结模型生命周期也已真实验证：第一次用 `--refit-models` 形成模型，第二次普通采集复用 Lighter、Hyperliquid 和外部日线三个模型；每个模型保存形成期起止和形成数据 SHA-256。

运行时证据：

- `research/runs/oil-relative-value.json`（可重算，Git 忽略）
- `research/raw/oil/<capture-id>/`（原始响应，Git 忽略）
- 浏览器：`/workbench`、`/workbench/oil`、`/workbench/data`
- API：`/workbench/api/oil`、`/workbench/api/oil.csv?source=<key>`
- 全仓测试：`PYTHONPATH=src python3 -m unittest discover -s tests -v`，146 项通过；
- Chrome 集成测试：Dashboard → 油专题、价格源/范围/指标/方向/规模切换、桌面与 390px 窄屏、JavaScript 错误检查均通过；
- Ruff、Python 编译和 `git diff --check` 均通过。

## 已验证心智模型

### 1. 美元价差不是策略收益

`Brent − WTI` 只描述两个不同基准的美元距离。它没有包含对冲比率、执行方向、数量、费用、funding 或退出。

### 2. 比值、对数比值和残差回答不同问题

- 比值降低绝对油价水平影响；
- 对数比值近似两腿百分比关系；
- 冻结残差描述 Brent 相对形成期关系的条件偏离；
- 残差极端也可能意味着结构变化，而非未来回归。

### 3. 形成期和验证期必须分开

如果用全部历史反复重估 alpha/beta，再声称过去每次偏离都可回归，就引入未来信息。v1 按时间冻结形成窗口，并单独展示验证窗口分布。

### 4. 统计关系与可执行仓位不是同一层

模型 beta 是统计条件关系；真实执行还需要合约月份、乘数/权重、合法数量网格和盘口。v1 暂只给 1:1 数量下的 L2 摩擦，不冒充 beta-hedged 策略。

### 5. “未知”本身是研究结果

roll 权重、venue-native funding、账户费率和未来退出没有证据时，系统显示阻断项，不用零补齐。日线周末和节假日也不能在没有交易所日历时误报为 feed failure。

## 当前研究判断

本模块已经能够识别和分解“当前关系相对历史异常”的现象，但仍不能据此发布交易结论。主要阻断项：

- CL/BZ 实时合约月份与场所产品权重；
- 可执行 beta/经济对冲比率；
- 经核验的 roll/session 日历；
- venue-native funding 历史与账户实际费率；
- 未来退出盘口和样本外机会回放。

因此当前状态是：**机制研究能力可用；策略是否可交易尚未验证。**

## 共学打卡

- Intensive CoLearn：已通过官方 Agent API 创建 2026-08-22 的 Day17 打卡，HTTP `201`；
- 写入前课程状态为 `ongoing`，当前报名状态为 `approved`，当天没有既有记录；
- 随后查询个人打卡列表，HTTP `200`；服务端返回同一记录 ID，平台正文哈希与提交内容一致；
- 脱敏证据：`research/checkins/icl-day17-2026-08-22.json`；
- 凭据仅从本地环境读取，值、认证 header 和原始账户响应均未写入仓库；
- 平台打卡验证成功不改变研究结论：策略仍为 **Blocked / No-Go**。

## 证据路径

- `src/monte_arb/oil_relative_value.py`
- `src/monte_arb/research_console_views.py`
- `src/monte_arb/workbench_app.py`
- `tests/test_oil_relative_value.py`
- `tests/test_oil_browser.py`
- `docs/product/research-console.md`
- `docs/product/oil-relative-value-v1.md`
- `docs/adr/0001-read-only-modular-research-console.md`
- `.scratch/brent-wti-relative-value/spec.md`
- `curriculum/day17.md`

## 下一步

1. 加入经核验的 CL/BZ 合约月份、权重、roll 与 session 日历；
2. 持续采集并接入 venue-native funding；
3. Day18 对冻结模型做机会寿命、收敛和失败样本回放；
4. 从油专题抽出通用 `PairDefinition`、同步器、图表与执行比较，支持全市场 Screener 和 Spread Grapher；
5. 用户结合真实页面解释一个异常究竟属于价格关系、机制变化、数据质量还是执行层，作为后续概念迁移证据。
