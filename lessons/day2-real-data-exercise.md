# Day 2 真实数据练习：Lighter WTI/BRENTOIL 原始数据审计

## 练习目标

用真实仓库快照，而不是模拟数据，完成一次可复查的只读审计：

- 识别 raw、manifest、audit、aligned 四种证据的关系；
- 按 timestamp 而不是数组下标匹配两腿；
- 区分行数、唯一 timestamp、共同观察数和收益变化数；
- 发现“没有重复”不等于“数据完整”；
- 把未知字段映射为研究 `Blocked`，而不是填成零成本。

## 输入文件

```text
lab/data/lighter_rwa_raw/WTI_candles_1h.json
lab/data/lighter_rwa_raw/BRENTOIL_candles_1h.json
lab/data/lighter_rwa_raw/WTI_fundings_1h.json
lab/data/lighter_rwa_raw/BRENTOIL_fundings_1h.json
lab/data/lighter_rwa_raw/145_orderBookDetails.json
lab/data/lighter_rwa_raw/159_orderBookDetails.json
lab/data/lighter_rwa_capture_manifest.json
lab/data/lighter_rwa_data_audit.json
lab/data/lighter_rwa_aligned_1h.jsonl
```

## A. 先闭卷写下预测

在运行命令前，写下你的预测：

1. 两腿各有多少根共同 1h candle？
2. 为什么收益变化数会比 candle 数少 1？
3. 哪个字段用于时间匹配？它的单位是什么？
4. 你预计 daily duplicate 是多少？这个结果不能证明什么？
5. 你预计研究状态是 `Go`、`No-Go` 还是 `Blocked`？

## B. 运行审计

```bash
python3 lab/audit_lighter_rwa.py
```

记录输出中的：

```text
common_rows
log_return_correlation
daily_duplicate_rows
decision
```

## C. 独立复现共同序列

```bash
python3 - <<'PY'
import json
from pathlib import Path

for name in ("WTI", "BRENTOIL"):
    rows = json.loads(
        (Path("lab/data/lighter_rwa_raw") / f"{name}_candles_1h.json").read_text()
    )["c"]
    timestamps = [int(row["t"]) for row in rows]
    print(name)
    print("rows=", len(rows))
    print("unique_timestamps=", len(set(timestamps)))
    print("first_timestamp_ms=", timestamps[0])
    print("last_timestamp_ms=", timestamps[-1])

aligned = [
    json.loads(line)
    for line in Path("lab/data/lighter_rwa_aligned_1h.jsonl").read_text().splitlines()
    if line.strip()
]
print("common_rows=", len(aligned))
print("first_utc=", aligned[0]["timestamp_utc"])
print("last_utc=", aligned[-1]["timestamp_utc"])
PY
```

## D. 字段语义检查

打开两个 `orderBookDetails` 文件，回答：

- WTI 与 BRENTOIL 的 `market_id` 是否正确？
- `market_type` 是否为 `perp`？
- 两腿的 `min_base_amount` 是否相同？
- `size_decimals` 是否相同？
- 为什么这些差异会阻止默认“等基础数量 + 1:1 对冲”的说法？

当前快照中可核对的事实：

```text
WTI:      market_id=145, min_base_amount=0.100,  size_decimals=3
BRENTOIL: market_id=159, min_base_amount=0.0800, size_decimals=4
```

## E. Funding 反例

两个 funding 文件都有 `timestamp`、`value`、`rate`、`direction`。请解释：

> 为什么“WTI value - BRENTOIL value 的均值为负”仍然不能直接等于某个交易者的 funding 净收益？

至少指出：

- 持仓方向；
- 实际基础数量；
- 结算价格或名义计算方式；
- funding 结算时间和账户账本；
- 两腿开仓/平仓时间是否覆盖相同 funding 事件。

## F. 交付格式

把以下内容发给老师（可以直接发在聊天里，也可以保存成自己的 Markdown）：

```markdown
# 我的 Day 2 审计

## 1. 文件关系

## 2. 实际数字

## 3. 字段语义

## 4. Funding 反例

## 5. 仍然阻断研究的未知项

## 6. 当前三层状态
- 学习：
- 研究：
- 真实执行：
```

## 通过标准

- 能运行审计脚本并复述真实输出；
- 能说明为什么按 timestamp 匹配；
- 能区分 `500` 根 candle 与 `499` 个收益变化；
- 能解释至少 3 个相关性无法回答的问题；
- 能解释 funding API 字段不等于个人现金账本；
- 能把历史、展期、funding、盘口退出和权限未知写成研究影响；
- 不把练习通过写成策略 `Go`，不执行任何交易操作。

## 提示

如果卡住，先只回答一个具体问题：

> 如果 WTI 在 10:00、11:00、12:00 有数据，而 BRENTOIL 在 10:00、12:00 有数据，11:00 的两腿价格应该如何处理？

不要先猜价格；先说你会保留、删除还是标记这个时间桶，以及为什么。
