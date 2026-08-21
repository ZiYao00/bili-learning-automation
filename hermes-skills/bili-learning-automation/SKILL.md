---
name: bili-learning-automation
description: Turn a Bilibili copied link, supported Bilibili short link, or BV id received in the owner's private conversation into a subtitle-first Obsidian learning note without downloading media. No command prefix is required.
---

# B站视频转笔记

把 owner 私聊中的 B站复制链接、受支持的 Bilibili 短链接或 BV 号视为生成一篇学习笔记的请求。

本 skill 是 Hermes/微信适配层。通用输入、数据、笔记和 finalizer 约束的唯一来源是项目根目录 `docs\AGENT-INTEGRATION.md`；本文件只保留 Hermes 私聊的触发、调用和回复规则。

只在 owner 私聊中运行；群聊或发送者范围不确定时先确认。

## Mandatory workflow

1. 原样把收到的消息交给 collector：

   ```powershell
   $installedSkill = Get-Item "$env:LOCALAPPDATA\hermes\skills\bili-learning-automation"
   $skillSource = [string]$installedSkill.Target
   $project = Split-Path (Split-Path $skillSource -Parent) -Parent
   python "$project\hermes-skills\bili-learning-automation\scripts\prepare_ytdlp_bilibili_note.py" '<received message text>'
   ```

2. 读取 JSON 状态：

   - `in_progress`：说明同一视频已有活动任务，不重复采集或生成。
   - `incomplete_note`：仅旧版遗留骨架会返回；说明该笔记尚未完成，不声称完成。
   - `subtitle_unavailable`：说明没有可用中文字幕，且没有下载媒体，不生成笔记。
   - `failed`：回复短错误，不声称完成。
   - 只有 `materials_ready` 才继续。

3. `materials_ready` 时读取 `handoff_path`、`job.json`、`subtitle_path`、`analysis_path`，并遵循项目共享的 `docs\\AGENT-INTEGRATION.md` 与内容标准。先判断字幕/简介是否足以支撑可信学习笔记；来源不足时在 `analysis.json` 记录原因，不得靠常识补全。直接读取原始 SRT；输出受限时分段读取，不得在 job 内生成 `_flat.txt`、缓存或任何临时副本。确需临时文件时只能使用系统 Temp，并在 `finally` 中立即删除。

4. 来源充分时，先填写 `knowledge_outline`，再只编辑 `draft_path` 的两个 marker：

   - `BILI_AI_SUMMARY`：短的“先看结论”；
   - `BILI_AI_BODY`：根据视频真实信息结构动态组织的知识正文。

   不强制套用“怎么做 / 容易踩坑 / 我来实践”。参数、公式、限制、专名、A/B 差异、兼容性、作者明确推荐和重要资源等高价值信息，不能只为缩短篇幅而删除。正文只写字幕或原始简介支持的事实。版式按共享标准选择 Table / Grid / Card / Risk / Resource / Chip，不为了好看强行卡片化；Frontmatter 与 `learning-page + video-note` cssclasses 由程序负责，Hermes 不修改。

5. 成稿后重新对照字幕或 `knowledge_outline` 做覆盖复核；确认无重要遗漏、无来源外补写后，将 `coverage_review.status` 设为 `passed` 并填写 notes。不要把 runtime 路径、job 文件名、analysis 文件、证据编号或采集状态写进主笔记。

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
