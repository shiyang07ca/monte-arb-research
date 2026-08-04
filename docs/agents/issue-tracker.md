# Issue tracker：Local Markdown

本仓库的 issue 和规格文档均以 Markdown 文件保存在 `.scratch/` 下。

## 文件约定

- 每个 feature 使用一个目录：`.scratch/<feature-slug>/`
- 规格文档路径为：`.scratch/<feature-slug>/spec.md`
- 实现票据每张使用一个文件，路径为 `.scratch/<feature-slug>/issues/<NN>-<slug>.md`；编号从 `01` 开始，不使用合并后的单一票据文件
- 每张 issue 文件顶部附近使用 `Status:` 行记录 triage 状态；对应的标签字符串见 `docs/agents/triage-labels.md`
- 评论和对话记录追加到文件末尾的 `## Comments` 标题下

## 技能要求“发布到 issue tracker”时

创建 `.scratch/<feature-slug>/` 目录（如果目录不存在），并在其中创建相应的 Markdown 文件。

## 技能要求“获取相关票据”时

读取用户提供的文件路径或 issue 编号对应的文件。用户通常会直接提供路径或编号。

## Wayfinding operations

Wayfinder 在本地 Markdown tracker 中使用以下规则：

- 本地 Markdown 没有独立的远程标签字段：`.scratch/<effort>/map.md` 的文件身份对应 `wayfinder:map`；子票据的 `Type:` 值对应 `wayfinder:research`、`wayfinder:prototype`、`wayfinder:grilling` 或 `wayfinder:task`。
- **Map**：`.scratch/<effort>/map.md`。每个 effort 只有一张地图；地图是索引，不重复保存子票据中的完整决定。
- **Map 正文**：使用固定标题 `## Destination`、`## Notes`、`## Decisions so far`、`## Not yet specified` 和 `## Out of scope`。`Destination` 说明最终要得到的规格、决定或变更；`Notes` 记录领域、每次会话应查阅的技能和持续适用的偏好；`Decisions so far` 每行链接一个已解决的子票据并概述其结论；`Not yet specified` 记录当前仍在范围内但尚不能准确表述的问题；`Out of scope` 记录明确排除在本 effort 外的工作。
- **Child ticket**：`.scratch/<effort>/issues/NN-<slug>.md`，编号从 `01` 开始。正文使用固定标题 `## Question`，提出这张票据要解决的一个决定或调查问题。`Type:` 记录 `research`、`prototype`、`grilling` 或 `task`；`Status:` 记录 `claimed` 或 `resolved`。未解决且未认领的票据视为开放票据。
- **Blocking**：票据顶部可使用 `Blocked by: NN, NN` 列出阻塞它的同一地图中的票据编号。所有列出的票据都为 `resolved` 后，该票据才算未阻塞。没有 `Blocked by:` 行的开放票据不受阻塞。
- **Frontier**：扫描 `.scratch/<effort>/issues/`，找到开放、未阻塞且未认领的子票据；按编号从小到大选择第一张。
- **Claim**：开始处理前先写入 `Status: claimed` 并保存；这表示当前会话已认领该票据，其他会话应跳过它。
- **Resolve**：在票据中追加固定标题 `## Answer` 及结论，写入 `Status: resolved`，然后在地图的 `Decisions so far` 中追加该票据的名称、链接和一句话摘要。
- 地图和票据在面向人的叙述中使用标题名称引用；编号、路径和链接作为名称的一部分保留，不单独用裸编号代替名称。
