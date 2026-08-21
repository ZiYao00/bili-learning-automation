# B站视频转笔记规范

本目录定义最终笔记的人类可读标准：

- `CODEX-VIDEO-NOTE-GUIDE.md`：Codex 与 Hermes 共用的内容质量、来源充分性、动态结构、版式决策和覆盖复核规则；文件名保留历史兼容，内容不是 Codex 专属。
- `STANDARD-VIDEO-NOTE-EXAMPLE.md`：短操作教程与知识密集型视频的结构/视觉示例；示例不是固定模板。
- `../OBSIDIAN-STYLING.md`：共享 `learning-lab.css` 与 `video-note.css` 的安装和职责边界。

当前正式实现采用：

```text
程序准备 metadata / description / subtitles 与 runtime 草稿
→ Agent 判断来源充分性并形成 knowledge_outline
→ Agent 填写“先看结论 + 动态知识正文”
→ Agent 做 coverage review
→ finalizer 校验流程状态和确定性结构
→ 原子发布正式笔记
```

责任优先级不是“Validator 决定内容质量”。

- 程序负责可确定验证的结构、路径、元数据、发布和清理；
- Agent 负责字幕理解、信息取舍、动态组织和语义覆盖复核；
- 共享标准约束质量底线，但不要用固定章节代替 Agent 思考。

最重要的边界：

- UP 主原始简介必须来自采集元数据，不能由 AI 改写或补造；
- Frontmatter、H1、BVID、简介、iframe、tags、cssclasses、阅读顺序和文件路径由程序负责；新笔记一律先进入 `00-待整理`；
- 来源不足时宁可拒绝生成正式学习笔记，也不得依靠模型常识补齐画面或字幕缺失的信息；
- 参数、公式、限制、专名、比较、兼容性、明确推荐和重要资源等高价值知识不能仅为缩短篇幅而删除；
- `analysis.json`、`BILI_AI_*` marker、runtime 路径和采集状态只存在于临时任务，不进入正式成品。
