---
name: bili-learning-automation-codex
description: Use in Codex to turn a Bilibili copied link, supported short link, or BV id into an Obsidian learning note from a local bili-learning-automation project. Also use to verify, initialize, diagnose, or organize this workflow. Do not use for unrelated Bilibili summaries when the project is not available.
---

# B站视频转笔记（Codex）

这是 Codex 的薄适配层。确定性采集、Job、写作契约、校验、发布、恢复和清理由当前 `bili-learning-automation` 项目负责，不在 Skill 内复制核心实现。

## 定位项目

1. 优先使用当前工作区。
2. 只有同时存在 `pyproject.toml`、`AGENTS.md`、`config/bilibili-note-taxonomy.json` 时，才确认当前目录是项目根目录。
3. 当前工作区不是该项目时，让用户提供或打开正确的项目目录；不要扫描整块磁盘猜路径。
4. 确认后完整读取根目录 `AGENTS.md`。它和当前 Job 的 handoff 是运行规则的事实来源。
5. 如果只是分析、解释或维护源码，按用户授权范围处理，不自动运行 onboarding 或生成笔记。

## 稳定命令入口

在项目根目录运行：

```powershell
python scripts/run_bili_learning.py <command> [args]
```

如果项目已有可用的 `.venv\Scripts\python.exe`，可优先使用它；否则使用 Python 3.10+。不要借用 Hermes 或 WorkBuddy 的兼容入口。

## 执行流程

### 1. 环境门禁

用户要求安装、检查、初始化、确认可用，或准备转换链接时，先运行：

```powershell
python scripts/run_bili_learning.py onboarding
```

- `ready`：分别报告 Skill 安装状态与运行环境状态；仅验收任务结束，生成任务继续。
- `action_required`：停止采集，只处理 `actions / warnings` 中真正缺失的项目，配置后重跑。
- CSS 缺失是非阻塞警告，不静默复制或覆盖。
- Cookie 只接收 Netscape 文件路径；不得读取、展示、复述或提交内容。

### 2. 来源路由

只根据当前消息的明确意图选择入口，并保存原始完整消息：

- 默认转换：`prepare '<原始完整消息>'`
- 明确要求纯资源、只整理简介或不用字幕：`prepare-description '<原始完整消息>'`
- 默认入口返回 `subtitle_unavailable` 后，只有用户明确授权 ASR，才取得纯文本并使用 `prepare-transcript '<原始完整消息>' --transcript '<文件>'`

示例：

```powershell
python scripts/run_bili_learning.py prepare '<原始完整消息>'
```

不要根据标题、旧笔记或历史记忆跳过字幕。`existing_note_found` 时停止并让用户选择更新、重新执行或取消；重试继续使用原始完整消息。多篇候选不得猜更新目标，`update_conflict` 不得强制覆盖。

### 3. Job 写作

`materials_ready` 后读取 `handoff_path`、`job.json`、`analysis_path`、`source_manifest_path` 和 manifest 列出的全部来源文件，并按 handoff 的 `source_mode` 与 `workflow_mode` 工作。

- 只编辑 handoff 授权的 runtime 文件、`analysis.json` 和草稿 AI 区域；
- 不改程序生成的 Frontmatter、标题元信息、来源区、路径或 marker；
- 来源不足时停止，不用模型常识补具体事实；
- 不手工删除 Job、reservation 或锁；
- 保留工作区内与当前任务无关的用户修改。

### 4. 发布与整理

完成内容、排版与来源覆盖复核后运行：

```powershell
python scripts/run_bili_learning.py finalize --job '<job_dir>' --note '<draft_path>'
```

只有 `note_ready` 才表示完成；runtime retire 或 cleanup warning 不改变已发布结果。

整理默认关闭。只有用户明确要求并确认 `single / latest / all` 范围后，才完整读取 `docs\NOTE-ORGANIZATION.md` 并调用 `organize`；完整阅读目标笔记后再判断长期价值：知识型/混合型使用默认 `archive`，只改文件名与路径；纯资源型才在整理阶段写 runtime 资源卡并使用 `--mode resource` 合并进 `05-资源` 集合页。不得把类型判断提前到生成阶段，也不得手工移动或重命名笔记。

## 回复要求

使用简体中文，先报告结果和结构化状态。不要展示 Cookie 内容、内部锁信息或无必要的本机敏感路径。不要自动提交 Git，除非用户明确要求。
