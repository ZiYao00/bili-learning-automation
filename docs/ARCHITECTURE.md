# 架构说明

## 主链路

```text
已授权智能体入口中的复制链接 / BV 号 / 受支持短链
→ input_resolver 规范化 BVID 与 canonical URL
→ 适配层只根据当前消息的明确意图选择 source_mode：默认 `subtitle_srt`；明确授权 ASR 后使用 `asr_text`；明确“纯资源分享 / 只整理简介 / 不用字幕”使用 `description_only`
→ `prepare` / `prepare-transcript` / `prepare-description` 先按 BVID 检查已发布笔记；可选 `prepare-asr` 同样先查重、取得长转录保护的 BVID reservation 再下载音轨、分块请求 ASR；默认重复返回 `existing_note_found`，用户明确选择 rerun / update 后才继续 `_prepare_materials`
→ rerun 继续创建独立新笔记并使用递增序号；update 绑定既有路径、保存旧笔记快照与 SHA-256，再由 SourceMaterial + source manifest 生成标准 Job
→ taxonomy 生成 tags 与后续整理建议；原视频标题的新笔记进入 00-待整理
→ Python 在 runtime 写入确定性 Markdown 草稿、analysis.json 与统一 source package
→ workflow_mode 路由：light 直接写作；strict 额外创建三份阶段工作文件
→ 接入智能体（Codex / Hermes / WorkBuddy）判断来源充分性
→ light 直接完成正文；strict 依次完成 Fact Ledger / Semantic Draft / Layout Pass
→ 两种模式都在内容完成后独立做一次版式优化
→ 智能体回看当前 Job 允许的来源完成 coverage review
→ finalizer 校验质量流程状态、真实元数据与结构后原子发布
→ navigation 原子刷新
→ runtime Job 退出活动区并 retire；物理清理不属于业务成功前提
```

## 代码分层

- `tools/yt-dlp.exe`：唯一固定执行的官方 Windows x64 单文件 yt-dlp；不搜索系统其它安装，也不内置于 ChatGPT Skill ZIP；版本、哈希和许可证随项目维护。
- `scripts/python_runtime.ps1` 与 `scripts/run_bili_learning.ps1`：Windows Agent 的只读 Python 预检与统一 CLI 入口；无内置 Python 运行时。canonical `local_bridge.ps1` 使用相同解析器，防止不同宿主选择不同解释器。
- `scripts/install_agent_skill.ps1` 和 `scripts/ensure_junction.ps1`：Agent 安装的只读计划/受控应用层；不包含笔记业务逻辑，不能覆盖目标目录。
- `src/bili_learning/`：可测试的核心逻辑和 agent-neutral CLI。`prepare`、`prepare-transcript`、`prepare-description` 只是清晰的外部入口，内部共用 `_prepare_materials`；`source.py` 定义三种 Source Mode，`transcript.py` 生成统一 source manifest；`pinned_comment.py` 负责条件触发/白名单置顶一级评论补充；`workflow.py` 只为 `strict` 模式创建并校验三份 runtime 工作文件。
- `skill/bili-learning-automation/`：唯一需要人工维护的 canonical 本地 Skill；Codex、Hermes、WorkBuddy 的用户级 Skill 目录直接 Junction 到这里。`scripts/local_bridge.py` / `.ps1` 只处理宿主路径、Python 与 `PYTHONPATH` 兼容，不复制业务规则。
- `scripts/build_chatgpt_skill.py`：从 canonical Skill 与批准的公开文档直接渲染唯一的 ChatGPT Web ZIP，并通过 `--check` 验证 package render；不生成本地 Agent 副本。
- `docs/AGENT-INTEGRATION.md`：所有智能体共用的接入协议。
- 本地 Agent 安装目录存在于用户环境而不是仓库；仓库不再维护宿主专用 Skill 副本。
- ChatGPT Web 通过专用 ZIP + 本地工作区桥接进入同一个项目核心；ZIP 不包含 Python core、Cookie、runtime、私人笔记或本机配置。
- `config/bilibili-note-taxonomy.json`：模型别名、tags、后续整理建议和默认 `notes_root`。
- `docs/standards/`：人类可读的笔记质量与版式语义标准。
- `config/obsidian-style.json`：共享 CSS 依赖契约，声明本项目需要的 `learning-lab.css` Core、`video-note.css` Extension 与 Frontmatter class。
- `docs/OBSIDIAN-STYLING.md`：共享 CSS 安装、作用域、同步和无样式降级规则。CSS 唯一真源是 `obsidian-learning-snippets` 仓库，运行时从 Vault 加载。

## 确定性边界

程序负责：

- canonical URL；
- H1 下方的“作者 · 发布日期 · 时长 · BVID”元信息行；
- Frontmatter；
- H1；
- 原始简介；
- iframe；
- tags；
- `learning-page + video-note` cssclasses；
- 阅读顺序（Summary → Player / Source → AI Body）；
- 输出路径；
- `source_mode`、source manifest、来源采集与模式一致的 Job recovery；
- `workflow_mode` 路由；`strict` 模式下额外生成 Fact Ledger / Semantic Draft / Layout Plan 脚手架及其路径；
- 导航。

taxonomy 的 route.path 不直接决定新文件的路径。新笔记统一先进入 fallback.path（默认 `00-待整理`）；route.path 仅随 job 保留为建议分类，并通过 tags 帮助 `organize` 在学习后归档。收集阶段 H1 直接使用原视频标题，不进行主题提炼。

接入智能体只负责当前 Job 允许来源的理解与语义内容：

- 判断 `subtitle_srt`、`asr_text` 或 `description_only` 当前允许的来源是否足以支撑可信笔记；description-only 不得推断视频口播或画面事实；
- `light` 模式按 source manifest 完整读取实际存在的 source chunks 后直接写作；description-only 没有伪造 chunk，只读取 Job 中的标题、metadata、简介和用户补充来源；
- `strict` 模式按 Fact Ledger → Semantic Draft → Layout Plan 执行；
- 两种模式都先把内容写完整，再独立做一次版式优化；
- 写短的“先看结论”；
- 根据视频真实信息结构组织动态知识正文；
- 最终排版后重新回到当前 Job 允许的来源完成覆盖复核；严格模式额外对照三份阶段工作文件。

章节、表格和步骤形式由内容决定；确定性骨架仍由程序控制，避免 LLM 重写元数据、简介或路径。

## 数据边界

- 长期产物：私人 Markdown 笔记与导航页，默认不入 Git。
- runtime 产物：`.runtime/bilibili-learning` 的活动 Job 始终包含 source manifest、analysis 与草稿；subtitle / ASR 还包含 source chunks，ASR 会保存 runtime 内纯文本副本，description-only 不伪造独立 source 文件或 chunk。`strict` 模式额外包含 Fact Ledger、Semantic Draft 与 Layout Plan。任务完成后 Job retire 到 `retired/`。
- 敏感数据：`key/` 中的 Cookie 文件和被 Git 忽略的 `config/pinned-comment-whitelist.local.json`。正常字幕/简介采集仍把文件路径交给 yt-dlp；仅当用户主动配置的本地置顶评论白名单命中时，`pinned_comment.py` 才会在本机读取 Netscape Cookie 并构造一次只读评论请求。Cookie 值不得打印、写入 Job/笔记、上传或提交。
- 已退役的 Chrome/CDP、本机历史采集材料与第三方副本不再保留在工作区；历史背景通过 Git / CHANGELOG 追溯。

## 配置边界

正式用户推荐显式配置 `notes_root + vault_root + notes_subdir`：`notes_root` 是真实 Markdown 写入真源，推荐位于 `<repo-root>/notes/bilibili` 并保持 Git ignored；`vault_root + notes_subdir` 只描述 Obsidian 映射位置，Windows 上应由 Vault 子目录 Junction 指向 `notes_root`。统一 settings loader 同时保留 direct-vault 和 notes-root-only 兼容模式；hybrid 模式由 doctor/onboarding 校验 `obsidian_notes_mapping`。taxonomy 的 `notes/bilibili` 仍只作为未配置时的 repository fallback；collector、finalizer、navigation 与 doctor 共用同一 settings loader。

## 可靠性原则

- 默认重复 BVID 不直接执行；先返回 `existing_note_found` 由用户选择。明确 rerun 时，文件名使用原视频标题并在 `note-names.lock` 保护下递增 `（2）/（3）`；明确 update 时保留原路径和文件名，finalizer 只在目标 SHA-256 仍与 Job 启动时一致时原子替换，否则返回 `update_conflict`。
- 同一 BVID 仅在活动 collector、智能体写作与 finalizer 期间使用 reservation 防止并发；reservation 使用 `active / released` 状态文件，并由 OS 文件锁保护 claim / bind / release 的原子性。任务完成后切换为 `released`，允许再次转换。
- 如果 reservation 持有进程已经结束，而绑定 Job 的 `job.json`、草稿、`analysis.json`、source manifest 及该模式必需的 source 文件 / chunks 仍完整，核心只在请求的 `source_mode` 与旧 Job 一致时恢复并返回 `materials_ready + recovered: true`；description-only 不要求独立 source 文件。
- `note-names.lock`、navigation lock 与 reservation lock 使用 OS 原生文件锁；锁文件本身可以长期存在，进程退出时由操作系统释放锁，不依赖 `unlink()` 或 stale-lock 删除。
- Finalizer 始终校验真实元数据、路径、固定结构、AI 区域与 `analysis.json`。`strict` 模式还会校验三份阶段工作文件；`light` 模式不要求这些文件。旧 job 不含 `workflow_mode` 时保持兼容。无效草稿不会进入笔记库；`BILI_AI_*` marker 发布时会移除。
- `note_ready` 是业务完成状态。Job retire 或后续维护失败只通过 `temporary_data_retired` / `cleanup_warning` 反映，不把已经发布成功的笔记改判为失败。
- 导航采用临时文件后原子替换。
- 不同 BVID 可并行处理；导航重建使用独占 OS 文件锁串行执行，避免多个 finalizer 交叉覆盖同一组导航页。当前不会自动删除旧导航页，以免误删用户手写内容。
- 外部 yt-dlp 调用有超时。
- runtime lifecycle 只允许作用于 runtime root 的子目录；活动 Job 通过 rename/replace retire 到 `retired/`，正常主链不要求物理删除。
- 默认普通 `organize` 保留原文件名和全部字节：目标为 notes_root 内相对目录，归档前后检查 SHA-256；文件名冲突、Junction 路径逃逸、潜在断链均停止。核心先创建目标硬链接并确认同 inode 后移除旧路径，再刷新导航；若导航失败，必须报告文件已移动。`organize-batch` 按已审核的 runtime 计划逐篇执行并持久化检查点，失败可安全续跑；`organize-duplicates` 仅按明确保留/回收清单与单独 `--apply` 走 Windows 回收站。`resource` 压缩保留为独立可选的有损功能，绝不作为普通整理默认操作。
