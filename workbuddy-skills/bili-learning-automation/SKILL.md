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

仅当用户在当前会话中主动提供 B站链接 / BV 号并明确要转笔记，或明确要求整理已学习笔记时执行。链接用途不明确时先确认；除非用户明确要求，不批量转换链接列表。

## 环境与路径

- 安装目录按 WorkBuddy 约定使用 `~/.workbuddy/skills/bili-learning-automation`，推荐通过 Junction 指向仓库中的适配层。
- 不硬编码仓库绝对路径；使用 `scripts/bridge.ps1` 与 `bridge.py` 定位并调用共享核心。
- yt-dlp、Cookie、Obsidian Vault 和工作模式来自项目配置或受支持环境变量。不得读取、展示或复述 Cookie 内容。

```bash
runner="$HOME/.workbuddy/skills/bili-learning-automation/scripts/bridge.ps1"
```

`$runner` 不存在时停止并说明安装无效，不猜测仓库路径。

## 必须执行的流程

1. 原样把用户消息交给 collector：

   ```bash
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" prepare '<用户消息原文>'
   ```

2. 按 JSON `status` 分支：

   - `configuration_required`：停止采集，询问包含 `.obsidian` 的 Vault 根目录，再调用 `configure-obsidian`。返回 `configured` 后重试原链接；不得自动扫描磁盘或自行选择 Vault。
   - `in_progress`：已有活动任务，不重复采集或抢占。
   - `subtitle_unavailable`：没有可用中文字幕，且没有下载媒体，不生成笔记。若用户已人工确认视频确实无字幕并明确要求应急转录，只说明可使用项目级 `scripts/bili_asr_fallback.py`；不得在当前 prepare job 内自动调用旁路或把旁路结果伪装成正常 Skill 流程。
   - `failed` 且 `code = ytdlp_not_configured`：只提供 `winget install yt-dlp`，不自动安装或复制可执行文件。
   - 其它 `failed` / `note_invalid`：报告短错误，不声称完成。
   - 只有 `materials_ready` 才继续。

3. 读取 `handoff_path`、`job.json`、`analysis_path` 与 `transcript_manifest_path`，确认 `workflow_mode`。按 manifest 顺序完整读取全部 transcript chunk，不自行重新切分或跳读。来源不足时在 `analysis.json` 记录原因，不得靠常识补具体事实。

4. 按模式写作：

   - **`light`（默认）**：读取 `docs\standards\LIGHT-WORKFLOW.md`。不要创建或执行 Fact Ledger、Semantic Draft、Layout Plan。直接完成 `draft_path` 的两个 AI 区域；先写完整内容，再独立做一次排版优化，最后回看 transcript 修正明显遗漏和无来源事实。
   - **`strict`**：读取 `docs\AGENT-INTEGRATION.md`、`docs\standards\CODEX-VIDEO-NOTE-GUIDE.md` 与 `docs\standards\KNOWLEDGE-DENSE-WORKFLOW.md`，按 `fact_ledger_path → semantic_draft_path → layout_plan_path → draft_path` 执行并完成阶段状态。

   两种模式都只能使用字幕或 UP 主简介支持的事实。Frontmatter、H1、播放器与来源区、资源、tags、cssclasses、路径和 marker 由程序负责，WorkBuddy 不修改。Grid 内 Card 必须使用嵌套 `> > [!card]`。

5. 最终排版后回看 transcript，修正明显遗漏和无来源内容，再将 `coverage_review.status` 设为 `passed` 并填写简短 notes。严格模式还要对照 Fact Ledger 与 Semantic Draft。不要把 runtime 路径、工作文件名、Fact ID、analysis 文件或采集状态写进主笔记。

6. 立即运行 finalizer：

   ```bash
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" finalize --job '<job_dir>' --note '<draft_path>'
   ```

   即使写作失败，也必须由 finalizer 清理 job；不得手工删除 job、reservation 或锁文件。

7. 只在 finalizer 返回后回复：

   - `note_ready` 且 `temporary_data_removed: true`：报告标题、文件名与已写入 Obsidian。
   - `source_insufficient`：说明现有字幕/简介不足，本次未发布正式笔记。
   - `note_invalid` / `failed` 或清理失败：只报告短错误，不能说已完成。

## 学习后整理

学习后整理**默认关闭**，只有用户明确要求整理 / 归档时才执行。先确认范围：指定一篇用 `single`，最近一篇用 `latest`，全部待整理笔记用 `all`；范围不明确时再询问。

整理时逐篇完整阅读，只决定**短文件名**和**目标目录**。目标是让以后在 Obsidian 中一眼看懂、容易找到，而不是套固定分类模板。通常使用“领域 / 对象”，最多两层；具体判断参考项目 `docs/NOTE-ORGANIZATION.md` 中的真实案例，并保留模型自行判断空间。

归档阶段不得修改笔记内容，包括 H1、Summary、正文、Frontmatter、Tags、视频简介、UP 主资源和测试标记。

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" organize --note '<现有笔记路径>' --filename '<新的简短文件名>' --destination '<领域/对象>' --confirmed-scope '<single|latest|all>'
```

统一 Organizer 只负责改文件名、移动文件和重建导航；内容修改或旧格式升级应作为独立任务处理。

## 诊断

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" doctor --json
```

CSS 缺失属于可诊断警告，不得静默覆盖用户已有 CSS。
