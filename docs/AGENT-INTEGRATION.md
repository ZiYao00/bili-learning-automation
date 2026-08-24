# 智能体接入协议

本项目当前优先服务 Codex、Hermes 与 WorkBuddy。核心脚本、字幕采集、内容质量标准、taxonomy 与 finalizer 是唯一事实来源；适配层只负责各平台的入口、授权、调用和最终回复。未来其他智能体如需接入，应复用核心协议而不是复制一套新的写作规则。

## 输入与授权

- 只接受可解析的 Bilibili 复制链接、受支持短链接或 BV 号。
- 无法解析 BV 号时要求用户重新发送“复制链接”，不得猜测。
- 适配层必须确认调用者已获授权；Hermes 的额外规则是只接受 owner 私聊，WorkBuddy 的额外规则是只接受用户在会话中主动提供链接/BV 号且意图明确。

## 必须执行的流程

1. 把原始消息交给 collector，并按返回的 `status` 分支。`configuration_required` 时停止采集并询问 Vault；`ytdlp_not_configured` 时只提供安装指引；`in_progress` 不重复采集；只有 `materials_ready` 或确认可安全续做的旧 job 才继续。
2. 读取 `handoff_path`、`job.json`、`analysis_path`、`workflow_mode` 与 `transcript_manifest_path`。按 manifest 顺序完整读取全部 transcript chunk，不自行重新切分或跳读。
3. 先判断字幕与简介是否足以支撑可信笔记，并填写 `analysis.json`。来源不足时停止，不用模型常识补具体参数、资源或结论。
4. 按 `workflow_mode` 执行：
   - `light`：读取 `docs\standards\LIGHT-WORKFLOW.md`，直接完成正文；先写完整内容，再做一次独立排版优化，不创建 Fact Ledger、Semantic Draft 或 Layout Plan。
   - `strict`：按 `fact_ledger_path → semantic_draft_path → layout_plan_path → draft_path` 执行，完整规则见 `CODEX-VIDEO-NOTE-GUIDE.md` 与 `KNOWLEDGE-DENSE-WORKFLOW.md`。
5. 最终排版后回看 transcript，修正明显遗漏和无来源内容；严格模式还要对照 Fact Ledger 与 Semantic Draft。完成后更新 `coverage_review`。
6. 无论成功、失败或中断，都必须由 finalizer 清理 job。只有返回 `note_ready` 且 `temporary_data_removed: true` 才能报告完成。

`configuration_required`、`in_progress`、`subtitle_unavailable`、`source_insufficient`、`failed` 和 `note_invalid` 都不是完成状态。

## 学习后整理授权

学习后整理与“转成笔记”是两套独立流程，**默认不执行**。任何适配层都不得在 finalizer 完成后自动改名、移动或归档笔记。

只有用户明确要求整理时才进入整理流程。如果用户尚未说明范围，适配层必须先询问“只整理最近一篇，还是全部待整理笔记？”，并等待明确的 `latest` / `all` 选择；用户已经明确给出范围时不重复询问。

范围确认后，适配层必须完整阅读目标笔记并显式给出短标题、唯一主分类、Tags 与一句简介，然后调用核心 `organize`。`--category` 必须来自 `taxonomy.organization.categories`，`--tag` 至少一个，`--confirmed-scope` 必须与用户选择一致。不得根据旧文件名或旧 Tags 直接批量猜分类，也不得绕过 organizer 手工移动文件。

视频生成分类优先按模型生态：MiniMax H3、Wan 系列、Seedance 等各自集中管理；`01-视频生成/90-进阶专题` 只用于真正跨模型、原理性、选型或对比内容。显存优化、首尾帧、数字人等技术维度优先使用 Tags，不继续增加模型目录下的多层分类。

Organizer 在改写短标题时会保留原视频标题，并统一更新 Tags、移动文件和重建导航。

## 数据契约

- 新生成的 `job.json` 使用 `schema_version: 1`，并包含 `workflow_mode: light | strict`；当前默认值为 `light`。
- collector 与 finalizer 的 JSON 响应包含 `schema_version: 1`、`status` 和可读 `message`（如适用）；`materials_ready` 还会返回 `workflow_mode`。智能体必须以 `status` 与 `workflow_mode` 判断分支。
- Frontmatter 的 `author`、`published`、`duration`、`source`、tags 与 `cssclasses`，以及标题下方“作者 · 日期 · 时长 · BVID”元信息行由程序生成，智能体不得自行改写；视频笔记固定使用 `learning-page + video-note` 以接入共享 Obsidian 视觉系统。
- `analysis.json` 是 runtime-only 质量报告，不进入最终 Obsidian 笔记。它用于记录来源充分性、知识索引和覆盖复核状态。
- 只有 `strict` 模式会在 `agent_work_dir` 创建 `fact-ledger.md`、`semantic-draft.md` 与 `layout-plan.md`，并返回对应路径；`light` 模式不创建这些文件。

## 不可突破的数据边界

- 默认流程只采集 metadata、UP 主原始简介和 `ai-zh`/`zh.*` 的 SRT 字幕；不得下载音视频、启动 Chrome/CDP 或回退到 ASR。
- `confirmed_empty` 仅代表 info-json 明确给出空字符串且（如存在）简介 sidecar 与其一致；字段缺失、`null`、类型异常或两者不一致都必须失败。
- Cookie 内容不得读取、打印、上传、编辑、提交或写入笔记；collector 仅可把配置的 Cookie 文件路径传给 yt-dlp。
- 原始字幕、元数据、简介、`analysis.json`、日志和智能体临时工作文件只允许存在于 `.runtime/bilibili-learning` 的单个 job；finalizer 负责精确清理。
- 智能体只可编辑既定的 `analysis.json`、草稿中的两个 AI 区域，以及当前模式明确提供的 runtime 工作文件。原始 SRT 会被转换为 `transcript-manifest.json` 与一个或多个 transcript chunk；转换只移除 SRT 序号、毫秒精度与空行，保留字幕文字、顺序和 cue 边界，不做摘要或语义过滤。`light` 模式直接读取 transcript 并写笔记；`strict` 模式才使用 `fact-ledger.md`、`semantic-draft.md`、`layout-plan.md`。`agent_work_dir` 不得存放最终笔记或持久资料；其内容随 job 一并清理。
- 智能体不得手工删除 job、reservation 或锁文件。finalizer 清理失败时必须如实报告失败状态，保留现场供后续诊断；只有用户明确授权后，才可对已核实的单个遗留文件执行回收站归档。
- 不得覆盖已有笔记；同一 BVID 仅在**活动任务期间**由 reservation 防止并发处理，任务完成后允许再次转换。草稿只存在于 runtime，只有 finalizer 校验通过后才原子发布到 `note_path`。

## 来源充分性判断

字幕是视频内容的文字投影，不等于视频本身。智能体必须先判断当前字幕与简介是否足以支撑可信学习笔记。

判断应结合上下文，不要用单一字符数或固定时长阈值代替思考。重点观察：

- 字幕是否连续、是否存在大面积缺句或乱码；
- 专有名词、模型名、节点名、参数是否严重损坏到无法恢复语义；
- 视频简介宣称的重要主题是否在字幕里实际出现；
- 是否大量依赖“这里、如图、这个参数、按这样连接”等画面信息，导致字幕无法说明关键事实；
- 是否能仅凭字幕与简介明确辨认主要结论、方法、参数、限制、比较和重要资源。

如果不足，设置 `source_assessment.status = "insufficient"`，说明原因，`coverage_review.status = "not_applicable"`，不要编造正文，也不要把任务包装成完成。

## 内容提取与整理原则

正文事实只能来自当前视频字幕和 UP 主原始简介；不得利用模型常识补全视频没有提供的具体参数、资源地址或结论。若简介或字幕明确说明“三连 / 充电 / 评论关键词 / 私信 / 进群”等条件后才能领取模板、工作流或其他资料，核心会将其记录为 `resource_access_notices` 并在播放器下方的来源区展示。资料本体没有出现在当前来源时，智能体只能说明获取条件，不得自行生成、还原或猜测该资料内容。

对学习价值高的信息应优先保护，不能仅为了缩短篇幅而删除：

- 参数、数值、公式、数量和上下限；
- 模型、节点、插件、LoRA、格式、版本等专有名词；
- A/B 差异、适用条件和兼容性；
- 作者明确推荐、质量/速度/稳定性的取舍；
- 会改变结果的前提、例外、冲突和警告；
- 结构化方法、提示词公式、关键工作流；
- 视频明确给出的运行入口、版本/安装前提与关键组件职责；
- 具有长期参考价值的实测案例：使用条件、配置、耗时、质量变化或失败表现之间的关系；
- 视频明确提供且具有学习价值的资源地址。

这不是机械保留规则。广告价格、活动口播或与学习目标无关的数字是否保留，应由智能体根据长期参考价值判断。

视频字幕可能来自音频自动转写。遇到不确定专名时：来源可确认就使用可确认写法；高度疑似但无法确认就保留“字幕原音 / 名称未确认 / 待核实”等检索线索；完全无法判断时保留仍可确认的用途、关系、参数或实测结果并省略具体拼写。不得把低置信名称静默升级成确定事实，也不得仅因名称受损就删除与之关联的高价值知识。

长字幕或知识密集内容允许按 transcript chunk / 自然主题分段提取，但必须遵循 Fact Ledger → Semantic Draft → Layout Pass → Source Recheck。Fact Ledger 先保全原子事实；Semantic Draft 再自然聚类成文；Layout Pass 只转换表达形式。具体成员及其来源、继承、步数、适用条件、冲突和兼容关系不能被压成一个类别名或名称列表；来源明确讲解的运行路线、版本/插件安装条件、组件职责，以及“配置 → 耗时 / 质量变化 / 失败表现”的实测证据，也不能只剩一句泛化结论。正文在事实、参数、比较和实测证据已经完整保留后，可以额外提炼由当前来源共同支持的能力边界、因果关系或选择原则；这种提炼只能作为增量解释，不能替代支撑证据、删减原始条件或引入来源之外的新知识。不要把固定 Map-Reduce 流程强加给所有短视频。

## 最终笔记结构

程序负责：Frontmatter、H1、标题下方元信息行、UP 主资源、条件资料获取提示、原始简介、iframe、tags、cssclasses、文件名和路径。UP 主资源标题由程序根据原始简介中的资源小节、原标签和 URL 平台规范化，例如 `GitHub 插件 · MieNodes`、`工作流（夸克网盘）`、`国际站 · 体验地址`；重复 URL 去重，已包含平台名或平台简称的标签不重复追加平台。正式阅读顺序固定为：**标题 / 元信息 → 先看结论 → 播放器与来源区 → 动态知识正文**。播放器直接位于“先看结论”后，不显示额外“视频资料”标题；资料获取提示使用紧凑 Callout，UP 主资源使用逐条 Markdown 链接列表，视频简介使用紧凑段落，完整原始简介以“UP 主原文（完整说明与链接）”折叠保留。

智能体负责两个区域：

- `BILI_AI_SUMMARY`：短的“先看结论”，用于快速判断视频价值；只写结论、选择、关键参数、限制、风险和适用场景，不写“本文覆盖 / 本笔记包含 / 接下来介绍”这类目录式元描述；
- `BILI_AI_BODY`：根据视频真实信息结构动态组织的知识正文。

正文不强制出现“怎么做 / 容易踩坑 / 我来实践”。需要时可以使用这些章节，不需要时应省略。章节名称、数量、长短、表格、列表和步骤形式由内容决定。

## 覆盖复核

程序可以检查结构和流程状态，但不能可靠判断“知识有没有漏”。因此最终排版后必须由智能体完成语义复核，而且复核必须重新回到原 transcript，并同时对照 Fact Ledger、Semantic Draft 与最终正文；不能只拿自己生成的 `knowledge_outline` 检查自己。

至少检查：

- `knowledge_outline` 中的重要参数、限制、比较和方法是否已经进入正文；
- 来源明确给出的运行入口、版本/安装前提、关键组件职责及可复用实测案例，是否被误判为口播而遗漏；
- 比较关系是否只写了一边；
- 默认值后面的例外或限制是否被误删；
- 多个方案是否被错误合并；
- H2 数量减少时，参数、成员、关系和实测证据是否也被同步压掉；
- Layout Pass 前后的高价值事实是否一一对应，是否为了卡片数量或页面简洁重新摘要；
- 是否为了简短而丢掉高价值具体信息；
- 是否出现字幕/简介没有支持的新事实。

复核通过后设置 `coverage_review.status = "passed"` 并简要记录复核结果。Finalizer 只验证该流程确实完成，不用确定性算法假装评估语义完整度。

## 笔记内容边界

必须阅读 `docs\standards\CODEX-VIDEO-NOTE-GUIDE.md`。长字幕、百科型、参数密集或实测证据多的内容还必须阅读 `docs\standards\KNOWLEDGE-DENSE-WORKFLOW.md`。`docs\standards\STANDARD-VIDEO-NOTE-EXAMPLE.md` 是语法与局部结构片段参考，不再作为每次任务的强制目录示例；只有需要确认 Table / Grid / Card / Callout 等具体写法时再读取相关片段，且不得复制其中的章节集合、顺序、数量或组件组合。

所有新笔记先进入 `00-待整理`。H1 默认使用 B站原视频标题；程序在 H1 下方生成“作者 · 发布日期 · 时长 · BVID”的紧凑元信息行。允许重复链接再次生成笔记；同名文件由程序以 `（2）`、`（3）` 防覆盖。分类建议和 tags 由程序确定；智能体不得自行跳过 `00-待整理`。

## 学习后整理流程

只有用户明确要求“整理笔记”后，智能体才可调用统一核心入口：

```powershell
bili-learning organize --note '<现有笔记路径>' --title '<学习后短标题>' --intro '<一句简介摘要>'
```

- `--title` 与 `--intro` 只能基于现有笔记、UP 主简介和用户的学习判断；不得捏造参数或资源。
- 省略 `--category` 时，核心按现有 tags 推断 taxonomy 建议目录。
- 核心负责原子创建、迁移和导航刷新；适配层不得自行移动或重命名文件。

## 适配层边界

- Hermes：微信私聊授权、链接接收、Hermes 安装、调用核心脚本和最终回复。
- Codex：在项目目录中读取 `AGENTS.md`、本协议和共享标准，直接使用核心流程；目前不要求独立 Codex Skill。
- WorkBuddy：适配层位于 `workbuddy-skills\bili-learning-automation\`，通过 junction 安装到 `%USERPROFILE%\.workbuddy\skills\`；负责会话触发、意图确认、调用核心脚本和最终回复，与 Hermes 共用同一套脚本入口。
- 未来其他平台：只新增薄适配层，不复制核心 Python 逻辑、内容标准、taxonomy 或 finalizer。
