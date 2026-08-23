# 轻量笔记工作流

适用于 `job.json` 中：

```json
"workflow_mode": "light"
```

目标很简单：**完整读字幕，写成真正有用的学习笔记，再单独做一次排版优化。**

## 执行顺序

1. 按 `transcript-manifest.json` 的顺序完整读取全部 transcript chunk。
2. 判断字幕与 UP 主简介是否足以支撑可信笔记；不足时停止，不凭常识补具体事实。
3. 直接写完整笔记，不先填写 Fact Ledger、Semantic Draft 或 Layout Plan。
4. 内容写完后，再独立做一次版式优化。
5. 最后回看字幕，修正明显遗漏和无来源内容，再完成 coverage review。

## 写作目标

把视频转成一篇适合长期学习、检索和实际操作的 Obsidian 笔记。

优先保留真正有用的信息，例如：

- 参数、数值、数量、上限和下限；
- 工具、模型、节点、插件、版本和资源；
- 操作步骤、前置条件、适用场景和兼容性；
- A/B 差异、作者明确建议和取舍；
- 配置、耗时、质量变化和失败表现等实测结果。

不要预设章节数量，也不要为了“简洁”主动压缩有长期参考价值的内容。章节、表格和列表由当前视频的信息关系自然决定。

## 排版

先确保内容完整，再考虑视觉表达。只有进入这一阶段后，才可按需读取 `docs/OBSIDIAN-STYLING.md`；需要确认某个组件的 Markdown 写法时，只查看 `STANDARD-VIDEO-NOTE-EXAMPLE.md` 中相关的局部片段，不读取严格工作流来重新规划正文。

可以按需要使用：

- 普通段落、列表和步骤；
- Markdown 表格；
- Grid / Card；
- Risk / Meta / Resource；
- Chip / Metric。

没有任何组件是必需的。只有内容关系确实适合时才使用；不要为了美化而删减、改写或重复知识。关闭 CSS 后仍应可读。

## 只保留这些硬边界

- 正文事实只来自当前字幕和 UP 主简介；
- 不修改程序生成的 Frontmatter、H1、元信息、播放器、来源区、资源链接、文件名、路径、tags、cssclasses 和 marker；
- 不覆盖已有笔记；
- 不把 Cookie、runtime 路径、日志或内部状态写进正式笔记；
- 最终仍由 finalizer 校验、发布并清理临时任务。

轻量模式不要求读取或执行 `KNOWLEDGE-DENSE-WORKFLOW.md`，除非用户明确要求切换到 `strict` 模式。
