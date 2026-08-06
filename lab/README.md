# Lighter WTI–BRENTOIL 研究代码

当前目录的研究代码分为两类：

- `lab/capture_lighter_rwa.py`：只读采集官方 candles、fundings 和 `orderBookDetails`，保存原始响应、请求元数据和 SHA-256；
- `lab/audit_lighter_rwa.py`：读取原始响应，输出覆盖、重复时间戳、描述性统计和共同小时 JSONL；

现有代码明确不认证、不发单、不提交交易。统计审计输出的 `decision` 为 `BLOCKED_FOR_STRATEGY_CONCLUSION`。

后续实现统计或执行回放时必须先补测试，并遵循：

1. 原始响应不可覆盖；
2. 时间统一为 UTC；
3. 训练集才能确定参数；
4. funding、费用、退出未知时不填零；
5. 结果必须带 reason code；
6. 研究代码不包含私钥、API secret、Authorization header 或无人值守下单。
