---
name: bili-learning-automation-chatgpt
description: Use in ChatGPT Work to turn a Bilibili copied link, supported short link, or BV id into an Obsidian learning note through a connected local-workspace bridge. Also use to verify, initialize, diagnose, or organize this local workflow. Do not use when ChatGPT has only its remote sandbox and cannot reach the cloned project.
---

# B站视频转笔记（ChatGPT）

这是 ChatGPT Work 的薄适配层。来源采集、Job、写作契约、校验、发布、恢复和清理由本机 `bili-learning-automation` 项目负责；不要在 ChatGPT 沙箱中复制或重建核心流程。

## 本地桥接门禁

本 Skill 必须通过已连接的本地工作区桥接工具操作项目。当前环境有 CodexPro 时优先使用它；等价工具必须同时支持打开工作区、读取/编辑文本文件和运行项目命令。

1. 优先使用已经打开的工作区；否则让用户提供项目根目录，再通过桥接打开。
2. 只在同时存在 `pyproject.toml`、`AGENTS.md`、`config/bilibili-note-taxonomy.json` 时确认项目身份。
3. 不扫描整块磁盘猜项目位置，不把维护者示例路径当成用户路径。
4. 桥接不可用或只有远程沙箱时停止，并明确区分：
   - Skill 已安装；
   - 本机项目尚不可访问。
5. 不把项目、Cookie、runtime 或私人笔记上传到 ChatGPT 沙箱。

确认项目后，完整读取根目录 `AGENTS.md`。它和当前 Job 的 handoff 是运行规则的事实来源；本文件只处理 ChatGPT 与本地桥接之间的入口差异。

## 稳定命令入口

所有项目命令都通过本地桥接、在项目根目录运行：

```powershell
python scripts/run_bili_learning.py <command> [args]
```

如果项目已有可用的 `.venv\Scripts\python.exe`，可优先使用它；否则使用本机 Python 3.10+。不要调用 Hermes 或 WorkBuddy 的适配脚本。

## 执行流程

### 1. 安装验收或生成前检查

用户要求安装、检查、初始化、确认可用，或准备转换链接时，先运行：

```powershell
python scripts/run_bili_learning.py onboarding
```

- `ready`：分别报告 Skill、桥接与运行环境状态；仅验收任务到此结束，生成任务继续。
- `action_required`：停止采集，只处理返回的 `actions / warnings`，配置后重跑。
- CSS 缺失是非阻塞警告，不静默复制或覆盖。
- Cookie 只接收 Netscape 文件路径；不得读取、展示、复述或上传内容。

仅分析、解释或维护仓库源码时，不强制运行 onboarding。

### 2. 按当前消息路由来源

保留触发任务的原始完整消息，不根据标题或历史记忆改变来源模式。

- 默认转换：`prepare '<原始完整消息>'`
- 当前消息明确要求纯资源、只整理简介或不用字幕：`prepare-description '<原始完整消息>'`
- 默认入口返回 `subtitle_unavailable` 后，只有用户明确授权 ASR，才取得纯文本并使用 `prepare-transcript '<原始完整消息>' --transcript '<文件>'`

命令统一使用共享启动器，例如：

```powershell
python scripts/run_bili_learning.py prepare '<原始完整消息>'
```

`existing_note_found` 时停止并让用户选择更新、重新执行或取消。重试必须继续使用原始完整消息；多篇候选不得猜更新目标，`update_conflict` 不得强制覆盖。

### 3. 写作与本机文件边界

`materials_ready` 后，通过桥接读取返回的 `handoff_path`、`job.json`、`analysis_path`、`source_manifest_path` 以及 manifest 列出的全部来源文件。严格按 handoff 的 `source_mode` 与 `workflow_mode` 工作。

所有读写继续留在本机项目与 Vault：

- 只编辑 handoff 授权的 runtime 文件、`analysis.json` 和草稿 AI 区域；
- 不改程序生成的 Frontmatter、标题元信息、来源区、路径或 marker；
- 来源不足时停止，不用模型常识补参数、资源或结论；
- 不手工删除 Job、reservation 或锁。

### 4. 发布与整理

写作、排版和来源覆盖复核完成后，通过共享启动器调用：

```powershell
python scripts/run_bili_learning.py finalize --job '<job_dir>' --note '<draft_path>'
```

只有 `note_ready` 才表示笔记已发布。维护 warning 不得覆盖成功状态。

学习后整理默认关闭；只有用户明确要求并确认范围后，才完整读取 `docs\NOTE-ORGANIZATION.md` 并调用 `organize`。完整阅读目标笔记后再判断长期价值：知识型/混合型使用默认 `archive`，只改文件名和路径；纯资源型才在整理阶段写 runtime 资源卡并使用 `--mode resource` 合并进 `05-资源` 集合页。不要把类型判断提前到生成阶段，也不要把转换与整理合并成一步。

## 回复要求

过程与最终回复使用简体中文。优先报告可验证的结构化状态；不要展示 Cookie 内容、内部锁信息或无必要的本机敏感路径。
