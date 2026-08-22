# 架构说明

## 主链路

```text
已授权智能体入口中的复制链接 / BV 号 / 受支持短链
→ input_resolver 规范化 BVID 与 canonical URL
→ yt-dlp 仅采集元数据、UP 主简介、ai-zh/zh 字幕
→ taxonomy 生成 tags 与后续整理建议；原视频标题的新笔记进入 00-待整理
→ Python 在 runtime 写入确定性 Markdown 草稿与 analysis.json
→ Codex/Hermes 判断来源充分性并形成 knowledge_outline
→ 智能体填写“先看结论 + 动态知识正文”并完成 coverage review
→ finalizer 校验质量流程状态、真实元数据与结构后原子发布
→ navigation 原子刷新
→ 清理临时 job
```

## 代码分层

- `src/bili_learning/`：可测试的核心逻辑和 agent-neutral CLI（`prepare`、`finalize`、`organize`、`doctor`、`configure-obsidian`、`build-nav`）。
- `docs/AGENT-INTEGRATION.md`：所有智能体共用的接入协议。
- `hermes-skills/bili-learning-automation/SKILL.md`：Hermes/微信专属适配约束。
- `hermes-skills/bili-learning-automation/scripts/`：只定位项目根目录并转发到核心 CLI 的兼容入口。
- `config/bilibili-note-taxonomy.json`：模型别名、tags、后续整理建议和默认 `notes_root`。
- `docs/standards/`：人类可读的笔记质量与版式语义标准。
- `obsidian/snippets/`：随仓库提交、可直接安装到 Obsidian Vault 的 `learning-lab.css` Core 与 `video-note.css` Extension。
- `docs/OBSIDIAN-STYLING.md`：CSS 安装、作用域、升级同步和无样式降级规则。当前副本与 `ComfyUI-Learning-Lab` Design System v0.3 / Video Note v0.1 对齐，但运行时不依赖另一个本地仓库。

## 确定性边界

程序负责：

- canonical URL；
- H1 下方的 BVID 小字；
- Frontmatter；
- H1；
- 原始简介；
- iframe；
- tags；
- `learning-page + video-note` cssclasses；
- 阅读顺序（Summary → Player → AI Body → Source）；
- 输出路径；
- 导航。

taxonomy 的 route.path 不直接决定新文件的路径。新笔记统一先进入 fallback.path（默认 `00-待整理`）；route.path 仅随 job 保留为建议分类，并通过 tags 帮助 `organize` 在学习后归档。收集阶段 H1 直接使用原视频标题，不进行主题提炼。

接入智能体只负责字幕理解与语义内容：

- 判断字幕与简介是否足以支撑可信学习笔记；
- 形成 runtime `knowledge_outline`；
- 写短的“先看结论”；
- 根据视频真实信息结构组织动态知识正文；
- 成稿后完成覆盖复核。

章节、表格和步骤形式由内容决定；确定性骨架仍由程序控制，避免 LLM 重写元数据、简介或路径。

## 数据边界

- 长期产物：私人 Markdown 笔记与导航页，默认不入 Git。
- 临时产物：`.runtime/bilibili-learning`；成功、失败或 failsafe 后清理。
- 敏感数据：`key/` 中的 Cookie 文件；程序只把路径传给 yt-dlp，不读取内容。
- 历史资料：`archive/`、`materials/` 及本机 legacy 依赖，不属于公开源码主链路。

## 配置边界

正式用户推荐显式配置 `vault_root + notes_subdir`，由统一 settings loader 计算 `notes_root`；旧版 `notes_root` / `BILI_LEARNING_NOTES_ROOT` 保持兼容。taxonomy 的 `notes/bilibili` 只作为临时 repository fallback；未显式配置时，新采集返回 `configuration_required`，但已有 job 的 finalizer / cleanup 仍可继续。collector、finalizer、navigation 与 doctor 共用同一 settings loader。

## 可靠性原则

- 文件名使用原视频标题，同名时在预约锁保护下使用递增序号，避免覆盖。已完成视频允许再次转换并生成新笔记。
- 同一 BVID 仅在活动 collector、智能体写作与 finalizer 期间使用 reservation 防止并发；任务结束后释放 reservation，允许再次转换。残留 reservation 超过 1 小时且对应 job 不再活动时可自动恢复。
- Finalizer 校验真实值，而非仅检查字段名；无效草稿不会进入笔记库，随 runtime job 一起清理。草稿的 `BILI_AI_*` marker 只用于校验，发布时会移除，因此正式 Obsidian 笔记不含机器标记。
- 导航采用临时文件后原子替换。
- 不同 BVID 可并行处理；导航重建使用独占锁串行执行，避免多个 finalizer 交叉覆盖同一组导航页。当前不会自动删除旧导航页，以免误删用户手写内容。
- 外部 yt-dlp 调用有超时。
- cleanup 只允许作用于 runtime root 的子目录，并且不把 `locks/` 当作 job 清理。
- `organize` 只接收 notes root 内的现有 Markdown；它先原子创建目标文件，确认成功后才删除旧位置，再重建导航。
