# Changelog

## [Unreleased]

### Added

- 新增 `scripts/bili_asr_fallback.py` 作为 `subtitle_unavailable` 的人工应急旁路：仅在确认视频完全无字幕后，临时下载低码率音轨并调用 SiliconFlow `FunAudioLLM/SenseVoiceSmall` 输出纯文本 transcript；默认从被 Git 忽略的 `config/local.json` 读取 `siliconflow.api_key`，公开仓库只保留示例占位符；不接入 collector / finalizer，也不改变默认“不下载媒体”的 Skill 行为。
- Organizer 新增 `single` 范围，区分“用户明确指定单篇”与真正的 `latest`；`latest` 会验证文件确实是待整理目录中的最近一篇。
- Organizer 会检测相同 BVID 的其它笔记并作为 `duplicate_bvid_notes` 提示，不自动覆盖或删除测试稿；输出同时区分逻辑 Vault 路径与 Junction 解析后的真实路径。
- Organizer 简化为纯归档器：只改文件名和目标路径，不再改写 H1、简介、Tags、Frontmatter 或旧笔记结构；归档前后 Markdown 内容保持不变。
- 归档目录改为浅层“领域 / 对象”结构，最多两层；例如 `02-图像/Krea2`、`01-视频/MiniMax-H3`，不再维护多层 `organization.categories` / legacy 迁移表。

### Fixed

- 本机 `config/local.json` 与 taxonomy 配置现在使用 `utf-8-sig` 读取，兼容 Windows 编辑器写入的 UTF-8 BOM，避免 `local_config_invalid_json`。

## [1.0.0] - 2026-08-23

### Documentation

- 进入 v1.0 Feature Freeze：停止继续堆叠新功能，新增 `docs/RELEASE-CHECKLIST.md` 作为正式版发布门禁与 clean-room 验收清单。
- 新增 `README.en.md` 英文项目说明，并在中英文 README 之间提供语言切换入口。
- 统一 README 与 `LICENSE` 的授权口径，移除旧的“尚未选择发布许可证”残留说明。
- 记录 v1.0 clean-room 发布验收基线：真实 Bilibili → yt-dlp → transcript → Agent → finalizer 链路通过，确认默认不下载媒体、重复视频不覆盖、无效草稿不发布、runtime 可清理；验收记录见 `docs/reports/2026-08-22-v1.0-release-acceptance.md`。
- 同步 `docs/ARCHITECTURE.md` 与 `AGENTS.md` 的现行发布口径，移除旧阅读顺序、1 小时 reservation 窗口和历史 pre-push handoff 的控制面残留。

### Added

- 新增默认 `light` 写作模式：完整读取 transcript 后直接完成笔记，内容完成再做一次版式优化；不创建三份阶段工作文件。
- 新增 `workflow_mode: light | strict` 配置与 `BILI_LEARNING_WORKFLOW_MODE` 环境变量；`strict` 保留此前的可审计分阶段流程。
- collector 在 `strict` 模式下创建 runtime-only 的 `fact-ledger.md`、`semantic-draft.md` 与 `layout-plan.md`，并返回对应路径；继续沿用 `analysis.json schema_version: 1`。
- 新增 `docs/standards/KNOWLEDGE-DENSE-WORKFLOW.md`，固化知识密集型视频的 `Fact Ledger → Semantic Draft → Layout Pass → Source Recheck` 工作流。

### Changed

- `light` 写作标准不再把字数、KB 大小、章节数量或压缩比作为完成/质量指标；改为优先检查重大知识覆盖、对象关系、实测证据、失败表现、作者判断以及专名/数字/单位的事实保真。
- 对字幕中的模糊专有名词、数字与来源自身冲突采取保守策略：能由 UP 主简介明确还原才修正，否则保留不确定性；禁止为了“看起来合理”自行猜测。
- README 新增中立的模型实测参考：项目不绑定默认或必选 LLM，只记录当前样本中的质量表现、主要优势与风险，并强调最终笔记质量会随模型、Agent 宿主、代理后端和推理配置变化；所有模型仍共用同一套 `light` 标准与 Markdown 结构。
- 默认写作流程由强制分阶段改为 `light`：Agent 获得更大的内容组织与版式自由，只保留来源、确定性结构、发布和清理等硬边界。
- `strict` 模式继续执行 Fact Ledger → Semantic Draft → Layout Pass，并由 finalizer 校验阶段状态与最小内容；旧 job 不含 `workflow_mode` 时保持兼容。
- validator 现在拒绝同一视频笔记出现多个最高优先级 Summary，并阻止三份 runtime 工作文件名泄漏到正式笔记。
- 去除知识正文的固定章节偏置：`knowledge_outline` 明确只做事实保护，不与最终 H2 一一对应；写正文前先按共同对象、因果、流程、比较、前提和使用场景自然聚类，不预设章节数量；完整“五段式”百科示例改为互不相同的结构片段库。
- 知识密集型/百科型视频新增“原子事实清单 → knowledge_outline → 正文”的语义保护流程；coverage review 必须重新回到原 transcript，避免同一个 Agent 只对照自己生成的 outline 而遗漏成员关系、具体值、例外和兼容性。
- 视频资料提前到“先看结论”之后、知识正文之前；移除“原视频”三级标题，播放器改为单行结构，UP 主资源与视频简介改为紧凑展示，条件资料提示同步压缩。
- `video-note.css` 升级为 v0.2：视频原标题只比正文略大、略粗，并收紧播放器、资源、简介与原始简介的纵向留白。
- `organize` 同时兼容旧版 `### 视频简介` 和新版紧凑 `video-note-overview`；validator 同步校验新的阅读顺序。

> 最终 clean-room / 真实 E2E 结果见 `docs/reports/2026-08-23-v1.0-cleanroom-acceptance.md`；CI 以最终 Release tag 指向的提交为准。

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
- WorkBuddy 新增动态 `scripts/bridge.py`，通过安装 Junction 的真实位置解析项目根目录，移除机器专属项目路径与固定 `.venv` 路径依赖。
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
