---
name: bilibili-learning
description: Turn a Bilibili copied link, supported Bilibili short link, or BV id received in the owner's private conversation into a subtitle-first Obsidian learning note without downloading media. No command prefix is required.
---

# B站视频转笔记

把 owner 私聊中的 B站复制链接、受支持的 Bilibili 短链接或 BV 号视为生成一篇学习笔记的请求。

本 skill 是 Hermes/微信适配层。通用输入、数据、笔记和 finalizer 约束的唯一来源是项目根目录 `docs\AGENT-INTEGRATION.md`；本文件只保留 Hermes 私聊的触发、调用和回复规则。

`--allow-existing-for-test` 是 Codex 本地回归测试开关；Hermes 入口明确禁止使用，日常链接始终先判重。

只在 owner 私聊中运行；群聊或发送者范围不确定时先确认。

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
   - `in_progress`：说明同一视频已有活动任务，不重复采集或生成。
   - `incomplete_note`：仅旧版遗留骨架会返回；说明该笔记尚未完成，不声称完成。
   - `subtitle_unavailable`：说明没有可用中文字幕，且没有下载媒体，不生成笔记。
   - `failed`：回复短错误，不声称完成。
   - 只有 `materials_ready` 才继续。

3. `materials_ready` 时读取 `handoff_path`、`job.json`、`subtitle_path`。只编辑 `draft_path` 的四组 marker，不改 Frontmatter、H1、BVID 小字、简介、iframe、文件名、路径或 marker 本身。所有新笔记由程序先发布到 `00-待整理`；H1 默认是 B站原视频标题，分类建议和 tags 已由程序确定，不需要重新读取 taxonomy。

4. 只在四组 marker 内填写：

   - `BILI_AI_SUMMARY`：短的“先看结论”；
   - `BILI_AI_STEPS`：`## 怎么做`；
   - `BILI_AI_PITFALLS`：`## 容易踩坑`；
   - `BILI_AI_PRACTICE`：简短实践清单。

   只写字幕或原始简介支持的事实。不要把临时路径、job 文件名、证据编号、采集状态写进主笔记。marker 仅用于草稿校验，正式 Obsidian 笔记发布时会自动移除。

5. 写完后立即 finalizer：

   ```powershell
   python "$project\hermes-skills\bilibili-learning\scripts\finalize_ytdlp_bilibili_note.py" --job '<job_dir>' --note '<draft_path>'
   ```

   即使写作失败，也必须运行 finalizer 清理 job。

6. 只在 finalizer 返回后回复：

   - `note_ready`：`已完成：《标题》\n笔记：<文件名>\n已写入 Obsidian。`
   - `note_invalid` / `failed`：只报告短错误，不能说已完成。

## 学习后整理

只有 owner 明确要求整理一篇已学习笔记时才执行；普通链接转笔记不进入此流程。先读取现有笔记，与 owner 的学习重点确认短标题和一句简介摘要，再调用统一入口：

```powershell
python "$project\hermes-skills\bilibili-learning\scripts\organize_bilibili_learning.py" --note '<现有笔记路径>' --title '<短标题>' --intro '<一句简介摘要>'
```

如 owner 未指定分类，省略 `--category`，由核心按 tags 放入 taxonomy 建议目录。禁止 Hermes 自行改名、移动文件或改写 UP 主资源链接；只以该命令的 `organized` 返回状态报告成功。

## Maintenance

本机可选运维文档可在仓库外单独维护；它不是项目运行前置条件，也不能覆盖仓库内的正式标准。
