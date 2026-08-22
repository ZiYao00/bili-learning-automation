---
name: bili-learning-automation
description: "Turn a Bilibili copied link, supported short link, or BV id provided by the user in the current WorkBuddy conversation into a subtitle-first Obsidian learning note without downloading media. Use when the user asks to convert a Bilibili video into a note, or to organize an already-learned note."
description_zh: "B站视频转笔记：把用户在会话中提供的 B站链接 / 短链 / BV 号转成字幕优先的 Obsidian 学习笔记（不下载音视频），以及学习后整理归档"
description_en: "Convert Bilibili videos into subtitle-first Obsidian learning notes; also organize learned notes"
version: 1.0.0
display_name: "B站视频转笔记"
display_name_en: "Bili Video to Note"
visibility: "private"
---

# B站视频转笔记（WorkBuddy 适配层）

把用户在当前 WorkBuddy 会话中主动提供的 B站复制链接、受支持短链接或 BV 号，视为生成一篇学习笔记的请求。

本 skill 是 **WorkBuddy 薄适配层**。通用输入、数据契约、内容标准、taxonomy 与 finalizer 约束的唯一事实来源是项目根目录 `docs\AGENT-INTEGRATION.md`；本目录只负责 WorkBuddy 的触发、授权与启动桥接，不复制核心业务逻辑。

**授权边界**：仅当用户在本会话中主动发送 B站链接/BV 号且意图是转笔记（或明确要求整理已学习笔记）时执行。用户只是提到某个视频、讨论视频内容、或链接用途不明确时先确认。除非用户明确要求，不得批量转换链接列表。

## 环境与路径

- 安装目录固定按 WorkBuddy 约定使用 `~/.workbuddy/skills/bili-learning-automation`；推荐通过 Junction 指向仓库中的 `workbuddy-skills/bili-learning-automation`。
- **不要硬编码仓库绝对路径。** `scripts/bridge.ps1` 先解析安装 Junction 的真实目标，再由 `bridge.py` 调用共享 `src/bili_learning`。
- 核心运行时只需要 Python 3.10+。PowerShell bridge 优先使用项目自己的 `.venv\Scripts\python.exe`，不存在时才尝试系统 `python` / `py -3`；因此不依赖某台机器上的固定 `.venv` 绝对路径。
- yt-dlp、Cookie、Obsidian Vault 等本机配置全部来自项目 `config/local.json` 或受支持环境变量；任何情况下不得读取、展示或复述 Cookie 内容。
- WorkBuddy Bash 环境可能通过 `PYTHONPATH` 注入 safe-delete 垫片，导致 runtime 清理失败。`bridge.ps1` 会在启动 Python 前清除该环境变量。

以下命令中的 `$runner` 定义为：

```bash
runner="$HOME/.workbuddy/skills/bili-learning-automation/scripts/bridge.ps1"
```

如果该文件不存在，停止并说明 WorkBuddy Skill 安装无效；不要猜测仓库位于 `G:\GitHub` 或其他固定目录。

## 必须执行的流程

1. 原样把用户消息交给 collector：

   ```bash
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" prepare '<用户消息原文>'
   ```

   若输出无法解析为 JSON 或 BV 号无法识别，请用户重新发送“复制链接”，不要猜测。

2. 读取 JSON 状态并分支：

   - `configuration_required`：**不要继续采集**。说明尚未绑定 Obsidian Vault，并询问用户的 Vault 根目录（即包含 `.obsidian` 的目录）。用户在当前会话提供路径后执行：

     ```bash
     powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" configure-obsidian --vault '<Vault根目录>' --notes-subdir 'bilibili'
     ```

     只有返回 `configured` 才可重新使用用户之前发送的 B站链接执行步骤 1。若用户希望放入 Vault 内其他目录，可把 `bilibili` 换成其明确指定的相对子目录。不得自动扫描整块磁盘、不得未经确认选择某个 Vault。
   - `in_progress`：同一视频已有活动任务，不重复采集或生成，如实告知用户。
   - `incomplete_note`：仅旧版遗留骨架会返回；说明笔记尚未完成，不声称完成。
   - `subtitle_unavailable`：没有可用中文字幕，且没有下载媒体，不生成笔记。
   - `failed` 且 `code = ytdlp_not_configured`：说明当前电脑未检测到 yt-dlp，并给用户 `winget install yt-dlp`。**只提供命令，不自动执行安装，也不要把 `yt-dlp.exe` 复制进 Skill / 仓库。** 安装完成后让用户重新运行原请求；若用户明确使用自定义 yt-dlp 路径，再指导配置 `BILI_LEARNING_YTDLP` 或 `local.json.ytdlp`。
   - 其它 `failed`：报告短错误，不声称完成。
   - 只有 `materials_ready` 才继续。

3. `materials_ready` 时读取 `handoff_path`、`job.json`、`analysis_path`、`agent_work_dir` 与 `transcript_manifest_path`，并遵循项目共享的 `docs\AGENT-INTEGRATION.md` 与 `docs\standards\` 内容标准。程序已把原始 SRT 无语义删减地整理成适合 Agent 阅读的 transcript：manifest 为 `direct` 时读取唯一 chunk；为 `chunked` 时严格按 `chunks` 顺序逐块阅读，**不要**把原始 SRT 整份塞入上下文，也不要自行按固定比例重新切分。处理长字幕时可在 `agent_work_dir` 创建当前 job 专用的中间梳理文件。来源不足时在 `analysis.json` 记录原因，不得靠常识补全。所有临时文件都属于当前 job，由 finalizer 与 failsafe 统一清理；不得写到项目其他目录，也不得手工删除 job、reservation 或锁文件。

4. 来源充分时，先填写 `knowledge_outline`，再只编辑 `draft_path` 的两个 marker：

   - `BILI_AI_SUMMARY`：短的“先看结论”；
   - `BILI_AI_BODY`：根据视频真实信息结构动态组织的知识正文。

   不强制套用“怎么做 / 容易踩坑 / 我来实践”。参数、公式、限制、专名、A/B 差异、兼容性、作者明确推荐和重要资源等高价值信息，不能只为缩短篇幅而删除。正文只写字幕或原始简介支持的事实。Frontmatter 与 `learning-page + video-note` cssclasses 由程序负责，不得修改。

5. 成稿后重新对照字幕或 `knowledge_outline` 做覆盖复核；确认无重要遗漏、无来源外补写后，将 `coverage_review.status` 设为 `passed` 并填写 notes。不要把 runtime 路径、job 文件名、analysis 文件、证据编号或采集状态写进主笔记。

6. 写完后立即运行 finalizer：

   ```bash
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" finalize --job '<job_dir>' --note '<draft_path>'
   ```

   即使写作失败，也必须运行 finalizer 清理 job。不得手工删除 job、reservation 或锁文件。

7. 只在 finalizer 返回后回复用户：

   - `note_ready` 且 `temporary_data_removed: true`：`已完成：《标题》\n笔记：<文件名>\n已写入 Obsidian。`
   - `source_insufficient`：说明现有字幕/简介不足以支撑可靠学习笔记，本次未写入正式笔记。
   - `note_invalid` / `failed`，或 `temporary_data_removed: false`：只报告短错误，不能说已完成；不要手工清理现场。

## 学习后整理

只有用户明确要求整理一篇已学习笔记时才执行；普通链接转笔记不进入此流程。先读取现有笔记，与用户确认短标题和一句简介摘要，再调用统一入口：

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" organize --note '<现有笔记路径>' --title '<短标题>' --intro '<一句简介摘要>'
```

如用户未指定分类，省略 `--category`，由核心按 tags 放入 taxonomy 建议目录。禁止自行改名、移动文件或改写 UP 主资源链接；只以该命令的 `organized` 返回状态报告成功。

## 诊断

遇到配置、CSS、yt-dlp、Cookie 或路径问题时运行：

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" doctor --json
```

- `notes_repository_fallback`：尚未显式绑定 Vault，新采集会被核心阻止；
- `obsidian_vault_detected`：确认 `vault_root` 是否真的是包含 `.obsidian` 的 Vault 根；
- `obsidian_snippet_learning_lab` / `obsidian_snippet_video_note`：检查两份 CSS 是否已经存在于 Vault 根的 `.obsidian/snippets/`。

CSS 缺失属于可诊断警告，不得静默覆盖用户已有 CSS；按项目 `docs\OBSIDIAN-STYLING.md` 指导用户安装或更新。

## 适配层边界（不可违反）

- 本目录是 WorkBuddy 专用薄适配层；不得复制核心 collector、内容标准、taxonomy 或 finalizer 逻辑到本目录。
- 核心流程、数据边界、内容标准的变更发生在共享层（`src/`、`docs/`），适配层只负责启动与平台差异。
- 并发保护由核心 reservation 机制提供：跨入口同时处理同一 BV 号时，后到者会收到 `in_progress`，如实报告即可，不要绕过。
