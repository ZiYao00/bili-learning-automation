# B站视频转笔记

本项目服务 ChatGPT、Codex、Hermes 与 WorkBuddy。四个薄适配层共用同一套环境门禁、来源采集、Job lifecycle、taxonomy、确定性笔记骨架、校验、发布、导航和清理逻辑。

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

## 先选择来源，再读取任务模式

不得根据标题、历史 memory 或模型猜测自动跳过字幕。默认“转换链接”使用 `prepare / subtitle_srt`；当前消息明确要求“纯资源分享 / 只整理简介 / 不用字幕 / 跳过字幕”才使用 `prepare-description / description_only`；默认入口返回 `subtitle_unavailable` 后，只有用户明确要求 ASR 才使用独立 ASR 工具与 `prepare-transcript / asr_text`。

三个入口在采集前都会按 BVID 检查已发布笔记。默认发现重复时返回 `existing_note_found`，Agent 必须先让用户选择更新、重新执行或取消；重新执行用 `--on-existing rerun`，更新用 `--on-existing update --update-target <path>`，并始终复用触发提示时的原始完整消息。多篇重复笔记不得自动猜更新目标。更新 Job 会保存旧笔记快照并做 SHA-256 冲突检查，`update_conflict` 时不得强制覆盖。

三个入口共用同一个 Job lifecycle。生成笔记前读取 collector 返回的 `handoff_path`、`job.json`、`analysis_path` 与 `source_manifest_path`，再根据 `workflow_mode` 选择说明。旧 Job 的 `transcript_manifest_path` 仅作为 schema-v1 兼容别名。

### `light`（当前默认实验模式）

只需读取：

- `docs\standards\LIGHT-WORKFLOW.md`
- 当前 `source_manifest_path` 及 manifest 中实际存在的全部 source chunk

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
- 正文事实只来自当前 Job 允许的来源：SRT 字幕、明确授权后的 ASR 纯文本，或明确要求 `description_only` 时的标题 / metadata / UP 主简介 / 用户补充来源。`description_only` 不得推断视频口播、画面参数或未提供的资源本体。来源不足时停止，不用模型常识补具体参数、资源或结论。
- 不覆盖已有笔记，不把 Cookie、runtime 路径、日志或内部状态写进正式笔记。
- 视频简介抓取失败不能当作视频没有简介。
- finalizer 返回 `note_ready` 即表示业务完成；临时数据采用 retire/维护语义，`temporary_data_retired` 或 `cleanup_warning` 不得覆盖已成功的发布结果。
- 学习后整理默认关闭。只有用户明确要求并确认 `single / latest / all` 范围后才读取 `docs\NOTE-ORGANIZATION.md`。整理阶段完整阅读笔记后再判断长期价值：知识型/混合型继续 `archive`，只改文件名与路径；纯资源型才使用 `resource` 压缩进 `05-资源` 集合页。不得把该判断提前到生成阶段，也不得自动整理。

## 共享 Obsidian 样式依赖

共享 CSS 的唯一真源是：<https://github.com/ZiYao00/obsidian-learning-snippets>。

修改笔记版式或 Frontmatter 前，先读取 `config\obsidian-style.json`。本项目只使用 `learning-lab.css` Core 与 `video-note.css` Extension；不得在此仓库复制、重建、fork 或独立修改共享 CSS，也不得把受 Git 跟踪的项目目录 junction 到共享仓库。需要改共享视觉系统时，修改共享仓库，再同步到 Obsidian Vault。

ChatGPT、Codex、Hermes 与 WorkBuddy 的 `SKILL.md` 只是入口适配层，不应复制或改写核心规则。ChatGPT 与 Codex 使用共享 `scripts\run_bili_learning.py`，不得借用其它宿主的兼容入口。

准备 v1.0 提交、推送或 Release 时，先阅读 `docs/RELEASE-CHECKLIST.md`。不要把 `ComfyUI-Learning-Lab` 的独立工作区混入本仓库提交。
