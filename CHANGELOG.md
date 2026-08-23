# Changelog

## [Unreleased]

### Documentation

- 进入 v1.0 Feature Freeze：停止继续堆叠新功能，新增 `docs/RELEASE-CHECKLIST.md` 作为正式版发布门禁与 clean-room 验收清单。
- 新增 `README.en.md` 英文项目说明，并在中英文 README 之间提供语言切换入口。
- 统一 README 与 `LICENSE` 的授权口径，移除旧的“尚未选择发布许可证”残留说明。
- 完成 v1.0 clean-room 发布验收：真实 Bilibili → yt-dlp → transcript → Agent → finalizer 链路通过，确认默认不下载媒体、重复视频不覆盖、无效草稿不发布、runtime 可清理；验收记录见 `docs/reports/2026-08-22-v1.0-release-acceptance.md`。
- 同步 `docs/ARCHITECTURE.md` 与 `AGENTS.md` 的现行发布口径，移除旧阅读顺序、1 小时 reservation 窗口和历史 pre-push handoff 的控制面残留。

### Added

- collector 为每个任务创建 runtime-only 的 `fact-ledger.md`、`semantic-draft.md` 与 `layout-plan.md`，并在 job / `materials_ready` 中返回对应路径，用于分离事实保全、内容成稿与视觉排版；继续沿用 `analysis.json schema_version: 1`。
- 新增 `docs/standards/KNOWLEDGE-DENSE-WORKFLOW.md`，固化知识密集型视频的 `Fact Ledger → Semantic Draft → Layout Pass → Source Recheck` 工作流。

### Changed

- 知识密集型笔记改为分阶段生成：章节数量只决定事实分组，不改变事实保留预算；Semantic Draft 完成后才进行 Layout Pass，排版不得再次摘要、重新选择或删除事实；最终 coverage review 同时对照原 transcript、Fact Ledger、Semantic Draft 与正式正文。
- finalizer 通过 runtime 工作文件的 `workflow_status` 与最小内容检查，拒绝跳过 Fact Ledger / Semantic Draft / Layout Pass 的新任务；短且简单的视频可将 Fact Ledger 标记为 `not_applicable`，但必须说明原因。旧 job 不含新字段时保持兼容。
- validator 现在拒绝同一视频笔记出现多个最高优先级 Summary，并阻止三份 runtime 工作文件名泄漏到正式笔记。
- 去除知识正文的固定章节偏置：`knowledge_outline` 明确只做事实保护，不与最终 H2 一一对应；写正文前先按共同对象、因果、流程、比较、前提和使用场景自然聚类，不预设章节数量；完整“五段式”百科示例改为互不相同的结构片段库。
- 知识密集型/百科型视频新增“原子事实清单 → knowledge_outline → 正文”的语义保护流程；coverage review 必须重新回到原 transcript，避免同一个 Agent 只对照自己生成的 outline 而遗漏成员关系、具体值、例外和兼容性。
- 视频资料提前到“先看结论”之后、知识正文之前；移除“原视频”三级标题，播放器改为单行结构，UP 主资源与视频简介改为紧凑展示，条件资料提示同步压缩。
- `video-note.css` 升级为 v0.2：视频原标题只比正文略大、略粗，并收紧播放器、资源、简介与原始简介的纵向留白。
- `organize` 同时兼容旧版 `### 视频简介` 和新版紧凑 `video-note-overview`；validator 同步校验新的阅读顺序。

> 以上修复发生在早先 clean-room 基线验收之后，因此正式 v1.0 Release 前必须重新执行 clean-room / 真实 E2E；`pyproject.toml` 暂时继续保持当前开发版本。

## [0.1.1] - 2026-08-22

### Added

- 条件资料识别：核心会从简介与相邻字幕 cue 中保守识别“三连 / 充电 / 评论关键词 / 私信 / 进群”等领取模板、工作流或资料的明确条件，只展示来源原话与获取方式，不生成未采集到的资料本体。
- 标题下方增加“作者 · 发布日期 · 时长 · BVID”紧凑元信息行，减少单独 BVID 行的割裂感。

### Changed

- 正式阅读顺序调整为“标题/元信息 → 先看结论 → 知识正文 → 视频资料”；播放器下移到“视频资料 → 原视频”，首屏优先展示可读知识。
- `video-note.css` 缩小长视频 H1，并放宽标题可用行宽；只影响 `learning-page + video-note`，不改变共享 Learning Lab 页面。
- “视频资料”按实际内容动态展示“资料获取方式 / UP 主资源 / 视频简介”，原始简介继续折叠保留。

### Fixed

- 过滤 `--------------在线工作流区域--------------`、`工作流：xxx` 等资源栏目文本，避免被误选为“视频简介”；正常内容性简介仍会保留。
- 保留国际站 / 国内站等资源栏目上下文，避免多个“体验地址”无法区分。
- 避免 `夸克网盘（夸克网盘）` 这类平台名重复，并对紧凑资源列表中的重复 URL 去重。
- 原始简介在渲染前先规范化 HTML entity，避免 `&amp;amp;` 二次转义。
- 学习后 `organize` 兼容新的元信息行与“只有资源、没有内容性视频简介”的笔记；legacy 笔记迁移时保持单一播放器。

## [0.1.0] - 2026-08-22

### Added

- Obsidian 首次绑定流程：新增 `vault_root + notes_subdir` 配置模型、`configure-obsidian` 统一入口，以及 Vault / CSS doctor 检查；未显式配置时新采集返回 `configuration_required`，不再静默写入仓库 fallback。
- yt-dlp 首次使用改为“只检测、不代安装”：默认通过 PATH 自动发现，缺失时 doctor/collector 返回 `winget install yt-dlp` 与官方安装入口；仓库和 Skill 不内置 `yt-dlp.exe`。
- WorkBuddy 新增动态 `scripts/bridge.py`，通过安装 Junction 的真实位置解析项目根目录，移除本机 `G:\GitHub\...` 与固定 `.venv` 路径依赖。
- `src/bili_learning` 核心 package，集中管理配置、输入解析、分类、模板、校验、导航和 doctor。
- 原视频标题文件名 + 同名序号防覆盖规则；BVID 固定显示在 H1 下方，活动任务期间使用 reservation 防并发。
- Bilibili 短链受控解析。
- 简介三态：`present` / `confirmed_empty` / `failed`。
- 确定性 Markdown 骨架和两个 Agent 内容区域：`BILI_AI_SUMMARY` + `BILI_AI_BODY`。
- 强校验 finalizer、无效笔记隔离、BVID 采集锁、原子导航写入、yt-dlp 超时、doctor、pytest、Ruff 和 GitHub Actions。
- 配置、开发、故障排查和 legacy 文档。
- 面向新手的使用文档体系：新增 `docs/QUICKSTART.md` 与 WorkBuddy 安装教程，并将 README、配置、Hermes 安装和故障排查重写为“安装 → 配置 → 使用 → 状态解释 → 排障”的教程式结构。
- runtime `analysis.json` 质量门禁：来源充分性、`knowledge_outline` 与成稿覆盖复核；来源不足时可返回 `source_insufficient` 而不发布低质量笔记。
- Obsidian 视觉系统：仓库自带 `obsidian/snippets/learning-lab.css` 与 `video-note.css`，新笔记自动使用 `learning-page + video-note`，并提供完整安装、升级和故障排查教程。

### Changed

- 中文展示名统一为「B站视频转笔记」，内部标识继续使用 `bilibili-learning`。
- `notes_root` 改为由统一 settings loader 读取 taxonomy。
- Hermes 不再负责重写 Frontmatter、简介、iframe、tags 或文件路径。
- legacy Chrome/CDP collector 明确标记为 deprecated。
- AI 正文从固定“怎么做 / 坑点 / 实践”四段式升级为“先看结论 + 动态知识正文”，按视频实际知识关系选择 Table / Grid / Card / Chip / Risk / Resource。
- 知识提取规则增加“类别成员不可被二次压缩”和“原则 + 典型可直接使用值”保护，H3 百科视频继续作为知识密集型回归样本。
- 长字幕处理改为 job 内受控 `agent-work` 工作区：核心会自动把 SRT 转换为 `transcript-manifest.json` 与一个或多个 transcript chunk，按完整 cue 边界分块且不做语义删减；Hermes 按 manifest 阅读，并可继续创建逐块知识摘录、索引和中间梳理文件，避免超长 SRT 被一次性压入上下文。极小尾块会自动并回前一块，避免为了几十字节额外触发一次 Agent 读取。所有临时文件由 finalizer / failsafe 随 job 统一清理。任务、reservation 与 stale-job 保护窗口统一为 2 小时；`in_progress` 会返回绑定 `job_dir`，让适配层在确认是陈旧且未写作的完整 job 时直接续做，无需默认 doctor 或重新采集。

### Security

- Cookie 内容仍不读取、不输出、不提交；只向 yt-dlp 传递配置的 Cookie 文件路径。
- runtime cleanup 继续限制在 `.runtime/bilibili-learning` 子目录。
