# Changelog

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
