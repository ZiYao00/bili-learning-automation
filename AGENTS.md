# B站视频转笔记

生成或修改 `notes\bilibili` 中的笔记前，必须先阅读：

- `docs\standards\CODEX-VIDEO-NOTE-GUIDE.md`
- `docs\standards\STANDARD-VIDEO-NOTE-EXAMPLE.md`
- `config\bilibili-note-taxonomy.json`

当前正式流程采用“程序确定性骨架 + 智能体 AI 内容区域”：

- Python 负责 Frontmatter、H1、UP 主原始简介、iframe、tags、文件路径和 BVID 唯一文件名；
- Agent 只填写 `BILI_AI_*_START/END` 标记之间的先看结论、怎么做、容易踩坑和实践清单；
- 不得重写或移动程序生成的确定性内容；
- 视频简介抓取失败不能当作视频无简介；
- 机器资料只可临时保留在 `.runtime`，不写入主阅读页面或长期归档；
- 完成状态以 finalizer 返回 `note_ready` 为准。

本机 Hermes 运维说明可在仓库外单独维护；它不是项目运行或其他智能体执行的前置条件。
