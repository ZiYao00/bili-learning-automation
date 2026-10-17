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
   & '<repo-root>\scripts\run_bili_learning.ps1' <command> [args]
   ```

   Codex、Hermes、WorkBuddy 通过目录链接安装本 Skill。宿主需要清除注入的 `PYTHONPATH`、从 Junction 反查项目根目录或提供稳定 cleanup runner 时，可调用 `scripts/local_bridge.ps1` / `scripts/local_bridge.py`；bridge 只解决宿主路径与进程兼容，不得另写业务规则。
5. 不读取、展示、复述、上传或提交 Cookie 内容；不把 runtime、私人笔记或本机配置复制到远程沙箱。

## 1. 环境门禁

用户要求安装、检查、初始化、确认可用，或准备转换链接时，先运行：

```powershell
& '<repo-root>\scripts\run_bili_learning.ps1' onboarding
```

- `ready`：分别报告 Skill/项目访问与运行环境状态；仅验收任务到此结束，生成任务继续。
- `action_required`：停止采集，只处理返回的 `actions / warnings`，配置后重跑。
- `obsidian_notes_mapping_invalid`：hybrid 模式下 Vault 子目录没有正确映射到 `notes_root`；先修复 Junction，禁止继续采集。
- CSS 缺失是非阻塞警告，不静默复制或覆盖。
- 仅分析、解释或维护仓库源码时，不强制运行 onboarding。

### 安装任务：由 Agent 执行，不要求用户手工安装

安装前按项目 `docs/QUICKSTART.md` 与 `docs/LOCAL-AGENT-INSTALL.md` 操作。先运行 `scripts/run_bili_learning.ps1 -ProbeOnly` 验证 Python，只有 `ready` 才进入 onboarding。Python 不随仓库打包；如缺失，由 Agent 在得到用户明确授权后准备官方 Python 3.12，不能要求用户手动安装或自动触发商店安装。可临时指定 `BILI_LEARNING_PYTHON` 使用外部可信解释器，必须验证版本。只使用项目内 `tools/yt-dlp.exe`，不得搜索系统 PATH、读取旧 `ytdlp` 配置作为可执行路径或安装源码/winget。Codex/Hermes/WorkBuddy 用户级 Skill 链接使用 `scripts/install_agent_skill.ps1`：默认只读计划，取得外部目录写入许可后才 `-Apply`；Obsidian Vault → 项目 notes 使用 `scripts/ensure_junction.ps1` 同样先计划再按授权应用。遇到已有目录、旧副本或不同目标的 Junction 返回 `conflict` 时停止，不自动删除/搬迁。首次 `configure-obsidian` 建立 Hybrid 配置，不迁移旧 direct-vault。ChatGPT Web 单独构建 ZIP 并需要有效本地桥接。`local-ASR-service` 是独立可选项目，不属于默认安装任务。

## 2. 来源路由与重复笔记

保留触发任务的原始完整消息，只按当前消息的明确意图选路：

- 默认转换：`prepare '<原始完整消息>'`
- 明确要求纯资源、只整理简介或不用字幕：`prepare-description '<原始完整消息>'`
- 默认入口返回 `subtitle_unavailable` 后，只有用户明确授权 ASR，才先运行 `asr-health`；`ready` 时使用 `prepare-asr '<原始完整消息>'` 调用外部 `local-ASR-service`，服务不可用时停止并报告状态，不在本项目安装或启动另一套 ASR。
- 用户已经通过其它已授权工具取得真实纯文本时，仍可使用 `prepare-transcript '<原始完整消息>' --transcript '<文件>'` 直接接入标准 Job。

`prepare-asr` 先在下载和转录前检查重复 BVID、更新目标和现有任务 reservation，再在明确授权后临时下载音轨、流式上传本地 ASR，完成后清理临时媒体。`in_progress` 或 `existing_note_found` 不得绕过、不得重复转录；`asr_outcome_unknown` 表示服务端结果不确定，须检查共享 ASR 的 Queue / 日志，不得自动重发 POST。回流给 Job 的仍是真实纯文本，不得把纯文本伪造成 SRT，也不得制造时间戳。不要根据标题、历史记忆或模型猜测自动跳过字幕。

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

整理默认关闭。指定一篇用 `single`，最近一篇用 `latest`，全部待整理笔记用 `all`；只有用户明确要求并确认范围后，才完整读取 `docs/NOTE-ORGANIZATION.md`。普通整理只归档完整笔记，**不得修改笔记内容**，也不修改标题、原文件名、正文、元信息、Frontmatter、资源链接或排版。

- 单篇：`organize --note <现有笔记> --destination <领域/对象> --confirmed-scope single`；默认保留文件名并校验 SHA-256。`--filename` 仅为旧版显式改名兼容，普通整理不要使用。
- 批量：先 `organize-list --scope all` 获取清单；Agent 完整阅读每篇，按知识主题判断目标目录，在 `runtime/organize-plans` 写带源文件相对路径、目标目录、原 SHA-256 的 JSON。先 `organize-batch --plan <路径> --confirmed-scope all` 预览；已授权后添加 `--apply` 执行。重复、哈希冲突、目标同名、目录逃逸、潜在断链均跳过并报告。中断后保留同计划及检查点重试。
- 重复版本：`organize-duplicates --bvid <BV号>` 仅查询；只有用户明确指明保留对象及待回收文件并授权后，才可使用 `organize-duplicates --plan <路径> --apply`，必须移入 Windows 回收站且不得永久删除。
- 原有纯资源 `--mode resource` 有损压缩仍可独立使用，但**不是普通整理的自动分支**；只有用户另行明确授权才执行，原文件同样使用回收站，不可用时停止。

不要把类型判断提前到生成阶段，也不要手工移动、重命名或删除正式笔记。

## 回复要求

过程与最终回复使用简体中文。优先报告可验证的结构化状态；不要展示 Cookie 内容、内部锁信息或无必要的本机敏感路径。不要自动提交 Git，除非用户明确要求。
