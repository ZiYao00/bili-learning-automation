---
name: bili-learning-automation-hermes
description: 在 Hermes 的 owner 私聊中，把 Bilibili 复制链接、短链接或 BV 号通过用户指定的本机 bili-learning-automation 项目转换为 Obsidian 笔记。仅适用于可运行本机命令的受信任工作区；不要用于远程沙箱或未提供项目位置的场景。
---

# B站视频转笔记（Hermes 独立包）

这是独立安装的薄适配层，不包含 Python 核心、Cookie、Obsidian 笔记或本机配置。仅在 owner 私聊中执行；只在用户明确提供或已打开项目根目录后工作。不得扫描整块磁盘猜测项目位置，也不得读取、展示或复述 Cookie 内容。

## 连接本机项目

确认用户指定目录同时包含 `pyproject.toml`、`AGENTS.md`、`config/bilibili-note-taxonomy.json` 与 `scripts/run_bili_learning.py`。以下命令中的 `$project` 是该已验证的项目根目录：

```powershell
python "$project\scripts\run_bili_learning.py" onboarding
```

`ready` 才能继续；`action_required` 时只处理返回的缺失项。Skill 已安装不等于运行环境已就绪。

## 生成流程

根据当前消息的明确意图选择来源，始终保留触发请求的原始完整消息：

- 默认转换链接：`prepare '<原始消息>'`，使用字幕优先来源。
- 明确要求纯资源分享、只整理简介或跳过字幕：`prepare-description '<原始消息>'`。
- 仅在默认入口返回 `subtitle_unavailable` 后且 owner 明确授权时，先取得 ASR 纯文本，再用 `prepare-transcript '<原始消息>' --transcript '<文件>'`。

每个命令都通过：

```powershell
python "$project\scripts\run_bili_learning.py" <command> [args]
```

`existing_note_found` 时停止并让 owner 选择更新、重新执行或取消；不得猜更新目标或丢失原始消息。`materials_ready` 后读取 handoff、job、analysis 与 source manifest，按 manifest 完整读取当前 Job 允许的来源；只填写 AI 内容和质量复核，再运行 `finalize --job '<job>' --note '<draft>'`。不要手工创建 Job、伪造字幕/时间戳、修改正式笔记绕过 finalizer，或删除 runtime 锁、reservation、Job。

## 核查已发布笔记

owner 要求检查“刚生成 / 最近 / 指定标题或 BV”的笔记时，优先使用当前 Job 或 finalizer 返回的正式笔记路径；没有现成路径时，只在已配置的 Obsidian Vault 与 taxonomy `notes_root` 范围内按标题、BV 或最近修改时间定位。不得从磁盘根目录或无关项目目录开始扩大搜索；配置范围内仍找不到时，报告未命中并让 owner 提供路径。

## 学习后整理

整理默认关闭，只在 owner 明确要求且确认 `single`、`latest` 或 `all` 范围后执行。完整阅读笔记并按 `docs/NOTE-ORGANIZATION.md` 判断：知识型/混合型使用默认 `archive`，只改名、移动和刷新导航；纯资源型才先在 `<runtime_root>/resource-cards/` 写短资源卡，再使用 `organize --mode resource --collection '<集合页>' --card-file '<卡片>'`。核心会备份原独立笔记、合并到 `05-资源` 集合页并重建导航；不得手工移动或删除正式笔记。
