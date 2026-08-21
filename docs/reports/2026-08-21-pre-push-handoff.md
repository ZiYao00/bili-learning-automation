# 2026-08-21 · 本轮提交与推送交接

## 目标

把当前 `bili-learning-automation` 的“高质量知识提取 + 动态笔记结构 + Obsidian Design System”升级作为一个完整变更提交并推送。

当前工作分支：

```text
feat/inbox-organize-flow
```

本交接只针对：

```text
G:\GitHub\bili-learning-automation
```

`G:\GitHub\ComfyUI-Learning-Lab` 是另一个独立仓库，即使它当前也有未提交变化，也不要混入本次 commit / push。

## 本轮应形成的完整能力

### 内容质量

- 固定四段式 AI 模板升级为 `BILI_AI_SUMMARY + BILI_AI_BODY`；
- Agent 先做来源充分性判断，再建立 `knowledge_outline`；
- 成稿后完成 `coverage_review`；
- 来源不足时返回 `source_insufficient`，不发布低质量正式笔记；
- H3 百科视频作为知识密集型回归样本；
- 保护参数、公式、限制、专名、比较、明确推荐、具体方案成员，以及“原则 + 可直接使用值”。

### 笔记结构与版式

- 新笔记自动使用：

```yaml
cssclasses:
  - learning-page
  - video-note
```

- 正式阅读顺序为：

```text
标题 / BVID
→ 先看结论
→ 播放器
→ 动态知识正文
→ 视频资料
```

- Agent 根据知识关系选择 Table / Grid / Card / Chip / Risk / Resource，不为视觉效果机械卡片化。

### 项目自带 Obsidian CSS

当前仓库必须提交：

```text
obsidian/snippets/learning-lab.css
obsidian/snippets/video-note.css
```

当前同步版本：

```text
Learning Lab Core v0.3
Video Note Extension v0.1
```

普通用户不再需要访问另一个仓库获取 CSS。README 与 `docs/OBSIDIAN-STYLING.md` 已提供安装、升级与故障排查教程。

## 提交前必须复核

先查看完整 diff，确认当前工作区的所有变更都属于本轮及前一轮已经确认的升级，不要为了“清理工作区”回退尚未提交但已经完成的核心改造。

必须排除：

- `key/` Cookie；
- `.runtime/`；
- 私人 `notes/`；
- 本机测试抓取材料；
- 本机绝对路径配置；
- 任何临时日志、缓存或凭据。

执行项目正式验证：

```powershell
python -m compileall -q src hermes-skills/bilibili-learning/scripts
python -m ruff check .
python -m pytest -q
git diff --check
```

如果测试失败，应先判断是代码回归、测试预期未同步还是本机环境缺依赖；不要在失败状态下直接推送。

## 重点验收

- 新建任务的 Frontmatter 自动包含 `learning-page` 与 `video-note`；
- Validator 允许未来追加其它 cssclasses，但必需的两个 class 不能缺失；
- `source_insufficient` 不发布正式笔记；
- `coverage_review` 未完成时 Finalizer 拒绝发布；
- `organize` 同时兼容新 `### 视频简介` 与旧 `## 视频简介`；
- 正式笔记不包含 runtime marker / `analysis.json` / 内部路径；
- 两份 CSS 已被 Git 跟踪，并且 `video-note.css` 的 Core 依赖版本与 `learning-lab.css` 一致；
- README、CHANGELOG、Architecture、Development、Troubleshooting、Obsidian Styling 与实际实现一致。

## 提交语义

本轮属于功能升级而不是单纯文档更新。建议 commit message 使用类似：

```text
feat: improve video note quality and Obsidian styling
```

默认保持当前分支历史并推送 `feat/inbox-organize-flow`；不要自行重写历史、强推、合并到 `main` 或操作 `ComfyUI-Learning-Lab`，除非用户另有明确要求。
