---
name: bili-learning-automation
description: Turn a Bilibili copied link, supported short link, or BV id into an Obsidian note. Use the default subtitle-first route, an explicitly requested ASR fallback, or an explicitly requested description-only pure-resource short note. Also use to install, inspect, verify, initialize, confirm readiness, or organize existing notes only when the user explicitly requests it.
---

# B站视频转笔记（WorkBuddy）

把本文件当作控制层；状态、配置、来源采集、Job、发布、导航和清理由共享 Python 核心负责，写作细节以 runtime handoff 为准。不要为了处理正常状态去阅读核心源码，也不得读取、展示或复述 Cookie 内容。

## 入口

安装目录使用 `~/.workbuddy/skills/bili-learning-automation`，通常通过链接指向仓库适配层：

```bash
runner="$HOME/.workbuddy/skills/bili-learning-automation/scripts/bridge.ps1"
```

`$runner` 不存在时停止并说明 Skill 安装无效。正常优先通过 `bridge.ps1`；若沙箱明确阻止 PowerShell，解析安装链接后使用仓库 `.venv/Scripts/python.exe` 调同目录 `bridge.py`，不要写死本机项目路径。

## 正常流程

1. **onboarding**

   ```bash
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" onboarding
   ```

   - `ready`：简要展示环境 `summary`；生成任务继续，仅验收任务结束。
   - `action_required`：停止采集，只处理 `actions / warnings` 中真正缺失的项目；配置后重跑。
   - CSS 警告不阻塞生成，也不得静默复制或覆盖用户 CSS。

2. **按当前消息的明确意图选择来源**

   不得根据标题、历史记忆或模型猜测自动跳过字幕。

   - 默认“转换链接 / 转成笔记”：

     ```bash
     powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" prepare '<用户消息原文>'
     ```

   - 当前消息明确要求“纯资源分享 / 只整理简介 / 不用字幕 / 跳过字幕”：

     ```bash
     powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" prepare-description '<用户消息原文>'
     ```

   - 默认入口返回 `subtitle_unavailable` 后，只有用户明确要求“ASR / 下载音频转文字 / 无字幕也继续”，才先运行项目 `scripts\bili_asr_fallback.py` 取得纯文本，再回流：

     ```bash
     powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" prepare-transcript '<用户消息原文>' --transcript '<transcript.txt>'
     ```

   三个入口共用同一 Job lifecycle。`materials_ready` 后继续写作；`recovered: true` 表示核心已恢复同一来源模式的完整 Job，不要重新采集。`onboarding_required` 按返回动作处理；`in_progress` 不抢占、不手工处理 runtime。

   如果返回 `existing_note_found`，停止采集并列出现有笔记，询问用户：**更新已有笔记 / 重新执行一次 / 取消**。只有一篇时“更新”可直接使用该目标；多篇时必须让用户指定具体笔记。选择后，用触发重复提示的**原始完整消息**重试同一来源入口：重新执行追加 `--on-existing rerun`；更新追加 `--on-existing update --update-target '<现有笔记路径>'`；取消则不再调用核心。不要只把后续回复“更新/重跑”当成新的输入消息，否则会丢失用户原先附带的资源和说明。`update_conflict` 必须报告冲突，不得强制覆盖。

   不得把纯文本伪造成 SRT、不得制造时间戳、手工创建 `job.json` / draft / source manifest，或直接修改已发布的正式笔记来绕过 finalizer。

3. **写作**

   读取 `handoff_path`、`job.json`、`analysis_path` 与 `source_manifest_path`，按 manifest 完整读取实际存在的 source chunk。以 handoff 指定的 `source_mode`、`workflow_mode` 和文档为唯一流程说明。

   只使用当前 Job 允许的来源支撑具体事实；来源不足时如实记录，不用模型常识补参数、资源或结论。程序负责确定性结构；WorkBuddy 只完成 AI 内容与质量复核。

4. **finalize**

   ```bash
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" finalize --job '<job_dir>' --note '<draft_path>'
   ```

   无论写作成功或失败，都由 finalizer 处理 runtime 生命周期；不要手工删除中间文件或锁。`note_ready` 即业务完成；`publish_state = already_published` 是安全重试。维护 warning 不得覆盖已成功发布的结果。

## 学习后整理

整理功能默认关闭，仅在用户明确要求时执行。指定一篇用 `single`，最近一篇用 `latest`，全部待整理笔记用 `all`；范围不明确再询问。先完整阅读目标笔记，并按 `docs/NOTE-ORGANIZATION.md` 判断短文件名与最多两层的目标目录。

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" organize --note '<现有笔记路径>' --filename '<新的简短文件名>' --destination '<领域/对象>' --confirmed-scope '<single|latest|all>'
```

Organizer 只负责重命名、移动和重建导航，不得修改笔记内容。

## 诊断

只有排查环境问题时才运行 `doctor --json`；正常生成流程不要额外加载安装教程或核心源码。
