# 知识密集型视频：保全、成稿与排版工作流

> 本文件只用于 `workflow_mode: strict`。默认 `light` 模式不要加载或执行本流程。

本文件用于长字幕、百科型、参数密集、实测案例多，或包含大量模型 / 插件 / 版本 / 配置关系的视频。是否启用不能只看时长：短视频也可能高度密集，长视频也可能只有一个简单观点。

核心目标不是生成更长的文章，而是避免在“读字幕 → 列主题 → 写正文”的过程中提前丢掉可长期复查的知识。

## 总流程

```text
Source Assessment
→ Fact Ledger
→ knowledge_outline
→ Semantic Draft
→ Layout Pass
→ Source Recheck
→ Final Note
```

这几个阶段解决不同问题：

- **Fact Ledger** 决定哪些具体事实需要保留；
- **knowledge_outline** 只给覆盖复核提供上层索引；
- **Semantic Draft** 决定事实如何自然成文；
- **Layout Pass** 决定完整内容如何更易读；
- **Source Recheck** 回到 transcript 检查遗漏和新增事实。

不得把这些阶段合并成一次“边读、边概括、边排版”的写作。

## 运行时工作文件

collector 会在 `agent_work_dir` 创建：

```text
fact-ledger.md
semantic-draft.md
layout-plan.md
```

它们都是 runtime-only 文件，随 job 由 finalizer / failsafe 清理，不进入正式 Obsidian 笔记。

### 阶段完成标记

三份文件的 Frontmatter 都包含 `workflow_status: pending`。新任务在 finalizer 前必须完成这些状态：

| 文件 | 允许状态 | 完成要求 |
| --- | --- | --- |
| `fact-ledger.md` | `complete` / `not_applicable` | 知识密集型内容使用 `complete` 并填写至少一条完成的原子事实；短且简单的视频可使用 `not_applicable`，但必须填写 `workflow_reason`。 |
| `semantic-draft.md` | `complete` | `## 内容稿` 下必须存在完整内容稿。 |
| `layout-plan.md` | `complete` | 至少填写一条排版决定；选择普通标题、段落或列表同样属于有效 Layout Pass。 |

finalizer 只检查阶段是否真正执行、文件是否仍是空模板以及路径是否位于当前 `agent_work_dir`；它不会假装用程序判断语义是否优秀。旧 job 不含这些字段时保持兼容。

### `fact-ledger.md`

按 manifest 顺序阅读 transcript，并记录原子事实。原子事实至少应覆盖视频实际出现的：

- 具体成员、专有名词和版本；
- 参数、公式、数量、上限、下限和可直接使用值；
- A/B 差异、来源 / 继承关系、兼容性和适用条件；
- 默认值后面的例外、冲突、失败模式和警告；
- 运行入口、安装前提和关键组件职责；
- 作者明确推荐、偏好与质量 / 速度 / 稳定性取舍；
- 可复用的 `配置 → 耗时 → 质量变化 / 失败表现` 证据链。

以下不是合格的原子事实：

```text
模型选择
提示词
加速方案
注意兼容性
还有一些 LoRA
```

它们只是主题标签，不能承担事实保全。

Fact Ledger 阶段不决定最终 H2 数量，也不为了文章简洁删除事实。来源无法确认的术语应保留不确定性，不得用模型常识静默修正。

## `knowledge_outline` 的正确定位

`knowledge_outline` 是 Fact Ledger 的上层索引，不是 Fact Ledger 的替代品，也不是最终目录。

正确关系：

```text
Fact Ledger
→ knowledge_outline
→ Semantic Draft
```

错误关系：

```text
字幕
→ 几个主题名
→ 每个主题写一段概括
```

一个 outline 条目可以覆盖多个原子事实；多个 outline 条目也可以在最终正文中合并到同一个自然章节。章节数量只改变事实的分组方式，不改变事实保留预算。

## `semantic-draft.md`

Semantic Draft 是内容完成稿，不是最终视觉稿。先使用普通 Markdown 把知识写完整，再考虑 Learning Lab 组件。

允许使用：

- 自然形成的 H2 / H3；
- 段落、列表和步骤；
- 具有固定比较字段的普通 Markdown 表格；
- 必要的 Risk / Meta 语义提醒。

这一阶段不应为了“看起来高级”加入大量 Grid、Card、Badge、Metric 或 Chip。

Semantic Draft 必须满足：

- 一个 H2 可以通过 H3、表格和列表承载大量事实；
- 减少章节不能同步减少参数、成员、关系和实测证据；
- 合并表达时仍能复查“为什么更快 / 更慢、更稳 / 更软、能否兼容”；
- `knowledge_outline` 中的主题不能只剩一句泛化结论；
- 不以文章字数或文件 KB 作为完成标准。

## `layout-plan.md` 与 Layout Pass

只有 Semantic Draft 内容完成后，才进入 Layout Pass。

Layout Pass 的职责是：

> 把已经完整的内容转换为更适合阅读的表达形式。

它不能承担：

- 第二次摘要；
- 重新选择哪些事实值得保留；
- 为了卡片数量或页面整齐删减信息；
- 从外部知识补写缺失内容。

内容关系与组件的常用映射：

| 内容关系 | 优先表达 |
| --- | --- |
| 2 个需要直接比较的核心对象 | `grid-2 + card` 或对比表 |
| 3 个平级入口 / 路线 / 模式 | `grid-3 + card` |
| 4 个以上对象或多字段实测 | Table |
| 一组名称需要保留检索，但不逐个展开 | Chip |
| 参数基线、时长、帧数等少量关键指标 | Metric / Card |
| 冲突、互斥、兼容性、失败模式 | Risk |
| 来源损坏、术语不确定、验证边界 | Meta |
| 不存在明显并列或比较关系 | 普通标题、段落和列表 |

整页只保留一个最高优先级 Summary。不要为了“组件丰富”重复表达同一事实，也不要把所有内容卡片化。

## Source Recheck

最终正文和排版完成后，必须重新按 manifest 顺序抽查或复读 transcript。不能只检查 Fact Ledger、outline 或自己刚写完的正文。

至少复核：

- Fact Ledger 中的高价值事实是否进入最终正文；
- 原则是否同时保留视频给出的典型可直接使用值；
- 同类成员是否保留了来源、步数、兼容性和作者评价；
- 默认值、推荐区间后面的例外是否还在；
- 实测是否保留条件、耗时和结果，而不是只剩“速度与质量需要权衡”；
- Layout Pass 前后的事实是否一一对应；
- 正文是否新增字幕和简介没有支持的具体事实。

对于决定省略的高价值候选，必须能说明原因，例如纯广告价格、重复口播、来源损坏到无法确认，或与学习目标无关；“为了简洁”不是充分理由。

## 常见失败模式

### 主题正确，知识丢失

```text
加速方案：注意力、LoRA、缓存各有取舍。
```

这句话方向正确，但如果来源明确给出具体成员、兼容关系、推荐步数、耗时和失败表现，就不能作为完整正文。

### 少章节被误解为短笔记

一篇 38 分钟百科可以自然形成 4 个 H2，也可以形成 6 个 H2。判断标准是语义关系，不是目标数字；无论章节多少，都应保留同等事实预算。

### 排版阶段再次摘要

把完整实测表改成三张只有“快 / 中 / 稳”的卡片，会丢掉配置和结果链。正确做法是保留实测表，并只对真正平级的路线做卡片化。

### 从示例复制目录或组件组合

示例只展示局部表达。不得因为示例使用 `grid-3 + metric + table`，就要求下一篇笔记也出现相同组件集合。

## 完成标准

知识密集型视频的完成标准不是篇幅，而是：

1. 来源足以支撑正文；
2. Fact Ledger 保留了可长期查阅的具体事实和关系；
3. Semantic Draft 在排版前已经内容完整；
4. Layout Pass 只改变表达形式，没有删除事实；
5. Source Recheck 回到原 transcript 并修正遗漏；
6. 最终笔记保持一个 Summary、动态章节结构和可关闭 CSS 后仍可读的 Markdown。
