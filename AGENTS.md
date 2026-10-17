# B站视频转笔记

本项目服务 ChatGPT、Codex、Hermes 与 WorkBuddy。Codex、Hermes、WorkBuddy 通过目录链接共享同一个 canonical Skill；ChatGPT Web 使用由该 Skill 构建的独立 ZIP。四个宿主共用同一套环境门禁、来源采集、Job lifecycle、taxonomy、确定性笔记骨架、校验、发布、导航和清理逻辑。

## 安装验收、首次使用与环境门禁

下面两类任务都要运行统一 `bili-learning onboarding`（或等价入口）：

1. “生成 B站学习笔记”：正式采集前先检查；
2. “安装 / 检查 / 验证 / 初始化 / 确认 bili-learning-automation 是否可用”：先确认当前入口或安装链接有效，再运行 onboarding。不能只验证文件存在、链接目标或 Skill 内容一致就结束。

如果用户只是分析、解释或编辑仓库源码，并没有要求检查当前本机是否可用，不强制运行 onboarding。不要根据仓库示例、本机历史或模型记忆猜测用户路径。

安装验收的反馈要明确区分“Skill 已安装”和“运行环境已就绪”。只有安装有效且 onboarding `ready`，才能告诉用户当前可以直接使用。

- `status = ready`：简要报告 Python、yt-dlp、Bilibili Cookie、Obsidian Vault 与 CSS 的就绪状态；不要展示 Cookie 内容。安装 / 验证任务到这里结束，生成笔记任务才继续采集。
- `status = action_required`：可以说明 Skill 安装成功，但必须明确运行环境尚未就绪；停止采集，只处理返回的 `actions`。Vault 要求用户提供直接包含 `.obsidian` 的根目录；Cookie 只接收 Netscape 文件路径，不读取或复述内容，不知道如何获取时指向 `docs/BILIBILI-COOKIE.md`；yt-dlp **只能使用项目内 `tools/yt-dlp.exe`**，缺失时让 Agent 恢复并校验官方单文件 EXE，禁止搜索系统 PATH、运行 winget、改 `local.json.ytdlp` 或静默下载。
- `warnings` 中的 CSS 缺失不阻塞笔记生成，但首次出现时应告知：共享真源是 `obsidian-learning-snippets`，需要 `learning-lab.css + video-note.css`，程序不会静默复制或覆盖；安装后还要在 Obsidian“设置 → 外观 → CSS 代码片段”中启用。
- 配置后重新运行 onboarding；只有 `ready` 才进入采集或把环境描述为“可直接使用”。`prepare` 自身也有同一门禁，若返回 `onboarding_required`，按其 `actions / warnings` 处理后重试原链接。

## Agent 主导安装（不提供双击向导）

- 安装/初始化任务先读 `docs/QUICKSTART.md` 与 `docs/LOCAL-AGENT-INSTALL.md`，由具备当前环境权限的 Agent 完成检测、配置、Junction 创建和 onboarding 验收，不要求普通用户执行 PowerShell 或编辑 JSON；不要假设每位用户都有 CodexPro。**必须先执行 `scripts/run_bili_learning.ps1 -ProbeOnly`**，再运行 `scripts/run_bili_learning.ps1 onboarding`。Python 和 `.venv` 不随仓库分发；缺少 Python 时，需取得明确的系统安装授权后由 Agent 准备 Python 3.12，禁止无授权静默安装。共享的 `scripts/python_runtime.ps1` 负责验证解释器，可信外部 Python 可临时通过 `BILI_LEARNING_PYTHON` 指定；指定失效须停下，不可悄然切换解释器。
- Windows 本地 Codex/Hermes/WorkBuddy 的 Skill 安装：`scripts/install_agent_skill.ps1 -Agent <Codex|Hermes|WorkBuddy>` 默认只输出计划；确认具体用户级目录写入权限和用户授权后才使用 `-Apply`。Vault → 项目 notes 只使用 `scripts/ensure_junction.ps1` 进行有保护的计划/安装。
- `planned` 不等于安装成功；`conflict` 时停止，禁止自动删除或迁移现有目录/笔记/Skill。新用户通过 `configure-obsidian` 建立推荐 Hybrid 配置，旧 direct-vault 不做静默迁移。ChatGPT Web 的 Skill ZIP 和本地连接须按其平台权限单独安装/授权。
- `local-ASR-service` 是独立可选服务，不进入首次安装，不复制/安装/启动它的源码和模型；只在用户明确授权 ASR 后检查并调用。

## 先选择来源，再读取任务模式

不得根据标题、历史 memory 或模型猜测自动跳过字幕。默认“转换链接”使用 `prepare / subtitle_srt`；当前消息明确要求“纯资源分享 / 只整理简介 / 不用字幕 / 跳过字幕”才使用 `prepare-description / description_only`；默认入口返回 `subtitle_unavailable` 后，只有用户明确授权 ASR 才先运行 `asr-health`，服务 `ready` 时使用 `prepare-asr / asr_text` 调用外部 `local-ASR-service`。`prepare-asr` 只在明确授权后临时下载音轨，转录完成即清理临时媒体，再把真实纯文本回流现有 `prepare-transcript` Job lifecycle；服务不可用时停止，不在本项目安装、复制或启动另一套 ASR Pipeline。用户已经通过其它授权工具取得真实纯文本时，仍可直接使用 `prepare-transcript / asr_text`。

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
- 正文事实只来自当前 Job 允许的来源：SRT 字幕、明确授权后的 ASR 纯文本、确定性采集到的 UP 主简介 / UP 主置顶一级评论、以及明确标注的用户补充来源；`description_only` 仍不得推断视频口播、画面参数或未提供的资源本体。置顶评论默认只在来源明确指向评论区资源时做一次匿名只读补充；仅当用户在被 Git 忽略的 `config/pinned-comment-whitelist.local.json` 中主动配置并命中 UP 主身份时，才允许使用项目现有 Netscape Cookie 做且只做一次只读查询。不得回退读取公开模板或预置任何 UP 主。两种模式都不翻页、不抓普通评论或楼中楼、不重试，失败或不存在不得阻塞任务；抓到置顶也不等于内容必然与当前视频主题相关，Agent 仍需按当前视频来源判断相关性。来源不足时停止，不用模型常识补具体参数、资源或结论。
- 不覆盖已有笔记，不把 Cookie、runtime 路径、日志或内部状态写进正式笔记。
- 本机笔记数据以 `settings.notes_root` 为唯一物理真源；推荐并当前采用 `<repo-root>\notes\bilibili`，该目录被 Git 忽略。Obsidian 的 `<vault_root>\<notes_subdir>` 只作为 Junction 映射到 `notes_root`，方向必须是 **Vault → 项目 notes**，不得把项目 `notes\bilibili` 反向链接到工作区外。Agent 编辑、finalize、整理和查重都必须使用 Job / Settings 返回的 `notes_root` 路径，不得自行改写为 Vault 路径。
- `config\local.json`、`notes\**`、`key\*`、`.runtime\*` 都是本机数据，禁止提交；只允许跟踪空目录占位文件和公开 example。onboarding 出现 `obsidian_notes_mapping_invalid` 时停止采集，先修复 Junction。
- 视频简介抓取失败不能当作视频没有简介。
- finalizer 返回 `note_ready` 即表示业务完成；临时数据采用 retire/维护语义，`temporary_data_retired` 或 `cleanup_warning` 不得覆盖已成功的发布结果。
- 学习后整理默认关闭。用户明确要求并确认 `single / latest / all` 范围后才读取 `docs\NOTE-ORGANIZATION.md`；默认只在 notes_root 内调整归档目录，保留原文件名、Markdown 全部字节、原始标题与 Frontmatter，并刷新导航。批量 `organize-list` → Agent 逐篇阅读/制定 runtime 计划 → `organize-batch` 预览 → 授权后 `--apply`；哈希变化、重名、同 BVID 重复和潜在断链一律跳过。重复版本仅通过独立 `organize-duplicates` 的精确保留/回收计划、明确授权和 Windows 回收站清理。旧 `resource` 有损压缩仅在单独授权后可用，默认不得启动，也不回退永久删除。

## 共享 Obsidian 样式依赖

共享 CSS 的唯一真源是：<https://github.com/ZiYao00/obsidian-learning-snippets>。

修改笔记版式或 Frontmatter 前，先读取 `config\obsidian-style.json`。本项目只使用 `learning-lab.css` Core 与 `video-note.css` Extension；不得在此仓库复制、重建、fork 或独立修改共享 CSS，也不得把受 Git 跟踪的项目目录 junction 到共享仓库。需要改共享视觉系统时，修改共享仓库，再同步到 Obsidian Vault。

唯一需要人工维护的本地 Skill 真源是 `skill\bili-learning-automation\SKILL.md`。Codex、Hermes、WorkBuddy 的用户级 Skill 目录都应直接 Junction 到 `skill\bili-learning-automation\`，仓库不维护宿主副本。`skill\bili-learning-automation\scripts\local_bridge.*` 只处理 Junction、Python 与宿主进程兼容，所有业务规则仍复用共享核心。ChatGPT Web ZIP 由 `scripts\build_chatgpt_skill.py` 从 canonical Skill 与当前公开文档生成；包内 references 只是构建快照，连接本地项目后仍以根目录 `AGENTS.md`、当前 Job handoff 与本地文档为运行事实源。

准备正式提交、推送或 Release 时，先阅读 `docs/RELEASE-CHECKLIST.md`。不要把 `ComfyUI-Learning-Lab` 的独立工作区混入本仓库提交。
