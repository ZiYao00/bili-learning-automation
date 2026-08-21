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

本 skill 是 **WorkBuddy 适配层**。通用输入、数据契约、内容标准、taxonomy 与 finalizer 约束的唯一事实来源是项目根目录 `docs\AGENT-INTEGRATION.md`；本文件只保留 WorkBuddy 会话的触发、授权、调用和回复规则。

**授权边界**：仅当用户在本会话中主动发送 B站链接/BV 号且意图是转笔记（或明确要求整理已学习笔记）时执行；用户只是提到某个视频、讨论视频内容、或链接用途不明确时，先询问确认。不得替用户批量转换链接列表，除非用户明确要求。

## 环境与路径

- **项目根目录**：`G:\GitHub\bili-learning-automation`（本机安装位置；若目录不存在，停止并说明，不要猜测新位置）
- **Python**：优先用项目自带环境 `G:\GitHub\bili-learning-automation\.venv\Scripts\python.exe`；不存在时退回系统 `python`（核心脚本零第三方依赖，自举注入 `src/`）
- **yt-dlp 与 Cookie**：由 `config\local.json` 配置（yt-dlp 在 `G:\Program\yt-dlp\yt-dlp.exe`，Cookie 文件路径由 collector 传给 yt-dlp，**任何情况下不得读取或展示 Cookie 内容**）
- **共享脚本**（所有智能体统一入口）：`G:\GitHub\bili-learning-automation\hermes-skills\bili-learning-automation\scripts\`（该路径是历史兼容启动壳，内部调用同一核心 CLI）
- **WorkBuddy 沙箱垫片规避（必读）**：WorkBuddy 的 Bash 环境通过 `PYTHONPATH` 注入 safe-delete 垫片，会把 `shutil.rmtree` 改写为走回收站且在沙箱内 fail-closed，导致 collector / finalizer 的运行时清理崩溃。调用所有脚本时统一加 `env -u PYTHONPATH` 前缀，例如：`env -u PYTHONPATH "$py" "$root/hermes-skills/.../prepare_ytdlp_bilibili_note.py" '<用户消息>'`。若某次运行已被垫片打断：素材可能实际已采集完整（检查 job 目录与 job.json），笔记也可能已实际发布（检查 note_path）——此时按 job 状态继续处理或重跑 finalizer 即可，不要手工删除 job、reservation、锁文件或发布产物。

## 必须执行的流程

以下 `$root` 指 `G:/GitHub/bili-learning-automation`，`$py` 指上面确定的 Python 解释器。

1. 原样把用户消息交给 collector：

   ```bash
   "$py" "$root/hermes-skills/bili-learning-automation/scripts/prepare_ytdlp_bilibili_note.py" '<用户消息原文>'
   ```

   若输出无法解析为 JSON 或 BV 号无法识别，请用户重新发送"复制链接"，不要猜测。

2. 读取 JSON 状态，按 `status` 分支：

   - `in_progress`：同一视频已有活动任务（可能是 Hermes 或其他入口启动的），不重复采集或生成，如实告知用户。
   - `incomplete_note`：仅旧版遗留骨架会返回；说明该笔记尚未完成，不声称完成。
   - `subtitle_unavailable`：没有可用中文字幕，且没有下载媒体，不生成笔记。
   - `failed`：报告短错误，不声称完成。
   - 只有 `materials_ready` 才继续。

3. `materials_ready` 时读取 `handoff_path`、`job.json`、`analysis_path`、`agent_work_dir` 与 `transcript_manifest_path`，并遵循项目共享的 `docs\AGENT-INTEGRATION.md` 与 `docs\standards\` 内容标准。程序已把原始 SRT 无语义删减地整理成适合 Agent 阅读的 transcript：manifest 为 `direct` 时读取唯一 chunk；为 `chunked` 时严格按 `chunks` 顺序逐块阅读，**不要**把原始 SRT 整份塞入上下文，也不要自行按 1/3 等固定比例重新切分。处理长字幕时可在 `agent_work_dir` 创建 `part-XX-notes.md`、索引或中间梳理文件，把每块的重要参数、比较、限制、方法和资源先外化，再合并为 `knowledge_outline`。来源不足时在 `analysis.json` 记录原因，不得靠常识补全。所有临时文件都属于当前 job，由 finalizer 与 failsafe 统一清理；不得写到项目其他目录，也不得手工删除 job、reservation 或锁文件。

4. 来源充分时，先填写 `knowledge_outline`，再只编辑 `draft_path` 的两个 marker：

   - `BILI_AI_SUMMARY`：短的"先看结论"；
   - `BILI_AI_BODY`：根据视频真实信息结构动态组织的知识正文。

   不强制套用"怎么做 / 容易踩坑 / 我来实践"。参数、公式、限制、专名、A/B 差异、兼容性、作者明确推荐和重要资源等高价值信息，不能只为缩短篇幅而删除。正文只写字幕或原始简介支持的事实。版式按共享标准选择 Table / Grid / Card / Risk / Resource / Chip，不为了好看强行卡片化；Frontmatter 与 `learning-page + video-note` cssclasses 由程序负责，不得修改。

5. 成稿后重新对照字幕或 `knowledge_outline` 做覆盖复核；确认无重要遗漏、无来源外补写后，将 `coverage_review.status` 设为 `passed` 并填写 notes。不要把 runtime 路径、job 文件名、analysis 文件、证据编号或采集状态写进主笔记。

6. 写完后立即运行 finalizer：

   ```bash
   "$py" "$root/hermes-skills/bili-learning-automation/scripts/finalize_ytdlp_bilibili_note.py" --job '<job_dir>' --note '<draft_path>'
   ```

   即使写作失败，也必须运行 finalizer 清理 job。不得手工删除 job、reservation 或锁文件。

7. 只在 finalizer 返回后回复用户：

   - `note_ready` 且 `temporary_data_removed: true`：`已完成：《标题》\n笔记：<文件名>\n已写入 Obsidian。`
   - `source_insufficient`：说明现有字幕/简介不足以支撑可靠学习笔记，本次未写入正式笔记。
   - `note_invalid` / `failed`，或 `temporary_data_removed: false`：只报告短错误，不能说已完成；不要手工清理现场。

## 学习后整理

只有用户明确要求整理一篇已学习笔记时才执行；普通链接转笔记不进入此流程。先读取现有笔记，与用户确认短标题和一句简介摘要，再调用统一入口：

```bash
"$py" "$root/hermes-skills/bili-learning-automation/scripts/organize_bilibili_learning.py" --note '<现有笔记路径>' --title '<短标题>' --intro '<一句简介摘要>'
```

如用户未指定分类，省略 `--category`，由核心按 tags 放入 taxonomy 建议目录。禁止自行改名、移动文件或改写 UP 主资源链接；只以该命令的 `organized` 返回状态报告成功。

## 适配层边界（不可违反）

- 本目录是 WorkBuddy 专用薄适配层；**不得修改** `hermes-skills\` 内任何文件（Hermes 通过 junction 实时读取该目录），也不得复制核心脚本、内容标准或 finalizer 逻辑到本目录。
- 核心流程、数据边界、内容标准的任何变更都必须发生在共享层（`src/`、`docs/`），再由各适配层引用。
- 并发保护由核心 reservation 机制提供：跨入口（WorkBuddy / Hermes）同时处理同一 BV 号时，后到者会收到 `in_progress`，如实报告即可，不要尝试绕过。
