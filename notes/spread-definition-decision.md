# 样本外价差定义决策模板

> Day 8 使用。当前只记录检验设计，不把短样本描述性结果写成策略结论。

## 候选定义

1. 固定美元差：`WTI - BRENTOIL`；
2. 对数差：`log(WTI) - log(BRENTOIL)`；
3. 训练集估计 beta：`log(WTI) - alpha - beta * log(BRENTOIL)`；
4. 加入展期和市场状态的分层模型。

不先看哪个结果赚钱再决定定义。

## 时间切分

- 训练集：只用于估计 beta、窗口、阈值和退出规则；
- 验证集：用于选择候选定义和压力参数；
- 测试集：完全冻结参数后只运行一次纸上回放；
- 若当前约 21 天样本不足以形成有意义的切分，状态为 `HISTORY_DEPTH_INSUFFICIENT`。

## 最低报告项

- 收益相关性（描述性）；
- 单位根/协整检验（仅在样本条件满足时）；
- beta 和截距的滚动稳定性；
- 残差波动和半衰期/回归时间；
- 阈值触发次数；
- 最大偏离；
- 展期前后和市场状态分层；
- 样本外触发和净现金结果；
- funding、开平仓冲击、费用和失败恢复后的结果。

## 拒绝规则

- 相关性高但没有足够历史：`Blocked`；
- 只在全样本拟合后盈利：拒绝；
- 依赖未知 funding 或退出成本：`Blocked`；
- 关系在测试集不稳定：`No-Go`；
- 通过更换公式、阈值或窗口反复寻找正结果：研究无效。

## 结论模板

```text
candidate_definition:
training_period:
validation_period:
test_period:
parameters_frozen_at:
out_of_sample_result:
net_cash_costs_included:
unknowns:
decision: Go / No-Go / Blocked
reason_codes:
```
