---
name: bili-learning-automation
description: Use in a supported local Agent host to turn a Bilibili copied link, supported short link, or BV id into an Obsidian learning note through the local bili-learning-automation project. Also use to verify, initialize, diagnose, update, or organize this workflow. Requires access to the local project and its shared launcher; do not use from a remote-only sandbox that cannot reach the project.
---

# B站视频转笔记

这是本项目唯一需要人工维护、也是 Codex / Hermes / WorkBuddy 共同通过目录链接安装的本地 Skill 真源。不要为本地宿主维护或生成第二套 `SKILL.md`；ChatGPT Web 的独立 ZIP 由 `scripts/build_chatgpt_skill.py` 从本目录渲染生成。

## 运行边界

1. 只通过当前宿主已经授权的本地工作区、命令执行或本机 bridge 操作项目；远程沙箱无法访问项目时停止。
2. 只有同时存在 `pyproject.toml`、`AGENTS.md`、`config/bilibili-note-taxonomy.json` 和 `scripts/run_bili_learning.py` 时才确认项目根目录。优先使用当前工作区或用户明确提供的路径，不扫描整块磁盘猜位置。
3. 确认项目后完整读取根目录 `AGENTS.md`。它与当前 Job 的 `agent_handoff.md` 是运行规则的事实来源；本 Skill 不复制评论策略、Cookie 细节、资源解析、taxonomy 或 finalizer 内部逻辑。
4. 默认通过项目共享启动器执行：

   ```powershell
   python <repo-root>\scripts\run_bili_learning.py <command> [args]
   ```

   Codex、Hermes、WorkBuddy 通过目录链接安装本 Skill。宿主需要清除注入的 `PYTHONPATH`、从 Junction 反查项目根目录或提供稳定 cleanup runner 时，可调用 `scripts/local_bridge.ps1` / `scripts/local_bridge.py`；bridge 只解决宿主路径与进程兼容，不得另写业务规则。
5. 不读取、展示、复述、上传或提交 Cookie 内容；不把 runtime、私人笔记或本机配置复制到远程沙箱。

## 1. 环境门禁

用户要求安装、检查、初始化、确认可用，或准备转换链接时，先运行：

```powershell
python <repo-root>\scripts\run_bili_learning.py onboarding
```

- `ready`：分别报告 Skill/项目访问与运行环境状态；仅验收任务到此结束，生成任务继续。
- `action_required`：停止采集，只处理返回的 `actions / warnings`，配置后重跑。
- `obsidian_notes_mapping_invalid`：hybrid 模式下 Vault 子目录没有正确映射到 `notes_root`；先修复 Junction，禁止继续采集。
- CSS 缺失是非阻塞警告，不静默复制或覆盖。
- 仅分析、解释或维护仓库源码时，不强制运行 onboarding。

## 2. 来源路由与重复笔记

保留触发任务的原始完整消息，只按当前消息的明确意图选路：

- 默认转换：`prepare '<原始完整消息>'`
- 明确要求纯资源、只整理简介或不用字幕：`prepare-description '<原始完整消息>'`
- 默认入口返回 `subtitle_unavailable` 后，只有用户明确授权 ASR，才先运行 `asr-health`；`ready` 时使用 `prepare-asr '<原始完整消息>'` 调用外部 `local-ASR-service`，服务不可用时停止并报告状态，不在本项目安装或启动另一套 ASR。
- 用户已经通过其它已授权工具取得真实纯文本时，仍可使用 `prepare-transcript '<原始完整消息>' --transcript '<文件>'` 直接接入标准 Job。

`prepare-asr` 仅在明确授权后临时下载音轨，转写结束即清理临时媒体；回流给 Job 的仍是真实纯文本，不得把纯文本伪造成 SRT，也不得制造时间戳。不要根据标题、历史记忆或模型猜测自动跳过字幕。

`existing_note_found` 时停止并让用户选择更新、重新执行或取消。重试必须继续使用原始完整消息；重新执行使用 `--on-existing rerun`，更新使用 `--on-existing update` 并在多篇候选时明确 `--update-target`。`update_conflict` 不得强制覆盖。

## 3. Job 写作

`materials_ready` 后读取返回的：

- `handoff_path`
- `job.json`
- `analysis_path`
- `source_manifest_path`
- manifest 中实际存在的全部来源文件

严格按 handoff 的 `source_mode` 与 `workflow_mode` 工作。

- 只编辑 handoff 授权的 runtime 文件、`analysis.json` 和草稿 AI 区域；
- 不修改程序生成的 Frontmatter、标题元信息、播放器、来源/资源区、路径或 marker；
- 只使用当前 Job 允许的来源支撑具体事实；来源不足时停止，不用模型常识补参数、资源或结论；
- 不手工创建、删除或修补 Job、reservation、锁或正式笔记来绕过 lifecycle；
- 所有正式笔记路径以 Settings / Job 返回的 `notes_root` 为准；推荐真实文件保存在项目内 Git-ignored `notes/bilibili`，Obsidian Vault 只通过 Junction 映射到它，不要反向链接项目目录到工作区外；
- 保留与当前任务无关的用户修改。

## 4. 发布

内容、排版与来源覆盖复核完成后运行：

```powershell
python <repo-root>\scripts\run_bili_learning.py finalize --job '<job_dir>' --note '<draft_path>'
```

只有 `note_ready` 才表示业务完成。`temporary_data_retired`、`temporary_data_removed` 或 `cleanup_warning` 只描述 runtime 维护状态，不得覆盖已经成功发布的结果。

## 5. 学习后整理

整理默认关闭。指定一篇用 `single`，最近一篇用 `latest`，全部待整理笔记用 `all`；只有用户明确要求并确认 `single / latest / all` 范围后，才完整读取 `docs/NOTE-ORGANIZATION.md` 并调用 `organize`。

知识型 / 混合型默认归档命令需要显式提供 `--filename`、`--destination` 与 `--confirmed-scope`；核心只负责安全重命名、移动和导航刷新，不得修改笔记内容。完整阅读目标笔记后再判断长期价值：

- 知识型 / 混合型：使用默认 `archive`，只改文件名和路径；
- 纯资源型：仅在整理阶段生成 runtime 资源卡，再使用 `--mode resource` 合并进 `05-资源` 集合页。

不要把类型判断提前到生成阶段，也不要手工移动、重命名或删除正式笔记。

## 回复要求

过程与最终回复使用简体中文。优先报告可验证的结构化状态；不要展示 Cookie 内容、内部锁信息或无必要的本机敏感路径。不要自动提交 Git，除非用户明确要求。
