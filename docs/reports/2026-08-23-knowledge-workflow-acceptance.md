# 知识密集型笔记工作流修复验收

日期：2026-08-23

## 背景

同一组视频回归测试表明：去除固定五段结构后，章节组织已经更自然，但 Agent 容易把“少章节”误解成“少内容”，在自然聚类时同步压缩参数、成员关系、安装前提和实测证据。随后使用完整字幕手工执行两轮工作，得到稳定高质量结果：

1. 先完整保全知识并形成内容稿；
2. 内容完成后再独立进行视觉排版。

本轮将该成功过程固化为正式工作流。

## 最终工作流

```text
Source Assessment
→ Fact Ledger
→ knowledge_outline
→ Semantic Draft
→ Layout Pass
→ Source Recheck
→ Final Note
```

关键原则：

- 知识选择与文章章节解耦；
- 内容成稿与视觉排版解耦；
- 章节数量只决定事实如何分组，不改变事实保留预算；
- Layout Pass 只转换表达形式，不承担第二次摘要；
- 最终复核必须回到 transcript，并对照 Fact Ledger、Semantic Draft 与最终正文。

## 实现范围

### Runtime 工作文件

collector 为新任务创建并返回：

- `fact-ledger.md`
- `semantic-draft.md`
- `layout-plan.md`

三份文件均位于当前 job 的 `agent_work_dir`，由 finalizer / failsafe 清理，不进入正式笔记。

### 阶段门禁

新任务发布前必须满足：

- Fact Ledger：知识密集型使用 `complete` 并至少填写一条完成的原子事实；短且简单的视频可使用 `not_applicable`，但必须填写原因；
- Semantic Draft：使用 `complete`，且内容稿不能是空模板或过短占位；
- Layout Plan：使用 `complete`，且至少存在一条完成的排版决定；
- 工作文件路径必须直接位于当前 `agent_work_dir`，文件名必须符合约定；
- 旧 job 没有新字段时保持兼容。

### 内容与排版规则

- Fact Ledger 保存成员、参数、版本、关系、条件、例外、冲突、作者评价和 `配置 → 耗时 / 质量 / 失败表现`；
- `knowledge_outline` 仅作为上层索引，不承担事实保全；
- Semantic Draft 先用普通 Markdown 完成知识正文；
- Layout Pass 根据真实关系选择 Table / Grid / Card / Chip / Metric / Risk / Meta 等组件；
- 整页只允许一个最高优先级 Summary；
- runtime 工作文件名、Fact ID 和内部状态不得泄漏到正式笔记。

## 未修改范围

本轮没有修改：

- 字幕切块阈值与 cue 处理；
- `analysis.json schema_version: 1`；
- yt-dlp、Cookie、Vault 或本机路径配置；
- `learning-lab.css` 与 `video-note.css`；
- 现有用户笔记；
- Git 提交与推送。

## 验证结果

```text
.venv/Scripts/python.exe -m pytest -q
66 passed

.venv/Scripts/python.exe -m ruff check src tests
All checks passed!
```

覆盖的新增回归包括：

- collector 创建并返回三份 runtime 工作文件；
- pending 阶段不能发布；
- 短简单视频可使用 `not_applicable + workflow_reason`；
- 完成工作流后 E2E 发布、重复转换、导航和 cleanup 正常；
- 多个 Summary 被拒绝；
- runtime 工作文件名泄漏到正式笔记会被拒绝；
- 去模板化规则、事实预算和 Layout Pass 文档约束不会回退。

## 后续验收建议

继续使用此前相同的三条视频进行真实回归。验收重点不是章节数量或文件 KB，而是：

1. 参数、成员、关系、安装前提和实测证据是否完整；
2. 三篇笔记的章节结构是否随视频内容自然变化；
3. Layout Pass 是否提升阅读体验而不减少事实；
4. 最终笔记是否保持一个 Summary、合理使用组件，并在关闭 CSS 后仍可读。
