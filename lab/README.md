# 历史研究代码与公开数据

`lab/` 保存 Day2–9 中仍可复现的市场规则、数据质量和字段语义实验。它不是 Day12 起的新系统实现目录；新的正式代码进入 `src/monte_arb/`。

## 保留的代码

- `capture_lighter_rwa.py`：公开 Lighter 历史数据采集。
- `day4_price_semantics.py`：成交价、指数价和标记价的用途差异。
- `day5_roll_session.py`：原油展期与交易时段规则。
- `day7_data_cleaning.py`：保留异常、按时间切分和可复现清洗。
- `venue_schema.py`：不同场所公开盘口字段的语义差异。
- `day9_parameter_recheck.py`：当前参数与历史快照比较。

相应测试只读取仓库固定测试数据，并将临时输出写入系统临时目录，不再修改已跟踪研究产物。

## 已删除

- 会把未知交易标识静默映射到 BRENTOIL 的旧审计程序。
- 使用错误 funding 结算价格的 Day6 程序、测试与输出。
- 打卡 API 请求和响应。

这些文件可从 Git 历史恢复，但不得用于当前研究。

## 数据规则

- `lab/data/lighter_rwa_raw/`、`lab/data/day8_raw/` 和 `lab/data/day9_raw/` 是带来源的历史公开响应。
- 所有历史快照只描述取得时刻，不代表当前市场状态。
- 原始响应不可覆盖；派生结果必须能从指定输入重新生成。
- 任何程序都不得包含账户密钥、Authorization header 或下单调用。
