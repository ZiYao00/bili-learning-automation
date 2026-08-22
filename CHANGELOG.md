# Changelog

## Unreleased

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
- 正式阅读顺序调整为“标题/BVID → 先看结论 → 播放器 → 知识正文 → 视频资料”；视频资料压成单一附录区，原始简介继续折叠保留。
- 长字幕处理改为 job 内受控 `agent-work` 工作区：核心会自动把 SRT 转换为 `transcript-manifest.json` 与一个或多个 transcript chunk，按完整 cue 边界分块且不做语义删减；Hermes 按 manifest 阅读，并可继续创建逐块知识摘录、索引和中间梳理文件，避免超长 SRT 被一次性压入上下文。极小尾块会自动并回前一块，避免为了几十字节额外触发一次 Agent 读取。所有临时文件由 finalizer / failsafe 随 job 统一清理。任务、reservation 与 stale-job 保护窗口统一为 2 小时；`in_progress` 会返回绑定 `job_dir`，让适配层在确认是陈旧且未写作的完整 job 时直接续做，无需默认 doctor 或重新采集。

### Security

- Cookie 内容仍不读取、不输出、不提交；只向 yt-dlp 传递配置的 Cookie 文件路径。
- runtime cleanup 继续限制在 `.runtime/bilibili-learning` 子目录。
