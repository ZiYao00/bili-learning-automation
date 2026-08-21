# B站视频转笔记

本项目当前优先服务 Codex 与 Hermes。两者共用同一套核心脚本、字幕采集、内容标准、质量门禁、taxonomy 和 finalizer；不要为不同入口复制内容分析规则。

生成或修改 `notes\bilibili` 中的笔记前，必须先阅读：

- `docs\AGENT-INTEGRATION.md`
- `docs\standards\CODEX-VIDEO-NOTE-GUIDE.md`
- `docs\standards\STANDARD-VIDEO-NOTE-EXAMPLE.md`
- `docs\OBSIDIAN-STYLING.md`

当前正式流程采用“runtime 草稿 + Agent 内容分析 + finalizer 原子发布”：

- Python 负责 Frontmatter、H1、BVID、小型视频简介、UP 主原始简介、iframe、tags、`learning-page + video-note` cssclasses、文件路径、文件名、runtime marker 与质量报告骨架；
- Agent 先判断字幕与简介是否足以支撑可信学习笔记，再建立运行时知识清单；来源不足时宁可停止，不得根据常识补全；
- Agent 只填写 `BILI_AI_SUMMARY` 与 `BILI_AI_BODY`：前者用于速读，后者根据视频真实内容动态组织，不强制套用“怎么做 / 容易踩坑 / 我来实践”；
- 参数、公式、数量/上下限、专有名词、A/B 差异、兼容性、作者明确推荐、重要资源等高价值信息，不得仅为了缩短篇幅而删除；
- 成稿后必须重新对照字幕或运行时知识清单做覆盖复核；程序验证流程状态和确定性结构，语义质量由 Agent 负责；
- 视频简介抓取失败不能当作视频无简介；机器资料只可临时保留在 `.runtime`；
- 只有 finalizer 返回 `note_ready` 才能声称完成。

Hermes `SKILL.md` 只是 Hermes/微信入口适配层。Codex 在仓库内直接遵循本文件与共享协议。未来其他智能体只增加薄适配层，不应改变共享核心规则。

准备提交 / 推送当前这轮内容质量与 Obsidian 版式升级时，先阅读 `docs/reports/2026-08-21-pre-push-handoff.md`，按其中的范围、安全边界和验收项复核；不要把 `ComfyUI-Learning-Lab` 的独立工作区混入本仓库提交。
