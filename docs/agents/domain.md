# 领域文档

engineering skill 探索代码库时，按以下规则读取本仓库的领域文档。

## 开始探索前读取

- 根目录的 `CONTEXT.md`；或
- 如果根目录存在 `CONTEXT-MAP.md`，读取它指向的、与当前主题相关的各个 `CONTEXT.md`；
- 读取涉及当前工作区域的 `docs/adr/` 中的架构决策记录。多上下文仓库还要检查 `src/<context>/docs/adr/` 中与当前上下文相关的决策。

如果这些文件或目录不存在，静默继续，不要专门提示缺失，也不要预先建议创建。`/domain-modeling` skill（通过 `/grill-with-docs` 和 `/improve-codebase-architecture` 使用）会在术语或决定真正确定后按需创建它们。

## 文件布局

本仓库使用 single-context 布局：

```text
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

如果以后改为 multi-context，则根目录使用 `CONTEXT-MAP.md`，并由它指向各个上下文的 `CONTEXT.md`；系统级决定仍放在 `docs/adr/`，上下文级决定放在 `src/<context>/docs/adr/`。

## 使用术语表中的词汇

在 issue 标题、重构建议、假设或测试名称中描述领域概念时，使用 `CONTEXT.md` 定义的术语，不要自行改用同义词。如果需要的概念尚未出现在术语表中，先判断这是误造的项目语言，还是应由 `/domain-modeling` 补充的真实缺口。

## 发现 ADR 冲突时

如果输出与已有 ADR 相矛盾，必须明确指出，不要静默覆盖。例如：

> _与 ADR-0007（事件溯源订单）矛盾，但由于……值得重新讨论。_
