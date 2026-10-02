# Changelog

## [Unreleased]

### Changed

- Skill 架构进一步收敛为单一 canonical 本地入口：Codex、Hermes、WorkBuddy 的用户级 Skill 目录直接 Junction 到 `skill/bili-learning-automation/`，仓库不再生成或维护宿主专用 Skill 副本；宿主路径 / `PYTHONPATH` 兼容统一由 canonical Skill 内的 `local_bridge.*` 处理。
- 只保留 ChatGPT Web 的独立分发包；`scripts/build_chatgpt_skill.py` 直接从 canonical Skill 与当前公开项目文档生成安全 `references/` 快照，连接本地项目后仍以 `AGENTS.md`、当前 Job handoff 与本地文档为运行事实源。
- 笔记存储支持推荐的 hybrid 拓扑：`notes_root` 作为项目内 Git-ignored 的真实 Markdown 真源，`vault_root + notes_subdir` 作为 Obsidian 映射元数据；doctor/onboarding 新增 `obsidian_notes_mapping` 校验，要求 Vault 子目录 Junction 正确指向 `notes_root`。

### Removed

- 退役旧 Chrome/CDP collector、Hermes 子命令 wrappers、WorkBuddy 独立 bridge 目录、Codex 仓库级生成副本以及旧多宿主 package builder；本地三 Agent 统一复用 canonical Skill。
- 退役仓库自定义 source snapshot 备份脚本；源码回滚以 Git / tag / release 为准。已确认无主链依赖的本机历史目录移入 Windows 系统回收站，由维护者自行清理。

## [1.4.0] - 2026-09-10

### Added

- 新增条件触发的 UP 主置顶一级评论资源补充：默认仅当简介/字幕明确指向评论区资源时执行一次匿名只读请求；另支持用户在本机私有白名单中主动配置 UP 主身份，白名单命中时使用项目现有 Netscape Cookie 做且只做一次只读请求，以兼容当前传统评论接口的认证要求。公开仓库只提供空模板，不预置任何 UP 主。两种模式都不翻页、不抓普通评论或楼中楼、不重试；请求失败或无置顶评论时直接降级，不影响既有笔记生成主链。

### Changed

- Skill 架构改为单一真源：只人工维护 `skill/bili-learning-automation/SKILL.md`，ChatGPT、Codex、Hermes、WorkBuddy 的安装出口与 ZIP 由 `scripts/build_agent_skill_packages.py` 自动同步/生成；新增 `--check` 防止宿主副本漂移，现有安装路径与宿主特有的最小权限边界继续兼容。
- 多项目 / `Top N` 笔记统一按来源顺序使用连续编号 `01 → N`；概览表与详细标题复用同一编号。来源明确提供外部 URL 时，项目 / 工具 / Skill 名称直接挂 Markdown 超链接；能力链、分类和对比只作为补充关系层，不再打乱主序列。
- UP 主简介与 UP 主置顶评论中的资源先进入同一作者资源池再按规范化 URL 去重；用户显式补充来源仍保持独立，不与作者来源混并。

### Fixed

- 修复裸 GitHub 仓库链接缺少描述时退化成 `UP 主资源 N（GitHub）` 的问题；现在直接从 URL 提取仓库名作为显示名称，不新增 GitHub 网络请求。
- 修复资源 URL 解析会把中文逗号、句号等后续说明吞入链接的问题；原始作者文本仍完整保留在折叠来源区。
- 修复 UP 主简介采用“项目说明行 + 下一行通用链接”时，资源名称退化为重复“链接（GitHub）”的问题；解析器现在优先提取可信项目上下文，同时保留“国际站 · 体验地址”等既有章节语义。
- Hermes 核查刚生成或指定笔记时，优先使用当前 Job / finalizer 路径与已配置 Vault 范围，不再从磁盘根目录或无关项目开始扩大搜索。

### Documentation

- 快速入门新增 `local-ASR-service` 可选本地部署说明：仅在用户确认无字幕并明确要求 ASR 时，用其取得真实纯文本后交回 `prepare-transcript`；不改变默认字幕优先、不开启自动下载或自动转写。

## [1.3.0] - 2026-08-28

### Added

- 新增独立 `bili-learning-automation-chatgpt`、`bili-learning-automation-codex`、`bili-learning-automation-hermes` 与 `bili-learning-automation-workbuddy` 薄适配层；四者使用不同 Skill 名称和安装包，避免不同宿主把同名入口识别为重复技能。
- 新增共享 `scripts/run_bili_learning.py`，让 ChatGPT 与 Codex 直接调用核心 CLI，不再借用其它宿主的兼容脚本。
- 新增白名单打包脚本与测试，分别生成 ChatGPT / Codex / Hermes / WorkBuddy ZIP，并强制每包只有一个根目录 `SKILL.md`，拒绝 Cookie、本机配置、嵌套 Skill 和 Python 缓存。
- 学习后 Organizer 新增显式 `resource` 分支：只在用户主动整理时，把纯资源分享压缩成短资源卡并聚合到 `05-资源` 集合页；普通 `archive` 仍保持 Markdown 正文完全不改写。资源压缩前会把原独立笔记备份到 runtime，资源集合页不会参与普通 BVID 重复更新判断。

### Documentation

- 新增 ChatGPT 与 Codex 安装教程，并为 Hermes 与 WorkBuddy 补充独立 ZIP 说明，明确本地桥接、仓库级 Skill、Junction、ZIP 更新和“安装成功不等于运行环境 ready”的验收边界。
- README、Quickstart、文档中心、Agent 接入协议和发布检查同步为四个独立薄入口。

## [1.2.0] - 2026-08-28

### Added

- 新增统一 Source Mode 契约：`subtitle_srt`、`asr_text`、`description_only` 三种来源共用同一个 Job lifecycle、source manifest、handoff、finalizer、恢复与 retire 逻辑。
- 新增 `prepare-transcript`，把用户明确授权后由独立 ASR 工具取得的无时间戳纯文本接回标准 Job；不自动下载音频、不自动调用 ASR，也不伪造 SRT / 时间戳。
- 新增 `prepare-description`，仅在用户当前消息明确要求“纯资源分享 / 只整理简介 / 不用字幕”时，只采集 metadata 与 UP 主简介并创建标准短记 Job；不请求字幕，也不推断视频口播或画面事实。
- 新增已发布 BVID 前置检查与 `existing_note_found` 状态；三个来源入口在采集前统一让用户选择更新、重新执行或取消。新增 `--on-existing ask|update|rerun` 与 `--update-target`。

### Changed

- `prepare`、`prepare-transcript` 与 `prepare-description` 现在只保留清晰的外部入口，内部统一调用 `_prepare_materials`；ASR 与 description-only 的 metadata 采集不再附带字幕请求。
- Hermes / WorkBuddy Skill 收敛为三路显式意图路由和统一 `materials_ready → handoff → finalize` 主干，不复制核心实现，也不允许根据标题、历史 memory 自动跳过字幕；重复 BVID 只增加 `existing_note_found` 的用户选择路由，具体检测、快照、哈希和发布仍由核心处理。

### Fixed

- 无字幕 ASR 旁路不再要求 Agent 手工组装 `job.json` / draft / manifest；纯资源分享也不再通过直接修改已发布笔记绕过 finalizer。
- 完整 Job 的恢复现在校验请求的 `source_mode`；description-only 可在没有独立 source 文件的情况下恢复，ASR Job 使用 runtime 内副本恢复。
- 保留 schema-v1 的 `transcript_*` 响应别名，已安装适配层与旧 Job 可以在迁移期间继续工作；新代码使用 `source_*` 契约。
- 重复链接不再先生成 `（2）` 后事后提醒；默认在 yt-dlp 与 Job 创建前拦截。更新模式保留原路径，保存旧笔记快照并记录 SHA-256；finalizer 只在目标未被再次修改时原子替换，否则返回 `update_conflict`。

## [1.1.0] - 2026-08-27

### Added

- 新增统一首次使用 onboarding：Hermes、WorkBuddy、Codex 在正式采集前共用同一结构化环境检查；Vault、Cookie、yt-dlp、Python 等必需项返回 `actions`，CSS 缺失只作为非阻塞 `warnings`。
- 新增 `configure-cookie` 与 `configure-ytdlp` 本机配置入口，以及 Hermes 对应兼容 launcher；只保存 Cookie 文件路径或自定义 yt-dlp 路径，不读取 Cookie 内容，也不自动安装软件。
- 新增 `scripts/bili_asr_fallback.py` 作为 `subtitle_unavailable` 的人工应急旁路：仅在确认视频完全无字幕后，临时下载低码率音轨并调用 SiliconFlow `FunAudioLLM/SenseVoiceSmall` 输出纯文本 transcript；默认从被 Git 忽略的 `config/local.json` 读取 `siliconflow.api_key`，公开仓库只保留示例占位符；不接入 collector / finalizer，也不改变默认“不下载媒体”的 Skill 行为。
- Organizer 新增 `single` 范围，区分“用户明确指定单篇”与真正的 `latest`；`latest` 会验证文件确实是待整理目录中的最近一篇。
- Organizer 会检测相同 BVID 的其它笔记并作为 `duplicate_bvid_notes` 提示，不自动覆盖或删除测试稿；输出同时区分逻辑 Vault 路径与 Junction 解析后的真实路径。
- Organizer 简化为纯归档器：只改文件名和目标路径，不再改写 H1、简介、Tags、Frontmatter 或旧笔记结构；归档前后 Markdown 内容保持不变。
- 归档目录改为浅层“领域 / 对象”结构，最多两层；例如 `02-图像/Krea2`、`01-视频/MiniMax-H3`，不再维护多层 `organization.categories` / legacy 迁移表。

### Changed

- WorkBuddy / Hermes 的 `SKILL.md` 收敛为薄控制层：保留 onboarding → prepare → handoff 写作 → finalize 主干，把 light / strict 细节、安装分支和确定性状态判断交回核心与按需文档，减少重复上下文和规则漂移。
- onboarding 新增面向 Agent 的 `summary`，即使环境已经 `ready` 也会明确返回 Python、yt-dlp、Cookie 就绪状态、Obsidian、CSS 与 workflow mode；yt-dlp 单纯版本探测超时不再作为面向用户的 warning，summary 保持 `ready`，完整 doctor 仍保留诊断记录，真正不可执行仍需修复。
- runtime 生命周期改为业务主链零删除依赖：文件锁使用 OS 原生锁，reservation 改为 `active / released` 持久状态，活动 Job 完成后 retire 到 `.runtime/bilibili-learning/retired/`；物理删除从笔记成功条件中剥离。
- 用户在转换消息中明确标注“视频简介 / UP主附加内容 / 附加信息 / 资源”等来源时，核心会作为 `user_supplied_source` 与 B站采集简介分层保留；两者不自动覆盖，冲突交给 Agent 明示来源差异。

### Documentation

- 新增 `docs/BILIBILI-COOKIE.md`，面向第一次使用的用户解释 Bilibili Cookie 的用途、Netscape `cookies.txt` 格式、浏览器导出方式、`SESSDATA` 常见误区、安全保存、`--cookies-from-browser` 风险、Windows `Failed to decrypt with DPAPI` 与 Cookie 失效处理。
- Quickstart、README、配置、依赖、安全和故障排查文档统一补充 Cookie 获取入口，并明确 Agent 只接收 Cookie 文件路径、不接收凭据内容；同时清理 Quickstart / Troubleshooting 中残留的旧 Organizer 参数与 `configuration_required` 状态。
- README、Quickstart、架构、Agent 接入、WorkBuddy 安装和故障排查统一更新 runtime 新语义：核心恢复 `recovered: true`、OS 文件锁、reservation 状态化、Job retire、`note_ready` 与维护状态解耦，以及 WorkBuddy safe-delete / PowerShell / MSYS 路径兼容。

### Fixed

- 安装 / 检查 / 验证 Skill 现在也会执行 onboarding：Hermes、WorkBuddy 与 Codex 明确区分“Skill 已安装”和“运行环境已就绪”，避免只验证目录链接或 `SKILL.md` 一致就误报“可以使用”；同时清理 Hermes / WorkBuddy 适配层与 WorkBuddy 安装教程中残留的旧 `configuration_required` / `ytdlp_not_configured` 分支。
- 本机 `config/local.json` 与 taxonomy 配置现在使用 `utf-8-sig` 读取，兼容 Windows 编辑器写入的 UTF-8 BOM，避免 `local_config_invalid_json`。
- 修复 WorkBuddy safe-delete 与旧 runtime 删除策略的冲突：正常锁释放、reservation 生命周期、Job 收尾和发布 staging 不再依赖 `Path.unlink()` / `shutil.rmtree()`；即使沙箱返回 `windows-sandbox-recycle-bin-unavailable`，业务主链仍可继续。
- 死进程绑定的完整 Job 现在由核心自动恢复：验证 `job.json`、草稿、analysis、transcript manifest 与字幕，缺少 `agent_handoff.md` 时自动重建，并返回 `materials_ready + recovered: true`；恢复过程明确禁止重新调用 yt-dlp。
- reservation claim / bind / release 使用独立 OS 文件锁串行化，保留同一 BVID 只有一个活动任务的并发原子性；死进程留下的不完整 Job 会先 retire 再允许新任务继续。
- finalizer 发布改为可安全重试：若前一次已经写出完全相同的正式笔记但返回丢失，重试返回 `note_ready + publish_state=already_published`，不同内容的同名文件仍严格拒绝覆盖；runtime retire/维护失败只返回 warning，不覆盖已经成功的发布状态。
- WorkBuddy 实机链接转换已在上述修复后通过，覆盖 `prepare → 写作 → finalize → note_ready → retire` 主链。

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
