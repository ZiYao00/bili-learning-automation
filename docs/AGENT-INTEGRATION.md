# 智能体接入协议

本项目当前优先服务 Codex、Hermes 与 WorkBuddy。核心脚本、Source Mode、内容质量标准、taxonomy 与 finalizer 是唯一事实来源；适配层只负责各平台的入口、当前消息意图路由、授权、调用和最终回复。未来其他智能体应复用核心协议，不复制来源采集、Job 或写作规则。

## 输入与授权

- 只接受可解析的 Bilibili 复制链接、受支持短链接或 BV 号。
- 无法解析 BV 号时要求用户重新发送“复制链接”，不得猜测。
- 适配层必须确认调用者已获授权；Hermes 的额外规则是只接受 owner 私聊，WorkBuddy 的额外规则是只接受用户在会话中主动提供链接/BV 号且意图明确。

## 必须执行的流程

1. 先通过统一 onboarding 门禁确认环境，再按当前消息的明确意图选择入口：默认 `prepare / subtitle_srt`；明确“纯资源分享 / 只整理简介 / 不用字幕”使用 `prepare-description / description_only`；默认入口返回 `subtitle_unavailable` 后，只有用户明确授权 ASR 才先取得纯文本并调用 `prepare-transcript / asr_text`。不得根据标题、历史 memory 或模型猜测自动改变来源模式。三个入口共用同一 Job lifecycle。
2. 读取 `handoff_path`、`job.json`、`analysis_path`、`workflow_mode` 与 `source_manifest_path`。按 manifest 完整读取实际存在的 source chunks，不自行切分或跳读。`description_only` 的 manifest 没有伪造 chunk；此时只读取 Job 中的标题、metadata、UP 主简介和明确用户补充来源。旧 Job 仍兼容 `transcript_manifest_path`。
3. 判断当前 `source_mode` 允许的来源是否足以支撑可信笔记，并填写 `analysis.json`。`description_only` 不得推断视频口播、画面参数或未提供的资源内容；任何模式来源不足时都停止，不用模型常识补事实。
4. 按 `workflow_mode` 执行：
   - `light`：读取 `docs\standards\LIGHT-WORKFLOW.md`，直接完成正文；先写完整内容，再做一次独立排版优化，不创建 Fact Ledger、Semantic Draft 或 Layout Plan。
   - `strict`：按 `fact_ledger_path → semantic_draft_path → layout_plan_path → draft_path` 执行，完整规则见 `CODEX-VIDEO-NOTE-GUIDE.md` 与 `KNOWLEDGE-DENSE-WORKFLOW.md`。
5. 最终排版后回看当前 Job 允许的来源，修正明显遗漏和无来源内容；strict 模式还要对照 Fact Ledger 与 Semantic Draft。完成后更新 `coverage_review`。
6. 无论成功、失败或中断，都由 finalizer 接管 runtime 生命周期。`note_ready` 即表示业务完成；`temporary_data_retired` / `cleanup_warning` 只描述 Job retire 或维护状态，不得把已经发布成功的笔记改判为失败。

`onboarding_required`、`in_progress`、`subtitle_unavailable`、`source_insufficient`、`failed` 和 `note_invalid` 都不是完成状态。

## 学习后整理授权

学习后整理与“转成笔记”是两套独立流程，**默认不执行**。任何适配层都不得在 finalizer 完成后自动改名、移动或归档笔记。

只有用户明确要求整理时才进入整理流程。如果用户尚未说明范围，适配层必须先询问“只整理最近一篇，还是全部待整理笔记？”，并等待明确的 `latest` / `all` 选择；用户已经明确给出范围时不重复询问。

范围确认后，适配层必须完整阅读目标笔记并显式给出短标题、唯一主分类、Tags 与一句简介，然后调用核心 `organize`。`--category` 必须来自 `taxonomy.organization.categories`，`--tag` 至少一个，`--confirmed-scope` 必须与用户选择一致。不得根据旧文件名或旧 Tags 直接批量猜分类，也不得绕过 organizer 手工移动文件。

视频生成分类优先按模型生态：MiniMax H3、Wan 系列、Seedance 等各自集中管理；`01-视频生成/90-进阶专题` 只用于真正跨模型、原理性、选型或对比内容。显存优化、首尾帧、数字人等技术维度优先使用 Tags，不继续增加模型目录下的多层分类。

Organizer 在改写短标题时会保留原视频标题，并统一更新 Tags、移动文件和重建导航。

## 数据契约

- 新生成的 `job.json` 继续使用 `schema_version: 1`，包含 `source_mode: subtitle_srt | asr_text | description_only`、`source_manifest_path`、source package 状态与 `workflow_mode: light | strict`。旧 `transcript_*` 字段作为迁移期兼容别名保留，新适配层使用 `source_*`。
- collector 与 finalizer 的 JSON 响应包含 `schema_version: 1`、`status` 和可读 `message`（如适用）；`materials_ready` 返回 `source_mode`、`source_manifest_path`、source package 状态与 `workflow_mode`，恢复时额外返回 `recovered: true`。智能体必须以结构化状态判断分支，不解析底层锁或 PID。
- Frontmatter 的 `author`、`published`、`duration`、`source`、tags 与 `cssclasses`，以及标题下方“作者 · 日期 · 时长 · BVID”元信息行由程序生成，智能体不得自行改写；视频笔记固定使用 `learning-page + video-note` 以接入共享 Obsidian 视觉系统。
- `analysis.json` 是 runtime-only 质量报告，不进入最终 Obsidian 笔记。它用于记录来源充分性、知识索引和覆盖复核状态。
- 只有 `strict` 模式会在 `agent_work_dir` 创建 `fact-ledger.md`、`semantic-draft.md` 与 `layout-plan.md`，并返回对应路径；`light` 模式不创建这些文件。

## 不可突破的数据边界

- 默认 `prepare` 使用 subtitle-first，但仍通过 `--skip-download` 不下载媒体；`prepare-transcript` 与 `prepare-description` 只采集 metadata / 简介，不请求字幕。ASR 只在 `subtitle_unavailable` 后得到用户明确授权时运行；description-only 只在当前消息明确要求纯资源分享时运行。
- `confirmed_empty` 仅代表 info-json 明确给出空字符串且（如存在）简介 sidecar 与其一致；字段缺失、`null`、类型异常或两者不一致都必须失败。
- Cookie 内容不得读取、打印、上传、编辑、提交或写入笔记；collector 仅可把配置的 Cookie 文件路径传给 yt-dlp。
- metadata、简介、source manifest、`analysis.json`、日志和智能体临时工作文件只允许存在于单个 runtime Job。SRT / ASR 模式包含 source 文件与 chunks；ASR 先复制为 runtime `asr-transcript.txt`；description-only 不伪造 source 文件或 chunks。finalizer / failsafe 负责 retire。
- 智能体只可编辑 `analysis.json`、草稿中的两个 AI 区域及当前模式明确提供的 runtime 工作文件。SRT 保留文字、顺序和 cue 边界；ASR 按标点/换行确定性分段且不生成虚假时间戳；description-only 的 manifest 只有来源契约而没有伪造 chunk。三种模式均不做摘要或语义过滤。
- 智能体不得手工删除 job、reservation 或锁文件。锁、reservation、恢复与 retire 都由共享核心管理；`note_ready` 已成立时，即使返回 `temporary_data_retired: false` 或 `cleanup_warning`，也只能作为维护警告报告，不能把已成功发布的笔记改判为失败。
- 不得覆盖已有笔记；同一 BVID 仅在**活动任务期间**由 reservation 防止并发处理，任务完成后允许再次转换。草稿只存在于 runtime，只有 finalizer 校验通过后才原子发布到 `note_path`。

## 来源充分性判断

当前 Job 允许的来源不等于视频本身。智能体必须先判断所选 `source_mode` 能否支撑可信笔记：subtitle / ASR 要评估文字连续性与专名质量；description-only 只能评估标题、metadata、UP 主简介和用户补充来源，不能把未采集的视频内容当作已知事实。

判断应结合上下文，不要用单一字符数或固定时长阈值代替思考。重点观察：

- 字幕是否连续、是否存在大面积缺句或乱码；
- 专有名词、模型名、节点名、参数是否严重损坏到无法恢复语义；
- 视频简介宣称的重要主题是否在字幕里实际出现；
- 是否大量依赖“这里、如图、这个参数、按这样连接”等画面信息，导致字幕无法说明关键事实；
- 是否能仅凭字幕与简介明确辨认主要结论、方法、参数、限制、比较和重要资源；
- `description_only` 是否确实能形成有价值的纯资源分享短记；若简介也没有可确认内容，应判定来源不足，而不是猜测视频内容。

如果不足，设置 `source_assessment.status = "insufficient"`，说明原因，`coverage_review.status = "not_applicable"`，不要编造正文，也不要把任务包装成完成。

## 内容提取与整理原则

正文事实只能来自当前 `source_mode` 允许的来源。subtitle / ASR 可使用对应文字与 UP 主简介；description-only 只能使用标题、metadata、UP 主简介和明确用户补充来源。不得利用模型常识补具体参数、资源地址或结论。若允许来源明确说明“三连 / 充电 / 评论关键词 / 私信 / 进群”等资料获取条件，核心会记录 `resource_access_notices`；资料本体未出现时只能说明条件，不得生成、还原或猜测。

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

subtitle / ASR 来源可能存在自动转写噪声。遇到不确定专名时：可确认就使用可确认写法；高度疑似但无法确认就保留“转写原音 / 名称未确认 / 待核实”等线索；完全无法判断时保留仍可确认的用途、关系、参数或实测结果并省略具体拼写。不得把低置信名称静默升级成确定事实。description-only 没有音频来源，不得用此规则反推视频口播。

长字幕或知识密集内容允许按 transcript chunk / 自然主题分段提取，但必须遵循 Fact Ledger → Semantic Draft → Layout Pass → Source Recheck。Fact Ledger 先保全原子事实；Semantic Draft 再自然聚类成文；Layout Pass 只转换表达形式。具体成员及其来源、继承、步数、适用条件、冲突和兼容关系不能被压成一个类别名或名称列表；来源明确讲解的运行路线、版本/插件安装条件、组件职责，以及“配置 → 耗时 / 质量变化 / 失败表现”的实测证据，也不能只剩一句泛化结论。正文在事实、参数、比较和实测证据已经完整保留后，可以额外提炼由当前来源共同支持的能力边界、因果关系或选择原则；这种提炼只能作为增量解释，不能替代支撑证据、删减原始条件或引入来源之外的新知识。不要把固定 Map-Reduce 流程强加给所有短视频。

## 最终笔记结构

程序负责：Frontmatter、H1、标题下方元信息行、UP 主资源、条件资料获取提示、原始简介、iframe、tags、cssclasses、文件名和路径。UP 主资源标题由程序根据原始简介中的资源小节、原标签和 URL 平台规范化，例如 `GitHub 插件 · MieNodes`、`工作流（夸克网盘）`、`国际站 · 体验地址`；重复 URL 去重，已包含平台名或平台简称的标签不重复追加平台。正式阅读顺序固定为：**标题 / 元信息 → 先看结论 → 播放器与来源区 → 动态知识正文**。播放器直接位于“先看结论”后，不显示额外“视频资料”标题；资料获取提示使用紧凑 Callout，UP 主资源使用逐条 Markdown 链接列表，视频简介使用紧凑段落，完整原始简介以“UP 主原文（完整说明与链接）”折叠保留。

智能体负责两个区域：

- `BILI_AI_SUMMARY`：短的“先看结论”，用于快速判断视频价值；只写结论、选择、关键参数、限制、风险和适用场景，不写“本文覆盖 / 本笔记包含 / 接下来介绍”这类目录式元描述；
- `BILI_AI_BODY`：根据视频真实信息结构动态组织的知识正文。

正文不强制出现“怎么做 / 容易踩坑 / 我来实践”。需要时可以使用这些章节，不需要时应省略。章节名称、数量、长短、表格、列表和步骤形式由内容决定。

## 覆盖复核

程序可以检查结构和流程状态，但不能可靠判断“知识有没有漏”。因此最终排版后必须由智能体重新回到当前 Job 允许的来源完成语义复核；strict 模式同时对照 Fact Ledger、Semantic Draft 与最终正文，不能只拿自己生成的 `knowledge_outline` 检查自己。

至少检查：

- `knowledge_outline` 中的重要参数、限制、比较和方法是否已经进入正文；
- 来源明确给出的运行入口、版本/安装前提、关键组件职责及可复用实测案例，是否被误判为口播而遗漏；
- 比较关系是否只写了一边；
- 默认值后面的例外或限制是否被误删；
- 多个方案是否被错误合并；
- H2 数量减少时，参数、成员、关系和实测证据是否也被同步压掉；
- Layout Pass 前后的高价值事实是否一一对应，是否为了卡片数量或页面简洁重新摘要；
- 是否为了简短而丢掉高价值具体信息；
- 是否出现当前 `source_mode` 允许来源没有支持的新事实；description-only 尤其检查是否误写了视频口播、画面参数或未提供资源本体。

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
