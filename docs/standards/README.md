# B站视频转笔记规范

本目录提供两种写作模式：

- `LIGHT-WORKFLOW.md`：当前默认实验模式。完整读取字幕后直接写笔记，内容完成再做一次排版优化，尽量减少过程规则。
- `KNOWLEDGE-DENSE-WORKFLOW.md`：保留的严格模式。使用 Fact Ledger、Semantic Draft、Layout Pass 与阶段门禁。
- `CODEX-VIDEO-NOTE-GUIDE.md`：严格模式的详细内容质量与版式规则；文件名保留历史兼容。
- `STANDARD-VIDEO-NOTE-EXAMPLE.md`：局部 Markdown / Obsidian 表达片段，不是目录或组件模板。
- `../OBSIDIAN-STYLING.md`：共享 CSS 的安装与语义组件说明。

## 默认轻量流程

```text
程序准备 metadata / description / subtitles 与 runtime 草稿
→ Agent 按顺序完整读取 transcript
→ Agent 直接完成“先看结论 + 动态知识正文”
→ 内容完成后独立做一次版式优化
→ Agent 回看 transcript 做 coverage review
→ finalizer 校验确定性结构并原子发布
```

轻量模式不创建 `fact-ledger.md`、`semantic-draft.md` 或 `layout-plan.md`。

## 可选严格流程

```text
Source Assessment
→ Fact Ledger
→ knowledge_outline
→ Semantic Draft
→ Layout Pass
→ Source Recheck
→ finalizer
```

通过 `workflow_mode: strict` 或环境变量 `BILI_LEARNING_WORKFLOW_MODE=strict` 启用。

## 共同边界

- UP 主原始简介必须来自采集元数据，不能由 AI 改写或补造；
- Frontmatter、H1、BVID、简介、iframe、tags、cssclasses、阅读顺序和文件路径由程序负责；
- 来源不足时宁可停止，也不得依靠模型常识补齐具体事实；
- 内容不以固定章节数量或固定组件组合为目标；
- `analysis.json`、严格模式工作文件、`BILI_AI_*` marker、runtime 路径和采集状态不进入正式成品。
