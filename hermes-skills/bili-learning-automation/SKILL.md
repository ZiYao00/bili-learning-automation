---
name: bili-learning-automation
description: Turn a Bilibili copied link, supported Bilibili short link, or BV id received in the owner's private conversation into a subtitle-first Obsidian learning note without downloading media. No command prefix is required.
---

# B站视频转笔记

把 owner 私聊中的 B站复制链接、受支持的 Bilibili 短链接或 BV 号视为生成一篇学习笔记的请求。

本 skill 是 Hermes/微信适配层。通用输入、数据、笔记和 finalizer 约束的唯一来源是项目根目录 `docs\AGENT-INTEGRATION.md`；本文件只保留 Hermes 私聊的触发、调用和回复规则。

只在 owner 私聊中运行；群聊或发送者范围不确定时先确认。过程消息与最终回复统一使用简体中文；代码、路径、模型名和原始专有名词除外。

## Mandatory workflow

1. 原样把收到的消息交给 collector：

   ```powershell
   $installedSkill = Get-Item "$env:LOCALAPPDATA\hermes\skills\bili-learning-automation"
   $skillSource = [string]$installedSkill.Target
   $project = Split-Path (Split-Path $skillSource -Parent) -Parent
   python "$project\hermes-skills\bili-learning-automation\scripts\prepare_ytdlp_bilibili_note.py" '<received message text>'
   ```

2. 读取 JSON 状态：

   - `configuration_required`：**不要继续采集**。说明尚未绑定 Obsidian Vault，并询问 owner 的 Vault 根目录（即包含 `.obsidian` 的目录）。owner 在当前私聊提供路径后执行 `python "$project\\hermes-skills\\bili-learning-automation\\scripts\\configure_bilibili_learning.py" --vault '<Vault根目录>' --notes-subdir 'bilibili'`；只有返回 `configured` 才可重新使用本会话中之前收到的 B站链接执行步骤 1。若 owner 明确指定 Vault 内其他相对子目录，则使用其指定值。不得自动扫描整块磁盘、不得未经确认选择 Vault。
   - `in_progress`：不重复采集。若响应带 `job_dir`，且 `reservation_age_seconds >= 1800`，只检查该绑定 job：`job.json`、`analysis_path`、`draft_path`、`transcript_manifest_path` 与 manifest 中全部 chunks 都存在，草稿两个 AI marker 仍未填写且 `analysis.json` 仍为 pending 时，视为可续做的中断任务，直接从步骤 3 继续；不要先跑 doctor。条件不满足则按活动任务处理，不抢占、不手工删锁。只有文件缺失、路径矛盾或状态异常时才运行 doctor 诊断。
   - `incomplete_note`：仅旧版遗留骨架会返回；说明该笔记尚未完成，不声称完成。
   - `subtitle_unavailable`：说明没有可用中文字幕，且没有下载媒体，不生成笔记。
   - `failed` 且 `code = ytdlp_not_configured`：说明当前电脑未检测到 yt-dlp，并给 owner `winget install yt-dlp`。**只提供命令，不自动执行安装，也不要把 `yt-dlp.exe` 复制进 Skill / 仓库。** 安装完成后重新执行原请求；只有 owner 明确使用自定义 yt-dlp 位置时才配置 `BILI_LEARNING_YTDLP` 或 `local.json.ytdlp`。
   - 其它 `failed`：回复短错误，不声称完成。
   - `materials_ready`，或满足上述“可续做中断任务”条件的 `in_progress`，才继续。

3. 进入可处理状态后读取 `handoff_path`（新任务）或绑定 job 内的 `job.json`（续做任务），再读取 `analysis_path`、`agent_work_dir` 与 `transcript_manifest_path`，并遵循项目共享的 `docs\\AGENT-INTEGRATION.md` 与内容标准。程序已把原始 SRT 无语义删减地整理成适合 Agent 阅读的 transcript：manifest 为 `direct` 时读取唯一 chunk；为 `chunked` 时严格按 `chunks` 顺序逐块阅读。单个 chunk 在工具限制内时优先一次完整读取，只有工具明确返回截断/continuation 时才继续读取剩余部分；不要主动把一个 chunk 再拆成多次读取，也不要把原始 SRT 整份塞入上下文或自行重新按固定比例切分。处理长字幕、百科型或参数密集内容时，在 `agent_work_dir` 创建 `part-XX-notes.md`、事实清单或中间梳理文件，把每块的具体成员、数值、关系、适用条件、例外、冲突、兼容性和作者评价先原子化外化，再合并为 `knowledge_outline`；不要先压成几个主题概括。来源不足时在 `analysis.json` 记录原因，不得靠常识补全。所有临时文件都属于当前 job，由 finalizer 与 failsafe 统一清理；不得写到项目其他目录，也不得手工删除 job、reservation 或锁文件。

4. 来源充分时，先填写 `knowledge_outline`，再只编辑 `draft_path` 的两个 marker：

   - `BILI_AI_SUMMARY`：短的“先看结论”；
   - `BILI_AI_BODY`：根据视频真实信息结构动态组织的知识正文。

   不强制套用“怎么做 / 容易踩坑 / 我来实践”。参数、公式、限制、专名、A/B 差异、兼容性、作者明确推荐和重要资源等高价值信息，不能只为缩短篇幅而删除；表达可以压缩，但字幕明确给出的成员来源、继承、步数、适用条件、例外和冲突关系必须保留。正文只写字幕或原始简介支持的事实。版式按共享标准选择 Table / Grid / Card / Risk / Resource / Chip，不为了好看强行卡片化；Frontmatter 与 `learning-page + video-note` cssclasses 由程序负责，Hermes 不修改。

5. 成稿后必须重新按 manifest 顺序抽查或复读原 transcript；`knowledge_outline` 只能辅助检查，不能替代回看字幕。知识密集型内容还要对照事实清单，确认成员关系、可直接使用值、例外和比较没有被二次压缩；修正遗漏后再将 `coverage_review.status` 设为 `passed` 并填写 notes。不要把 runtime 路径、job 文件名、analysis 文件、证据编号或采集状态写进主笔记。

6. 写完后立即 finalizer：

   ```powershell
   python "$project\hermes-skills\bili-learning-automation\scripts\finalize_ytdlp_bilibili_note.py" --job '<job_dir>' --note '<draft_path>'
   ```

   即使写作失败，也必须运行 finalizer 清理 job。不得手工删除 job、reservation 或锁文件。

7. 只在 finalizer 返回后回复：

   - `note_ready` 且 `temporary_data_removed: true`：`已完成：《标题》\n笔记：<文件名>\n已写入 Obsidian。`
   - `source_insufficient`：说明现有字幕/简介不足以支撑可靠学习笔记，本次未写入正式笔记。
   - `note_invalid` / `failed`，或 `temporary_data_removed: false`：只报告短错误，不能说已完成；不要手工清理现场。

## 学习后整理

只有 owner 明确要求整理一篇已学习笔记时才执行；普通链接转笔记不进入此流程。先读取现有笔记，与 owner 的学习重点确认短标题和一句简介摘要，再调用统一入口：

```powershell
python "$project\hermes-skills\bili-learning-automation\scripts\organize_bilibili_learning.py" --note '<现有笔记路径>' --title '<短标题>' --intro '<一句简介摘要>'
```

如 owner 未指定分类，省略 `--category`，由核心按 tags 放入 taxonomy 建议目录。禁止 Hermes 自行改名、移动文件或改写 UP 主资源链接；只以该命令的 `organized` 返回状态报告成功。

## Maintenance

本机可选运维文档可在仓库外单独维护；它不是项目运行前置条件，也不能覆盖仓库内的正式标准。
