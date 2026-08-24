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

学习后整理**默认关闭**。生成新笔记、finalizer 完成、检测到 `00-待整理` 有文件，均不得自动触发整理。

只有用户明确提出“整理 / 归档笔记”时才进入整理流程。执行前必须先确定范围：

- 用户已经明确指定某一篇笔记时，直接使用 `single`，不要把它映射成 `latest`；
- 用户明确说“最近一篇”时使用 `latest`，Organizer 会验证指定文件确实是当前最近一篇；
- 用户明确说“全部”时使用 `all`；
- 只有用户提出整理但没有任何可判定范围时，才询问：**“要整理指定的一篇、最近一篇，还是全部待整理笔记？”**；
- 未得到 `single`、`latest` 或 `all` 的明确范围时，不得调用 `organize`，也不得先改名、移动文件或修改 tags。

范围确认后，逐篇完整阅读笔记，但**只决定文件名和目标目录**：

1. **文件名**：短、直接，让人一眼知道这篇笔记是什么；可按需要使用 `百科：`、`教程：`、`工作流：`、`实测：`、`对比：` 等前缀；不要把摘要或章节列表塞进文件名。
2. **目标目录**：优先采用“领域 / 对象”，最多两层，例如 `02-图像/Krea2`、`01-视频/MiniMax-H3`。有明确模型/工具时按对象聚合；没有稳定对象时才用主题作为第二层。

归档阶段不得修改笔记内容。H1、Summary、正文、Frontmatter、Tags、视频简介、UP 主资源以及 `(workbuddy)` / `(GPT)` 等测试标记全部保持原样。

然后调用：

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" organize --note '<现有笔记路径>' --filename '<新的简短文件名>' --destination '<领域/对象>' --confirmed-scope '<single|latest|all>'
```

必须通过统一 organizer 完成改文件名、移动和导航重建。Organizer 不负责改 H1、简介或 Tags，也不顺手升级旧笔记格式。需要内容修改时必须作为独立任务处理。

## 诊断

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" doctor --json
```

CSS 缺失属于可诊断警告，不得静默覆盖用户已有 CSS。
