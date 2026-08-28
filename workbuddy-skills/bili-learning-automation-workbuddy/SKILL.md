---
name: bili-learning-automation-workbuddy
description: 在 WorkBuddy 中把用户主动提供的 Bilibili 复制链接、短链接或 BV 号通过用户指定的本机 bili-learning-automation 项目转换为 Obsidian 笔记。仅适用于可运行本机命令的受信任工作区；不要用于远程沙箱或未提供项目位置的场景。
---

# B站视频转笔记（WorkBuddy 独立包）

这是独立安装的薄适配层，不包含 Python 核心、Cookie、Obsidian 笔记或本机配置。只处理用户在当前会话明确提供的链接或 BV 号；项目位置不明确时让用户打开或提供本机项目根目录，不能扫描所有磁盘猜测位置。不得读取、展示或复述 Cookie 内容。

## 连接本机项目

确认用户指定目录同时包含 `pyproject.toml`、`AGENTS.md`、`config/bilibili-note-taxonomy.json` 与 `scripts/run_bili_learning.py`。以下命令中的 `$project` 是该已验证的项目根目录：

```powershell
python "$project\scripts\run_bili_learning.py" onboarding
```

只有 `ready` 表示可以继续；`action_required` 时只处理返回的真实缺失项。Skill 已安装不等于运行环境已就绪。

## 生成流程

根据当前消息明确意图选路并保留原始完整消息：默认用 `prepare '<原始消息>'`；明确要求纯资源分享、只整理简介或跳过字幕时用 `prepare-description '<原始消息>'`；只有默认入口返回 `subtitle_unavailable` 且用户明确授权 ASR 后，才用 `prepare-transcript '<原始消息>' --transcript '<文件>'`。

统一命令：

```powershell
python "$project\scripts\run_bili_learning.py" <command> [args]
```

`existing_note_found` 时暂停并让用户选择更新、重新执行或取消；多篇笔记不得猜更新目标。`materials_ready` 后读取 handoff、job、analysis 与 source manifest，完整读取 manifest 中当前 Job 允许的来源，只填写 AI 内容和质量复核，最后运行 `finalize --job '<job>' --note '<draft>'`。不得伪造 SRT/时间戳、手工组装 Job、直接改正式笔记绕过 finalizer，或删除 runtime 锁、reservation、Job。

## 学习后整理

整理默认关闭，只在用户明确要求且确认 `single`、`latest` 或 `all` 范围后进行。完整阅读目标笔记：知识型/混合型使用默认 `archive`，只改名、移动和刷新导航；纯资源型才在 `<runtime_root>/resource-cards/` 写短资源卡，再使用 `organize --mode resource --collection '<集合页>' --card-file '<卡片>'`。核心会备份原独立笔记、合并资源卡到 `05-资源` 集合页并重建导航；不得手工移动或删除正式笔记。
