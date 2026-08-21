# B站视频转笔记规范

本目录定义最终笔记的人类可读标准：

- `CODEX-VIDEO-NOTE-GUIDE.md`：内容质量与结构规则；
- `STANDARD-VIDEO-NOTE-EXAMPLE.md`：符合当前程序骨架的最终成品示例。

当前正式实现采用：

```text
程序确定性骨架
→ 接入智能体只填写 AI 内容区域
→ finalizer 强校验
```

因此优先级为：

```text
validator / schema
> SKILL.md
> CODEX-VIDEO-NOTE-GUIDE.md
> STANDARD-VIDEO-NOTE-EXAMPLE.md
```

最重要的边界：

- UP 主原始简介必须来自采集元数据，不能由 AI 改写或补造；
- Frontmatter、H1、简介、iframe、tags、文件路径由程序负责；新笔记一律先进入 `00-待整理`，模型/主题目录只是学习后的人工整理位置；
- 接入智能体只生成先看结论、怎么做、容易踩坑和实践清单；
- 文件名包含 BVID，H1 不包含 BVID；
- 主笔记不展示 runtime 路径、证据编号或抓取状态。
- `BILI_AI_*` marker 仅用于 runtime 草稿校验，正式成品中不展示。
