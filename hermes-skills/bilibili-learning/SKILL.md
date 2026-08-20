---
name: bilibili-learning
description: Turn a Bilibili copied link, supported Bilibili short link, or BV id received in the owner's private conversation into a subtitle-first Obsidian learning note without downloading media. No command prefix is required.
---

# B站视频转笔记

把 owner 私聊中的 B站复制链接、受支持的 Bilibili 短链接或 BV 号视为生成一篇学习笔记的请求。

本 skill 是 Hermes/微信适配层。所有智能体共用的输入、数据、笔记与 finalizer 约束见项目根目录 `docs\AGENT-INTEGRATION.md`；本文件只增加 Hermes 私聊、安装与回复规则。

## Hard boundaries

- 只在 owner 私聊中运行；群聊或发送者范围不确定时先确认。
- 永远不要读取、打印、上传、编辑或提交 Cookie 内容；collector 只可把配置的 Cookie 文件路径传给 yt-dlp。
- 默认流程不下载视频或音频，不启动 Chrome/CDP，不回退到 ASR。
- 字幕只接受 `ai-zh` 和 `zh.*`。
- 不覆盖现有笔记；同 source 先判重，不同 source 即使标题相同也必须写入不同 BVID 文件。
- 原始字幕、元数据、简介和日志只存在于 `.runtime/bilibili-learning` 的临时 job 中，finalizer 无论成败都要清理。

## Mandatory workflow

1. 原样把收到的消息交给 collector：

   ```powershell
   $installedSkill = Get-Item "$env:LOCALAPPDATA\hermes\skills\bilibili-learning"
   $skillSource = [string]$installedSkill.Target
   $project = Split-Path (Split-Path $skillSource -Parent) -Parent
   python "$project\hermes-skills\bilibili-learning\scripts\prepare_ytdlp_bilibili_note.py" '<received message text>'
   ```

2. 读取 JSON 状态：

   - `already_exists`：回复已有文件名，不继续。
   - `incomplete_note`：说明已有未完成骨架，不声称完成；先处理该笔记或等待当前任务结束。
   - `subtitle_unavailable`：说明没有可用中文字幕，且没有下载媒体，不生成笔记。
   - `failed`：回复短错误，不声称完成。
   - 只有 `materials_ready` 才继续。

3. `materials_ready` 时读取 `handoff_path`、`job.json`、`subtitle_path`，并阅读：

   ```text
   docs\standards\CODEX-VIDEO-NOTE-GUIDE.md
   docs\standards\STANDARD-VIDEO-NOTE-EXAMPLE.md
   config\bilibili-note-taxonomy.json
   ```

4. `note_path` 已由程序写入确定性骨架。不要改动：

   - Frontmatter：`author`、`published`、`duration`、`source`、`tags`
   - H1
   - UP 主原始简介
   - Bilibili iframe
   - 文件路径与文件名
   - `BILI_AI_*_START/END` marker

5. 只在四组 marker 内填写：

   - `BILI_AI_SUMMARY`：短的“先看结论”；
   - `BILI_AI_STEPS`：`## 怎么做`；
   - `BILI_AI_PITFALLS`：`## 容易踩坑`；
   - `BILI_AI_PRACTICE`：简短实践清单。

   只写字幕或原始简介支持的事实。不要把临时路径、job 文件名、证据编号、采集状态写进主笔记。

6. 写完后立即 finalizer：

   ```powershell
   python "$project\hermes-skills\bilibili-learning\scripts\finalize_ytdlp_bilibili_note.py" --job '<job_dir>' --note '<note_path>'
   ```

   即使写作失败，也必须运行 finalizer 清理 job。

7. 只在 finalizer 返回后回复：

   - `note_ready`：`已完成：《标题》\n笔记：<文件名>\n已写入 Obsidian。`
   - `note_invalid` / `failed`：只报告短错误，不能说已完成。

## Maintenance

本机可选运维文档可在仓库外单独维护；它不是项目运行前置条件，也不能覆盖仓库内的正式标准。
