---
name: bili-learning-automation
description: Turn a Bilibili copied link, supported short link, or BV id received in the owner's private conversation into an Obsidian note. Use the default subtitle-first route, an explicitly requested ASR fallback, or an explicitly requested description-only pure-resource short note. Also use to install, inspect, verify, initialize, confirm readiness, or organize existing notes only when the owner explicitly requests it.
---

# B站视频转笔记（Hermes）

只在 owner 私聊中执行；群聊或发送者范围不确定时先确认。把本文件当作控制层：状态、配置、来源采集、Job、发布、导航和清理由共享 Python 核心负责，写作细节以 runtime handoff 为准。过程与最终回复使用简体中文。

不得读取、展示或复述 Cookie 内容，也不要为了处理正常状态去阅读核心源码。

## 正常流程

1. **onboarding**

   生成笔记前，以及安装 / 检查 / 验证 / 初始化 / 可用性确认时，先运行：

   ```powershell
   python "$project\hermes-skills\bili-learning-automation\scripts\onboarding_bilibili_learning.py"
   ```

   - `ready`：简要展示返回的环境 `summary`；生成任务继续，仅验收任务结束。
   - `action_required`：停止采集，只处理 `actions / warnings` 中真正缺失的项目；配置后重跑。
   - CSS 警告不阻塞生成，也不得静默复制或覆盖用户 CSS。

2. **按当前消息的明确意图选择来源**

   不得根据标题、历史 memory 或模型猜测自动跳过字幕。

   - 默认“转换链接 / 转成笔记”：使用核心 `prepare` 的字幕优先入口。

     ```powershell
     python "$project\hermes-skills\bili-learning-automation\scripts\prepare_ytdlp_bilibili_note.py" '<received message text>'
     ```

   - owner 当前消息明确要求“纯资源分享 / 只整理简介 / 不用字幕 / 跳过字幕”：使用核心 `prepare-description` 的 description-only 入口，只采集 metadata 与 UP 主简介。

     ```powershell
     python "$project\hermes-skills\bili-learning-automation\scripts\prepare_description_bilibili_note.py" '<received message text>'
     ```

   - 默认入口返回 `subtitle_unavailable` 后，只有 owner 明确要求“ASR / 下载音频转文字 / 无字幕也继续”，才先运行项目 `scripts\bili_asr_fallback.py` 取得纯文本，再通过核心 `prepare-transcript` 回流标准 Job：

     ```powershell
     python "$project\hermes-skills\bili-learning-automation\scripts\prepare_transcript_bilibili_note.py" '<received message text>' --transcript '<transcript.txt>'
     ```

   三个入口共用同一 Job lifecycle。`materials_ready` 后继续写作；`recovered: true` 表示核心已恢复同一来源模式的完整 Job，不要重新采集。`onboarding_required` 按返回动作处理；`in_progress` 不抢占、不手工处理 runtime；其它失败只报告短错误。

   不得把纯文本伪造成 SRT、不得制造时间戳、手工创建 `job.json` / draft / source manifest，或直接修改已发布的正式笔记来绕过 finalizer。

3. **写作**

   读取 `handoff_path`、`job.json`、`analysis_path` 与 `source_manifest_path`，按 manifest 完整读取实际存在的 source chunk。以 handoff 指定的 `source_mode`、`workflow_mode` 和文档为唯一流程说明。

   只使用当前 Job 允许的来源支撑具体事实；来源不足时如实记录，不用模型常识补参数、资源或结论。程序负责 Frontmatter、H1、播放器、来源/资源区、tags、cssclasses、路径和 marker；Hermes 只完成 handoff 指定的 AI 内容与质量复核。

4. **finalize**

   ```powershell
   python "$project\hermes-skills\bili-learning-automation\scripts\finalize_ytdlp_bilibili_note.py" --job '<job_dir>' --note '<draft_path>'
   ```

   无论写作成功或失败，都由 finalizer 处理 runtime 生命周期；不要手工删除中间文件或锁。`note_ready` 即业务完成；`publish_state = already_published` 是安全重试。`temporary_data_retired` / `cleanup_warning` 不得覆盖已成功发布的结果。

## 学习后整理

整理功能默认关闭，仅在 owner 明确要求时执行。指定一篇用 `single`，最近一篇用 `latest`，全部待整理笔记用 `all`；范围不明确再询问。先完整阅读目标笔记，并按 `docs/NOTE-ORGANIZATION.md` 判断短文件名与最多两层的目标目录。

```powershell
python "$project\hermes-skills\bili-learning-automation\scripts\organize_bilibili_learning.py" --note '<现有笔记路径>' --filename '<新的简短文件名>' --destination '<领域/对象>' --confirmed-scope '<single|latest|all>'
```

Organizer 只负责重命名、移动和重建导航，不得修改笔记内容。
