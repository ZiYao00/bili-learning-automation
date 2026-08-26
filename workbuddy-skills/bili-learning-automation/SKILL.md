---
name: bili-learning-automation
description: Turn a Bilibili copied link, supported short link, or BV id into a subtitle-first Obsidian learning note without downloading media. Also use when the user asks to install, inspect, verify, initialize, or confirm readiness of this skill, or explicitly asks to organize already-learned notes.
---

# B站视频转笔记（WorkBuddy）

把本文件当作控制层；确定性状态、配置、发布、导航和清理由共享 Python 核心负责，写作细节以 runtime `handoff_path` 和对应 workflow 文档为准。不要为了处理正常状态去阅读核心源码。

## 入口

安装目录使用 `~/.workbuddy/skills/bili-learning-automation`，通常通过链接指向仓库适配层。不要硬编码用户仓库绝对路径。

```bash
runner="$HOME/.workbuddy/skills/bili-learning-automation/scripts/bridge.ps1"
```

`$runner` 不存在时停止并说明 Skill 安装无效。正常优先通过 `bridge.ps1` 调用；若 WorkBuddy 沙箱明确阻止 `powershell.exe`，解析已安装 Skill 链接目标得到仓库根，再用该仓库 `.venv/Scripts/python.exe` 调同目录 `bridge.py`，不要写死 `G:\...` 路径。若当前 shell 把 Windows 路径表示为 `/g/...` 一类 MSYS 路径，先转换为真实 Windows 路径再交给 `python.exe`，不要手工拼接盘符。

不得读取、展示或复述 Cookie 内容。

## 正常流程

1. **onboarding**

   生成笔记前，以及安装 / 检查 / 验证 / 初始化 / 可用性确认时，都先运行：

   ```bash
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" onboarding
   ```

   - `ready`：向用户简要展示返回的 `summary`（Python、yt-dlp、Cookie 是否就绪、Obsidian、CSS、workflow mode）。Cookie 只报告状态。生成笔记任务继续；仅验收任务到此结束。
   - `action_required`：停止采集，只按 `actions / warnings` 处理真正缺失项；只询问机器无法自动确定的输入。配置完成后重跑 onboarding。
   - CSS 警告不阻塞生成，也不得静默复制或覆盖用户 CSS。

2. **prepare**

   把用户当前消息原样交给 collector：

   ```bash
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" prepare '<用户消息原文>'
   ```

   - `materials_ready`：继续写作；若同时返回 `recovered: true`，表示核心已恢复此前完整的采集材料，不要重新调用 yt-dlp。
   - `onboarding_required`：按返回动作完成配置后重试原消息。
   - `in_progress`：说明仍有活动任务；不重复采集、不抢占，也不要手工处理 runtime 内部状态。
   - `subtitle_unavailable`：说明正常流程没有可用中文字幕且没有下载媒体；只有用户明确要求时才讨论项目级 ASR fallback。
   - 其它失败：报告短错误，不声称完成。

3. **写作**

   读取 `handoff_path`、`job.json`、`analysis_path` 与 `transcript_manifest_path`，按 manifest 顺序完整读取全部 transcript。以 handoff 指定的 `workflow_mode` 和文档为唯一流程说明，不在本 Skill 重复 light / strict 的内部步骤。

   只使用当前任务允许的来源支撑具体事实；来源不足时如实记录，不用模型常识补参数、资源或结论。程序负责 Frontmatter、H1、播放器、来源/资源区、tags、cssclasses、路径和 marker；WorkBuddy 只完成 handoff 指定的 AI 内容与质量复核。

4. **finalize**

   写完立即运行：

   ```bash
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" finalize --job '<job_dir>' --note '<draft_path>'
   ```

   无论写作成功或失败，都由 finalizer 处理 runtime 生命周期；不要手工删除中间文件或锁。`note_ready` 即表示业务完成；`publish_state = already_published` 表示此前发布已成功，本次是安全重试。`temporary_data_retired` / `cleanup_warning` 仅反映临时数据维护状态，不得把已成功发布的笔记改判为失败。

## 学习后整理

整理功能**默认关闭**，仅在用户明确要求时执行。指定一篇用 `single`，最近一篇用 `latest`，全部待整理笔记用 `all`；范围不明确再询问。先完整阅读目标笔记，并按 `docs/NOTE-ORGANIZATION.md` 判断短文件名与最多两层的目标目录。

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" organize --note '<现有笔记路径>' --filename '<新的简短文件名>' --destination '<领域/对象>' --confirmed-scope '<single|latest|all>'
```

Organizer 只负责重命名、移动和重建导航，**不得修改笔记内容**。

## 诊断

只有排查环境问题时才运行 `doctor --json`；正常生成流程不要额外加载安装教程或核心源码。
