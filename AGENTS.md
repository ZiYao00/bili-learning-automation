# B站视频转笔记

本项目服务 Codex、Hermes 与 WorkBuddy。三者共用同一套采集、taxonomy、确定性笔记骨架、校验、发布和清理逻辑。

## 先读取任务模式

生成或修改 `notes\bilibili` 中的笔记前，先读取 collector 返回的 `handoff_path` 与 `job.json`，再根据 `workflow_mode` 选择说明：

### `light`（当前默认实验模式）

只需读取：

- `docs\standards\LIGHT-WORKFLOW.md`
- 当前 `transcript_manifest_path` 及全部 transcript chunk

不要主动加载或执行 `KNOWLEDGE-DENSE-WORKFLOW.md`，也不要创建 Fact Ledger、Semantic Draft 或 Layout Plan。先完整写内容，再在同一笔记上独立做一次排版优化；只有进入排版阶段后，才可按需读取 `docs\OBSIDIAN-STYLING.md` 和示例文档中的相关局部片段。

### `strict`（保留的严格模式）

读取：

- `docs\AGENT-INTEGRATION.md`
- `docs\standards\CODEX-VIDEO-NOTE-GUIDE.md`
- `docs\standards\KNOWLEDGE-DENSE-WORKFLOW.md`
- `docs\OBSIDIAN-STYLING.md`

`STANDARD-VIDEO-NOTE-EXAMPLE.md` 只在需要确认 Table / Grid / Card / Callout 语法时参考，不得复制章节集合、顺序、数量或组件组合。

## 所有模式共同遵守

- Python 负责 Frontmatter、H1、标题元信息、播放器与来源区、UP 主资源、原始简介、iframe、tags、`learning-page + video-note`、文件名、路径和 marker；Agent 只填写两个 AI 区域与 runtime `analysis.json`。
- 正文事实只来自当前字幕和 UP 主简介。来源不足时停止，不用模型常识补具体参数、资源或结论。
- 不覆盖已有笔记，不把 Cookie、runtime 路径、日志或内部状态写进正式笔记。
- 视频简介抓取失败不能当作视频没有简介。
- 只有 finalizer 返回 `note_ready` 且临时数据清理成功，才能声称完成。

Hermes 与 WorkBuddy 的 `SKILL.md` 只是入口适配层，不应复制或改写核心规则。

准备 v1.0 提交、推送或 Release 时，先阅读 `docs/RELEASE-CHECKLIST.md`。不要把 `ComfyUI-Learning-Lab` 的独立工作区混入本仓库提交。
