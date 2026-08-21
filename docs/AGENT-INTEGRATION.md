# 智能体接入协议

本协议适用于 Hermes、Codex 和未来接入本项目的其他智能体。核心脚本、taxonomy、笔记标准与 finalizer 是唯一事实来源；适配层只能处理各平台的消息入口、权限判断和最终回复。

## 输入与授权

- 只接受可解析的 Bilibili 复制链接、受支持短链接或 BV 号。
- 无法解析 BV 号时要求用户重新发送“复制链接”，不得猜测。
- 适配层必须确认调用者已获授权；Hermes 的额外规则是只接受 owner 私聊。

## 必须执行的流程

1. 把原始收到的文本交给 collector。
2. 仅当 collector 返回 `materials_ready` 时，读取 handoff、job、字幕和项目标准。
3. 只在 `draft_path` 的程序生成 `BILI_AI_*_START/END` 标记内填写 AI 内容；`note_path` 是只读的最终发布位置。marker 仅存在于 runtime 草稿，finalizer 发布时会移除。
4. 无论写作成功、失败或中断，都必须立即运行 finalizer。
5. 仅在 finalizer 返回 `note_ready` 后报告完成。

`already_exists`、`in_progress`、`incomplete_note`（仅旧版遗留骨架）、`subtitle_unavailable`、`failed` 和 `note_invalid` 都不是完成状态，必须返回简短真实说明，不得继续伪造笔记或声称成功。

## 数据契约

- 新生成的 `job.json` 使用 `schema_version: 1`；finalizer 只接受该版本。
- 当前 collector 与 finalizer 的 JSON 响应都包含 `schema_version: 1`、`status` 和可读 `message`（如适用）。智能体应以 `status` 判断分支，不能从自然语言猜状态。
- Frontmatter 的 `author`、`published`、`duration`、`source` 和 tags 由程序采用 JSON 风格双引号编码；这是 YAML 的无歧义子集。智能体不得自行改写这些字段。

## 不可突破的数据边界

- 默认流程只采集 metadata、UP 主原始简介和 `ai-zh`/`zh.*` 的 SRT 字幕；不得下载音视频、启动 Chrome/CDP 或回退到 ASR。
- `confirmed_empty` 仅代表 info-json 明确给出空字符串且（如存在）简介 sidecar 与其一致；字段缺失、`null`、类型异常或两者不一致都必须失败，不能写成“没有简介”。
- Cookie 内容不得读取、打印、上传、编辑、提交或写入笔记；collector 仅可把配置的 Cookie 文件路径传给 yt-dlp。
- 原始字幕、元数据、简介和日志只允许存在于 `.runtime/bilibili-learning` 的单个 job；finalizer 负责精确清理。
- 不得覆盖已有笔记；同 BVID 的 reservation 从 collector 持续到 finalizer 或清理完成。草稿只存在于 runtime，只有 finalizer 校验通过后才会原子发布到 `note_path`。文件名、tags、Frontmatter、H1、简介、iframe 和输出路径由程序决定；所有新笔记先发布到 `00-待整理`。同名文件使用序号防覆盖。

## 笔记内容边界

必须阅读：

```text
docs\standards\CODEX-VIDEO-NOTE-GUIDE.md
docs\standards\STANDARD-VIDEO-NOTE-EXAMPLE.md
```

taxonomy 已由程序用于确定 tags 和后续整理建议；新笔记的 H1 默认使用 B站原视频标题，BVID 由程序写为 H1 下方的小字。简介由程序写成简要说明、UP 主资源链接和可折叠的原始简介。所有新笔记先进入 `00-待整理`，不得由智能体自行改放模型目录。AI 内容只能基于字幕或 UP 主原始简介；不得暴露 runtime 路径、job 文件名、证据编号或采集状态。

## 学习后整理流程

只有用户明确要求“整理笔记”后，智能体才可调用统一核心入口。该操作把短标题、视频简介的一句摘要和归档目录合并为一次用户触发的整理动作；不要在收集阶段自动执行。

```powershell
bili-learning organize --note '<现有笔记路径>' --title '<学习后短标题>' --intro '<一句简介摘要>'
```

- `--title` 与 `--intro` 只能基于现有笔记、UP 主简介和用户的学习判断；不得捏造参数或资源。
- 省略 `--category` 时，核心按现有 tags 推断 taxonomy 建议目录；需要时才传入项目内相对目录，例如 `01-视频生成/01-MiniMax-H3`。
- 核心原子创建新文件、确认成功后才删除旧位置，并重建导航；适配层不得自行移动或重命名文件。

## 适配层边界

- Hermes 适配层：微信私聊授权、链接接收、Hermes 安装和回复格式。
- Codex 当前直接在项目目录中读取 `AGENTS.md` 与本协议，不安装独立 skill。
- 其他平台只新增薄适配层；不得复制核心 Python 逻辑、另建 taxonomy 或绕过 finalizer。
