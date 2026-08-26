# 架构说明

## 主链路

```text
已授权智能体入口中的复制链接 / BV 号 / 受支持短链
→ input_resolver 规范化 BVID 与 canonical URL
→ yt-dlp 仅采集元数据、UP 主简介、ai-zh/zh 字幕
→ taxonomy 生成 tags 与后续整理建议；原视频标题的新笔记进入 00-待整理
→ Python 在 runtime 写入确定性 Markdown 草稿、analysis.json 与 transcript
→ workflow_mode 路由：light 直接写作；strict 额外创建三份阶段工作文件
→ 接入智能体（Codex / Hermes / WorkBuddy）判断来源充分性
→ light 直接完成正文；strict 依次完成 Fact Ledger / Semantic Draft / Layout Pass
→ 两种模式都在内容完成后独立做一次版式优化
→ 智能体回看 transcript 完成 coverage review
→ finalizer 校验质量流程状态、真实元数据与结构后原子发布
→ navigation 原子刷新
→ runtime Job 退出活动区并 retire；物理清理不属于业务成功前提
```

## 代码分层

- `src/bili_learning/`：可测试的核心逻辑和 agent-neutral CLI（`prepare`、`finalize`、`organize`、`doctor`、`configure-obsidian`、`build-nav`）；`workflow.py` 只为 `strict` 模式创建并校验三份 runtime 工作文件。
- `docs/AGENT-INTEGRATION.md`：所有智能体共用的接入协议。
- `hermes-skills/bili-learning-automation/SKILL.md`：Hermes/微信专属适配约束。
- `hermes-skills/bili-learning-automation/scripts/`：只定位项目根目录并转发到核心 CLI 的兼容入口。
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
- `workflow_mode` 路由；`strict` 模式下额外生成 Fact Ledger / Semantic Draft / Layout Plan 脚手架及其路径；
- 导航。

taxonomy 的 route.path 不直接决定新文件的路径。新笔记统一先进入 fallback.path（默认 `00-待整理`）；route.path 仅随 job 保留为建议分类，并通过 tags 帮助 `organize` 在学习后归档。收集阶段 H1 直接使用原视频标题，不进行主题提炼。

接入智能体只负责字幕理解与语义内容：

- 判断字幕与简介是否足以支撑可信学习笔记；
- `light` 模式完整读取 transcript 后直接完成“先看结论 + 动态知识正文”，不创建阶段工作文件；
- `strict` 模式按 Fact Ledger → Semantic Draft → Layout Plan 执行；
- 两种模式都先把内容写完整，再独立做一次版式优化；
- 写短的“先看结论”；
- 根据视频真实信息结构组织动态知识正文；
- 最终排版后重新回到 transcript 完成覆盖复核；严格模式额外对照三份阶段工作文件。

章节、表格和步骤形式由内容决定；确定性骨架仍由程序控制，避免 LLM 重写元数据、简介或路径。

## 数据边界

- 长期产物：私人 Markdown 笔记与导航页，默认不入 Git。
- runtime 产物：`.runtime/bilibili-learning` 的活动 Job 始终包含 transcript、analysis 与草稿；`strict` 模式额外包含 Fact Ledger、Semantic Draft 与 Layout Plan。任务完成后 Job 从活动区 retire 到 `retired/`；物理删除属于独立维护，不参与笔记成功判定。
- 敏感数据：`key/` 中的 Cookie 文件；程序只把路径传给 yt-dlp，不读取内容。
- 历史资料：`archive/`、`materials/` 及本机 legacy 依赖，不属于公开源码主链路。

## 配置边界

正式用户推荐显式配置 `vault_root + notes_subdir`，由统一 settings loader 计算 `notes_root`；旧版 `notes_root` / `BILI_LEARNING_NOTES_ROOT` 保持兼容。taxonomy 的 `notes/bilibili` 只作为临时 repository fallback；未显式配置时，新采集会被 onboarding 门禁阻止，但已有 Job 的 finalizer / retire lifecycle 仍可继续。collector、finalizer、navigation 与 doctor 共用同一 settings loader。

## 可靠性原则

- 文件名使用原视频标题，同名时在 `note-names.lock` OS 文件锁保护下使用递增序号，避免覆盖。已完成视频允许再次转换并生成新笔记。
- 同一 BVID 仅在活动 collector、智能体写作与 finalizer 期间使用 reservation 防止并发；reservation 使用 `active / released` 状态文件，并由 OS 文件锁保护 claim / bind / release 的原子性。任务完成后切换为 `released`，允许再次转换。
- 如果 reservation 持有进程已经结束，而绑定 Job 的 `job.json`、草稿、`analysis.json`、transcript manifest 与字幕仍完整，核心会直接恢复已有 Job、必要时重建 `agent_handoff.md`，返回 `materials_ready + recovered: true`，不会重新调用 yt-dlp。
- `note-names.lock`、navigation lock 与 reservation lock 使用 OS 原生文件锁；锁文件本身可以长期存在，进程退出时由操作系统释放锁，不依赖 `unlink()` 或 stale-lock 删除。
- Finalizer 始终校验真实元数据、路径、固定结构、AI 区域与 `analysis.json`。`strict` 模式还会校验三份阶段工作文件；`light` 模式不要求这些文件。旧 job 不含 `workflow_mode` 时保持兼容。无效草稿不会进入笔记库；`BILI_AI_*` marker 发布时会移除。
- `note_ready` 是业务完成状态。Job retire 或后续维护失败只通过 `temporary_data_retired` / `cleanup_warning` 反映，不把已经发布成功的笔记改判为失败。
- 导航采用临时文件后原子替换。
- 不同 BVID 可并行处理；导航重建使用独占 OS 文件锁串行执行，避免多个 finalizer 交叉覆盖同一组导航页。当前不会自动删除旧导航页，以免误删用户手写内容。
- 外部 yt-dlp 调用有超时。
- runtime lifecycle 只允许作用于 runtime root 的子目录；活动 Job 通过 rename/replace retire 到 `retired/`，正常主链不要求物理删除。
- `organize` 只接收 notes root 内的现有 Markdown；它先原子创建目标文件，确认成功后才删除旧位置，再重建导航。
