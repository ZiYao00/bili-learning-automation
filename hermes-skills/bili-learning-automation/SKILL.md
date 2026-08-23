---
name: bili-learning-automation
description: Turn a Bilibili copied link, supported Bilibili short link, or BV id received in the owner's private conversation into a subtitle-first Obsidian learning note without downloading media. No command prefix is required.
---

# B站视频转笔记

把 owner 私聊中的 B站复制链接、受支持的 Bilibili 短链接或 BV 号视为生成一篇学习笔记的请求。只在 owner 私聊中运行；群聊或发送者范围不确定时先确认。过程消息与最终回复使用简体中文，代码、路径、模型名和原始专有名词除外。

## Mandatory workflow

1. 原样把消息交给 collector：

   ```powershell
   $installedSkill = Get-Item "$env:LOCALAPPDATA\hermes\skills\bili-learning-automation"
   $skillSource = [string]$installedSkill.Target
   $project = Split-Path (Split-Path $skillSource -Parent) -Parent
   python "$project\hermes-skills\bili-learning-automation\scripts\prepare_ytdlp_bilibili_note.py" '<received message text>'
   ```

2. 按 JSON `status` 分支：

   - `configuration_required`：停止采集，向 owner 询问包含 `.obsidian` 的 Vault 根目录，再调用统一 `configure_bilibili_learning.py`；返回 `configured` 后重试原链接。不得自动扫描磁盘或自行选择 Vault。
   - `in_progress`：不重复采集。只有绑定 job 已明显陈旧、必需文件完整、草稿和 analysis 仍未写作时才续做；否则按活动任务处理，不抢占、不手工删锁。
   - `subtitle_unavailable`：说明没有可用中文字幕，且没有下载媒体，不生成笔记。
   - `failed` 且 `code = ytdlp_not_configured`：只提供 `winget install yt-dlp`，不自动安装或复制可执行文件。
   - 其它 `failed` / `note_invalid`：报告短错误，不声称完成。
   - 只有 `materials_ready`，或确认可安全续做的旧 job，才继续。

3. 读取 `handoff_path` 或 job 内的 `job.json`，确认 `workflow_mode`，再读取 `analysis_path` 与 `transcript_manifest_path`。按 manifest 顺序完整读取全部 transcript chunk，不主动重新切分或跳读。来源不足时在 `analysis.json` 记录原因，不得靠常识补具体事实。

4. 按模式写作：

   - **`light`（默认）**：读取 `docs\standards\LIGHT-WORKFLOW.md`。不要创建或执行 Fact Ledger、Semantic Draft、Layout Plan。直接完成 `draft_path` 的两个 AI 区域；先写完整内容，再独立做一次排版优化，最后回看 transcript 修正明显遗漏和无来源事实。
   - **`strict`**：读取 `docs\AGENT-INTEGRATION.md`、`docs\standards\CODEX-VIDEO-NOTE-GUIDE.md` 与 `docs\standards\KNOWLEDGE-DENSE-WORKFLOW.md`，按 `fact_ledger_path → semantic_draft_path → layout_plan_path → draft_path` 执行并完成阶段状态。

   两种模式都只能使用字幕或 UP 主简介支持的事实。Frontmatter、H1、播放器与来源区、资源、tags、cssclasses、路径和 marker 由程序负责，Hermes 不修改。Grid 内 Card 必须使用嵌套 `> > [!card]`。

5. 最终排版后回看 transcript，修正明显遗漏和无来源内容，再将 `coverage_review.status` 设为 `passed` 并填写简短 notes。严格模式还要对照 Fact Ledger 与 Semantic Draft。不要把 runtime 路径、工作文件名、Fact ID、analysis 文件或采集状态写进主笔记。

6. 立即运行 finalizer：

   ```powershell
   python "$project\hermes-skills\bili-learning-automation\scripts\finalize_ytdlp_bilibili_note.py" --job '<job_dir>' --note '<draft_path>'
   ```

   即使写作失败，也必须由 finalizer 清理 job；不得手工删除 job、reservation 或锁文件。

7. 只在 finalizer 返回后回复：

   - `note_ready` 且 `temporary_data_removed: true`：报告标题、文件名与已写入 Obsidian。
   - `source_insufficient`：说明现有字幕/简介不足，本次未发布正式笔记。
   - `note_invalid` / `failed` 或清理失败：只报告短错误，不能说已完成。

## 学习后整理

只有 owner 明确要求整理已学习笔记时，才调用统一 `organize_bilibili_learning.py`。不得自行改名、移动文件或改写 UP 主资源链接。
