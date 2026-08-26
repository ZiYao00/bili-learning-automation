# B站视频转笔记

本项目服务 Codex、Hermes 与 WorkBuddy。三者共用同一套采集、taxonomy、确定性笔记骨架、校验、发布和清理逻辑。

## 安装验收、首次使用与环境门禁

下面两类任务都要运行统一 `bili-learning onboarding`（或等价入口）：

1. “生成 B站学习笔记”：正式采集前先检查；
2. “安装 / 检查 / 验证 / 初始化 / 确认 bili-learning-automation 是否可用”：先确认当前入口或安装链接有效，再运行 onboarding。不能只验证文件存在、链接目标或 Skill 内容一致就结束。

如果用户只是分析、解释或编辑仓库源码，并没有要求检查当前本机是否可用，不强制运行 onboarding。不要根据仓库示例、本机历史或模型记忆猜测用户路径。

安装验收的反馈要明确区分“Skill 已安装”和“运行环境已就绪”。只有安装有效且 onboarding `ready`，才能告诉用户当前可以直接使用。

- `status = ready`：简要报告 Python、yt-dlp、Bilibili Cookie、Obsidian Vault 与 CSS 的就绪状态；不要展示 Cookie 内容。安装 / 验证任务到这里结束，生成笔记任务才继续采集。
- `status = action_required`：可以说明 Skill 安装成功，但必须明确运行环境尚未就绪；停止采集，只处理返回的 `actions`。Vault 要求用户提供直接包含 `.obsidian` 的根目录；Cookie 只接收 Netscape 文件路径，不读取或复述内容，不知道如何获取时指向 `docs/BILIBILI-COOKIE.md`；yt-dlp 默认自动检测，缺失时说明项目不会自动安装，Windows 推荐 `winget install yt-dlp`，只有自定义安装才询问可执行文件路径。
- `warnings` 中的 CSS 缺失不阻塞笔记生成，但首次出现时应告知：共享真源是 `obsidian-learning-snippets`，需要 `learning-lab.css + video-note.css`，程序不会静默复制或覆盖；安装后还要在 Obsidian“设置 → 外观 → CSS 代码片段”中启用。
- 配置后重新运行 onboarding；只有 `ready` 才进入采集或把环境描述为“可直接使用”。`prepare` 自身也有同一门禁，若返回 `onboarding_required`，按其 `actions / warnings` 处理后重试原链接。

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
- finalizer 返回 `note_ready` 即表示业务完成；临时数据采用 retire/维护语义，`temporary_data_retired` 或 `cleanup_warning` 不得覆盖已成功的发布结果。

## 共享 Obsidian 样式依赖

共享 CSS 的唯一真源是：<https://github.com/ZiYao00/obsidian-learning-snippets>。

修改笔记版式或 Frontmatter 前，先读取 `config\obsidian-style.json`。本项目只使用 `learning-lab.css` Core 与 `video-note.css` Extension；不得在此仓库复制、重建、fork 或独立修改共享 CSS，也不得把受 Git 跟踪的项目目录 junction 到共享仓库。需要改共享视觉系统时，修改共享仓库，再同步到 Obsidian Vault。

Hermes 与 WorkBuddy 的 `SKILL.md` 只是入口适配层，不应复制或改写核心规则。

准备 v1.0 提交、推送或 Release 时，先阅读 `docs/RELEASE-CHECKLIST.md`。不要把 `ComfyUI-Learning-Lab` 的独立工作区混入本仓库提交。
