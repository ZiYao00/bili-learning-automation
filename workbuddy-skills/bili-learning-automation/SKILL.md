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

- 如果用户尚未明确范围，先询问：**“要只整理最近一篇笔记，还是整理全部待整理笔记？”**，等待用户选择后再继续；
- 如果用户已经明确说“最近一篇”或“全部”，不要重复询问；
- 未得到 `latest` 或 `all` 的明确范围时，不得调用 `organize`，也不得先改名、移动文件或修改 tags。

范围确认后，逐篇完整阅读笔记，根据实际知识内容确定：

1. **短标题**：文件名 / H1 用于快速说明核心知识，删除视频式营销措辞；
2. **唯一主分类**：必须从 `config/bilibili-note-taxonomy.json` 的 `organization.categories` 中选择；视频生成优先按模型生态归类，真正跨模型、原理性、选型或对比内容才进入 `01-视频生成/90-进阶专题`；
3. **技术 Tags**：模型、工具、技术点和用途放入 tags；整理后移除 `待整理`；
4. **一句简介**：概括该笔记长期检索时最需要知道的内容。

然后调用：

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" organize --note '<现有笔记路径>' --title '<短标题>' --intro '<一句简介摘要>' --category '<taxonomy 目标目录>' --tag '<标签1>' --tag '<标签2>' --confirmed-scope '<latest|all>'
```

同一个模型可以有很多技术教程，不要因为“显存优化 / 首尾帧 / 数字人”等技术点继续建立多层目录；这些维度优先使用 tags。`Wan2.1`、`Wan2.2`、`SCAIL-2`、`Wan-Animate-2` 等统一进入 `01-视频生成/02-Wan系列`，具体版本和衍生模型通过标题与 tags 区分。

必须通过统一 organizer 完成改名、tags 更新、移动与导航重建；不得手工移动文件或改写 UP 主资源链接。Organizer 会在短标题旁保留原视频标题，不能删除该来源信息。

## 诊断

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" doctor --json
```

CSS 缺失属于可诊断警告，不得静默覆盖用户已有 CSS。
