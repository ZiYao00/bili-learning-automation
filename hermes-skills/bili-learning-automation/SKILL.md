---
name: bili-learning-automation
description: Turn a Bilibili copied link, supported short link, or BV id received in the owner's private conversation into a subtitle-first Obsidian learning note without downloading media. Also use to install, inspect, verify, initialize, or confirm readiness of this skill, and organize existing notes only when the owner explicitly requests it.
---

# B站视频转笔记（Hermes）

只在 owner 私聊中执行；群聊或发送者范围不确定时先确认。把本文件当作控制层：确定性状态、配置、发布、导航和清理由共享 Python 核心负责，写作细节以 runtime `handoff_path` 和对应 workflow 文档为准。过程与最终回复使用简体中文。

不得读取、展示或复述 Cookie 内容，也不要为了处理正常状态去阅读核心源码。

## 正常流程

1. **onboarding**

   生成笔记前，以及安装 / 检查 / 验证 / 初始化 / 可用性确认时，都先运行：

   ```powershell
   python "$project\hermes-skills\bili-learning-automation\scripts\onboarding_bilibili_learning.py"
   ```

   - `ready`：向 owner 简要展示返回的 `summary`（Python、yt-dlp、Cookie 是否就绪、Obsidian、CSS、workflow mode）。Cookie 只报告状态。生成任务继续；仅验收任务到此结束。
   - `action_required`：停止采集，只按 `actions / warnings` 处理真正缺失项；只询问机器无法自动确定的输入。配置后重跑 onboarding。
   - CSS 警告不阻塞生成，也不得静默复制或覆盖用户 CSS。

2. **prepare**

   解析已安装 Skill 链接得到 `$project`，把 owner 当前消息原样交给 collector：

   ```powershell
   python "$project\hermes-skills\bili-learning-automation\scripts\prepare_ytdlp_bilibili_note.py" '<received message text>'
   ```

   - `materials_ready`：继续写作；若同时返回 `recovered: true`，表示核心已恢复此前完整的采集材料，不要重新调用 yt-dlp。
   - `onboarding_required`：按返回动作完成配置后重试原消息。
   - `in_progress`：说明仍有活动任务；不重复采集、不抢占，也不要手工处理 runtime 内部状态。
   - `subtitle_unavailable`：说明正常流程没有可用中文字幕且没有下载媒体；只有 owner 明确要求时才讨论项目级 ASR fallback。
   - 其它失败：报告短错误，不声称完成。

3. **写作**

   读取 `handoff_path`、`job.json`、`analysis_path` 与 `transcript_manifest_path`，按 manifest 顺序完整读取全部 transcript。以 handoff 指定的 `workflow_mode` 和文档为唯一流程说明，不在本 Skill 重复 light / strict 的内部步骤。

   只使用当前任务允许的来源支撑具体事实；来源不足时如实记录，不用模型常识补参数、资源或结论。程序负责 Frontmatter、H1、播放器、来源/资源区、tags、cssclasses、路径和 marker；Hermes 只完成 handoff 指定的 AI 内容与质量复核。

4. **finalize**

   ```powershell
   python "$project\hermes-skills\bili-learning-automation\scripts\finalize_ytdlp_bilibili_note.py" --job '<job_dir>' --note '<draft_path>'
   ```

   无论写作成功或失败，都由 finalizer 处理 runtime 生命周期；不要手工删除中间文件或锁。`note_ready` 即表示业务完成；`publish_state = already_published` 表示此前发布已成功，本次是安全重试。`temporary_data_retired` / `cleanup_warning` 仅反映临时数据维护状态，不得把已成功发布的笔记改判为失败。

## 学习后整理

整理功能**默认关闭**，仅在 owner 明确要求时执行。指定一篇用 `single`，最近一篇用 `latest`，全部待整理笔记用 `all`；范围不明确再询问。先完整阅读目标笔记，并按 `docs/NOTE-ORGANIZATION.md` 判断短文件名与最多两层的目标目录。

```powershell
python "$project\hermes-skills\bili-learning-automation\scripts\organize_bilibili_learning.py" --note '<现有笔记路径>' --filename '<新的简短文件名>' --destination '<领域/对象>' --confirmed-scope '<single|latest|all>'
```

Organizer 只负责重命名、移动和重建导航，**不得修改笔记内容**。
