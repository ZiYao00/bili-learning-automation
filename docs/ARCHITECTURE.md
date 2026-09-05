# 架构说明

## 主链路

```text
已授权智能体入口中的复制链接 / BV 号 / 受支持短链
→ input_resolver 规范化 BVID 与 canonical URL
→ 适配层只根据当前消息的明确意图选择 source_mode：默认 `subtitle_srt`；明确授权 ASR 后使用 `asr_text`；明确“纯资源分享 / 只整理简介 / 不用字幕”使用 `description_only`
→ `prepare` / `prepare-transcript` / `prepare-description` 先按 BVID 检查已发布笔记；默认重复返回 `existing_note_found`，用户明确选择 rerun / update 后才继续 `_prepare_materials`
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

- `src/bili_learning/`：可测试的核心逻辑和 agent-neutral CLI。`prepare`、`prepare-transcript`、`prepare-description` 只是清晰的外部入口，内部共用 `_prepare_materials`；`source.py` 定义三种 Source Mode，`transcript.py` 生成统一 source manifest；`pinned_comment.py` 负责条件触发/白名单置顶一级评论补充；`workflow.py` 只为 `strict` 模式创建并校验三份 runtime 工作文件。
- `skill/bili-learning-automation/`：唯一需要人工维护的 Skill 真源；不复制评论策略、Cookie 细节、taxonomy 或 finalizer 业务规则。
- `scripts/build_agent_skill_packages.py`：从统一 Skill 真源生成 ChatGPT、Codex、Hermes、WorkBuddy 的安装出口与 ZIP，并通过 `--check` 检查生成副本是否漂移。
- `docs/AGENT-INTEGRATION.md`：所有智能体共用的接入协议。
- ChatGPT、Codex、Hermes、WorkBuddy 的宿主目录只保留由构建脚本生成的 `SKILL.md` 安装副本；宿主特有内容仅限最小权限/安装边界。
- `hermes-skills/bili-learning-automation/scripts/`、`workbuddy-skills/bili-learning-automation/scripts/`：只处理宿主路径/进程兼容；同目录 `SKILL.md` 也是生成安装出口，不是第二套流程源码。
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
- 敏感数据：`key/` 中的 Cookie 文件。正常字幕/简介采集仍把文件路径交给 yt-dlp；命中置顶评论白名单时，`pinned_comment.py` 会在本机读取 Netscape Cookie 并构造一次只读评论请求。Cookie 值不得打印、写入 Job/笔记、上传或提交。
- 历史资料：`archive/`、`materials/` 及本机 legacy 依赖，不属于公开源码主链路。

## 配置边界

正式用户推荐显式配置 `vault_root + notes_subdir`，由统一 settings loader 计算 `notes_root`；旧版 `notes_root` / `BILI_LEARNING_NOTES_ROOT` 保持兼容。taxonomy 的 `notes/bilibili` 只作为临时 repository fallback；未显式配置时，新采集会被 onboarding 门禁阻止，但已有 Job 的 finalizer / retire lifecycle 仍可继续。collector、finalizer、navigation 与 doctor 共用同一 settings loader。

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
- `organize` 只接收 notes root 内的现有 Markdown；它先原子创建目标文件，确认成功后才删除旧位置，再重建导航。
