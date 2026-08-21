# 智能体接入协议

本项目当前优先服务 Codex、Hermes 与 WorkBuddy。核心脚本、字幕采集、内容质量标准、taxonomy 与 finalizer 是唯一事实来源；适配层只负责各平台的入口、授权、调用和最终回复。未来其他智能体如需接入，应复用核心协议而不是复制一套新的写作规则。

## 输入与授权

- 只接受可解析的 Bilibili 复制链接、受支持短链接或 BV 号。
- 无法解析 BV 号时要求用户重新发送“复制链接”，不得猜测。
- 适配层必须确认调用者已获授权；Hermes 的额外规则是只接受 owner 私聊，WorkBuddy 的额外规则是只接受用户在会话中主动提供链接/BV 号且意图明确。

## 必须执行的流程

1. 把原始收到的文本交给 collector。
2. 仅当 collector 返回 `materials_ready` 时，读取 `handoff_path`、`job.json`、`analysis_path`、`agent_work_dir`、`transcript_manifest_path` 和共享内容标准。程序会把原始 SRT 整理为 runtime-only transcript；短字幕为单块 `direct`，长字幕为按完整 cue 边界生成的 `chunked` 清单。
3. 先判断字幕与简介是否足以支撑可信学习笔记，并填写 runtime 的 `analysis.json`。
4. 来源充分时先形成 `knowledge_outline`，再编辑 `draft_path` 中的 `BILI_AI_SUMMARY` 与 `BILI_AI_BODY` 两个区域。
5. 成稿后重新对照字幕或 `knowledge_outline` 做覆盖复核；确认无重要遗漏、无来源外补写后，将 `coverage_review.status` 设为 `passed` 并填写 notes。
6. 无论写作成功、失败或中断，都必须运行 finalizer 清理 job。
7. 只有 finalizer 返回 `note_ready` 且 `temporary_data_removed: true` 才能报告完成。

`in_progress`、`subtitle_unavailable`、`source_insufficient`、`failed` 和 `note_invalid` 都不是完成状态。

## 数据契约

- 新生成的 `job.json` 使用 `schema_version: 1`；finalizer 只接受该版本。
- collector 与 finalizer 的 JSON 响应包含 `schema_version: 1`、`status` 和可读 `message`（如适用）；智能体必须以 `status` 判断分支。
- Frontmatter 的 `author`、`published`、`duration`、`source`、tags 与 `cssclasses` 由程序生成，智能体不得自行改写；视频笔记固定使用 `learning-page + video-note` 以接入共享 Obsidian 视觉系统。
- `analysis.json` 是 runtime-only 质量报告，不进入最终 Obsidian 笔记。它用于记录来源充分性、知识清单和覆盖复核状态，不是给用户阅读的机器报告。

## 不可突破的数据边界

- 默认流程只采集 metadata、UP 主原始简介和 `ai-zh`/`zh.*` 的 SRT 字幕；不得下载音视频、启动 Chrome/CDP 或回退到 ASR。
- `confirmed_empty` 仅代表 info-json 明确给出空字符串且（如存在）简介 sidecar 与其一致；字段缺失、`null`、类型异常或两者不一致都必须失败。
- Cookie 内容不得读取、打印、上传、编辑、提交或写入笔记；collector 仅可把配置的 Cookie 文件路径传给 yt-dlp。
- 原始字幕、元数据、简介、`analysis.json`、日志和智能体临时工作文件只允许存在于 `.runtime/bilibili-learning` 的单个 job；finalizer 负责精确清理。
- 智能体只可编辑既定的 `analysis.json`、草稿中的两个 AI 区域，以及 `agent_work_dir` 内的临时辅助文件。原始 SRT 由核心预处理器转换为 `transcript-manifest.json` 与一个或多个 transcript chunk；转换只移除 SRT 序号、毫秒精度与空行，保留字幕文字、顺序和 cue 边界，不做摘要、关键词过滤或语义去重。智能体应优先按 manifest 读取这些 chunk；长字幕可在 `agent_work_dir` 继续创建逐块知识摘录、索引或中间梳理文件，再合并与复核。`agent_work_dir` 不得存放最终笔记或持久资料；其内容随 job 一并由 finalizer / failsafe 清理。
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

正文事实只能来自当前视频字幕和 UP 主原始简介；不得利用模型常识补全视频没有提供的具体参数、资源地址或结论。

对学习价值高的信息应优先保护，不能仅为了缩短篇幅而删除：

- 参数、数值、公式、数量和上下限；
- 模型、节点、插件、LoRA、格式、版本等专有名词；
- A/B 差异、适用条件和兼容性；
- 作者明确推荐、质量/速度/稳定性的取舍；
- 会改变结果的前提、例外、冲突和警告；
- 结构化方法、提示词公式、关键工作流；
- 视频明确提供且具有学习价值的资源地址。

这不是机械保留规则。广告价格、活动口播或与学习目标无关的数字是否保留，应由智能体根据长期参考价值判断。

长字幕或知识密集内容允许先按语义章节/时间段分段提取，再合并、去重和组织。不要把固定 Map-Reduce 流程强加给所有短视频。

## 最终笔记结构

程序负责：Frontmatter、H1、BVID、小型视频简介、UP 主资源、原始简介、iframe、tags、cssclasses、文件名和路径。UP 主资源标题由程序根据原始简介中的资源小节、原标签和 URL 平台规范化，例如 `GitHub 插件 · MieNodes`、`工作流（夸克网盘）`、`MiniMax H3 模型提示词指令（飞书）`；无法可靠判断类型时保留原标签，不凭 URL 猜测内容类型。正式阅读顺序由程序固定为：**标题 / BVID → 先看结论 → 播放器 → 动态知识正文 → 视频资料**。

智能体负责两个区域：

- `BILI_AI_SUMMARY`：短的“先看结论”，用于快速判断视频价值；
- `BILI_AI_BODY`：根据视频真实信息结构动态组织的知识正文。

正文不强制出现“怎么做 / 容易踩坑 / 我来实践”。需要时可以使用这些章节，不需要时应省略。章节名称、数量、长短、表格、列表和步骤形式由内容决定。

## 覆盖复核

程序可以检查结构和流程状态，但不能可靠判断“知识有没有漏”。因此成稿后必须由智能体完成语义复核。

至少检查：

- `knowledge_outline` 中的重要参数、限制、比较和方法是否已经进入正文；
- 比较关系是否只写了一边；
- 默认值后面的例外或限制是否被误删；
- 多个方案是否被错误合并；
- 是否为了简短而丢掉高价值具体信息；
- 是否出现字幕/简介没有支持的新事实。

复核通过后设置 `coverage_review.status = "passed"` 并简要记录复核结果。Finalizer 只验证该流程确实完成，不用确定性算法假装评估语义完整度。

## 笔记内容边界

必须阅读：

```text
docs\standards\CODEX-VIDEO-NOTE-GUIDE.md
docs\standards\STANDARD-VIDEO-NOTE-EXAMPLE.md
```

所有新笔记先进入 `00-待整理`。H1 默认使用 B站原视频标题，BVID 由程序写为 H1 下方的小字。允许重复链接再次生成笔记；同名文件由程序以 `（2）`、`（3）` 防覆盖。分类建议和 tags 由程序确定；智能体不得自行跳过 `00-待整理`。

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
