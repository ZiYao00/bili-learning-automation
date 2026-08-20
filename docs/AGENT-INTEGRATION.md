# 智能体接入协议

本协议适用于 Hermes、Codex 和未来接入本项目的其他智能体。核心脚本、taxonomy、笔记标准与 finalizer 是唯一事实来源；适配层只能处理各平台的消息入口、权限判断和最终回复。

## 输入与授权

- 只接受可解析的 Bilibili 复制链接、受支持短链接或 BV 号。
- 无法解析 BV 号时要求用户重新发送“复制链接”，不得猜测。
- 适配层必须确认调用者已获授权；Hermes 的额外规则是只接受 owner 私聊。

## 必须执行的流程

1. 把原始收到的文本交给 collector。
2. 仅当 collector 返回 `materials_ready` 时，读取 handoff、job、字幕和项目标准。
3. 只在程序生成的 `BILI_AI_*_START/END` 标记内填写 AI 内容。
4. 无论写作成功、失败或中断，都必须立即运行 finalizer。
5. 仅在 finalizer 返回 `note_ready` 后报告完成。

`already_exists`、`incomplete_note`、`subtitle_unavailable`、`failed` 和 `note_invalid` 都不是完成状态，必须返回简短真实说明，不得继续伪造笔记或声称成功。

## 不可突破的数据边界

- 默认流程只采集 metadata、UP 主原始简介和 `ai-zh`/`zh.*` 字幕；不得下载音视频、启动 Chrome/CDP 或回退到 ASR。
- Cookie 内容不得读取、打印、上传、编辑、提交或写入笔记；collector 仅可把配置的 Cookie 文件路径传给 yt-dlp。
- 原始字幕、元数据、简介和日志只允许存在于 `.runtime/bilibili-learning` 的单个 job；finalizer 负责精确清理。
- 不得覆盖已有笔记；文件名、分类、tags、Frontmatter、H1、简介、iframe 和输出路径由程序决定。

## 笔记内容边界

必须阅读：

```text
docs\standards\CODEX-VIDEO-NOTE-GUIDE.md
docs\standards\STANDARD-VIDEO-NOTE-EXAMPLE.md
config\bilibili-note-taxonomy.json
```

AI 内容只能基于字幕或 UP 主原始简介；不得暴露 runtime 路径、job 文件名、证据编号或采集状态。

## 适配层边界

- Hermes 适配层：微信私聊授权、链接接收、Hermes 安装和回复格式。
- Codex 当前直接在项目目录中读取 `AGENTS.md` 与本协议，不安装独立 skill。
- 其他平台只新增薄适配层；不得复制核心 Python 逻辑、另建 taxonomy 或绕过 finalizer。
