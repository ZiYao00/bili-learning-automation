# B站视频转笔记规范

本目录定义最终笔记的人类可读标准：

- `CODEX-VIDEO-NOTE-GUIDE.md`：内容质量与结构规则；
- `STANDARD-VIDEO-NOTE-EXAMPLE.md`：符合当前程序骨架的最终成品示例。

当前正式实现采用：

```text
程序确定性骨架
→ Hermes 只填写 AI 内容区域
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
- Frontmatter、H1、简介、iframe、tags、文件路径由程序负责；
- Hermes 只生成先看结论、怎么做、容易踩坑和实践清单；
- 文件名包含 BVID，H1 不包含 BVID；
- 主笔记不展示 runtime 路径、证据编号或抓取状态。
