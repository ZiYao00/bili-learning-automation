# B站视频转笔记：成品示例

本文件展示的是内容质量和结构自由度，不是要求所有视频复制同一套章节。

## 示例 A：短操作教程

```md
---
author: "示例UP主"
published: "2026-08-11"
duration: "07:05"
source: "https://www.bilibili.com/video/BV1EXAMPLE01/"
tags:
  - "视频生成"
  - "工作流"
  - "MiniMax-H3"
cssclasses:
  - "learning-page"
  - "video-note"
---

# H3 分段工作流：连续片段生成

<small class="video-note-meta">示例UP主 · 2026-08-11 · 07:05 · BV1EXAMPLE01</small>

> [!summary] 先看结论
> 这段视频讲如何把受单段时长限制的视频拆成连续片段生成；关键是让上一段末帧参与下一段生成，并在扩大总时长前先验证两段之间的主体与动作衔接。

## 怎么做

1. 根据目标总时长拆分片段。
2. 为每个片段准备对应提示词。
3. 第一段使用初始参考图。
4. 后续片段以上一段末帧作为连续性参考。
5. 检查输出片段后再决定是否继续增加总时长。

## 容易踩坑

- **主体在后续片段发生明显变化** → 检查上一段末帧是否正确作为下一段参考。

## 视频资料

### 原视频

<iframe ...></iframe>

### 资料获取方式

> [!resource] UP 主提供的附加资料
> **资料**：提示词模板
> **获取条件 / 方式**：三连
> **来源**：字幕
> **原始说明**：三连后可领取本期提示词模板。
>
> 当前采集内容未包含该资料本体，本笔记不自行补写。

### UP 主资源

- [GitHub 插件 · 示例节点](https://github.com/example/example-node)
- [工作流（夸克网盘）](https://pan.quark.cn/s/example)
- [模型提示词指令（飞书）](https://example.feishu.cn/wiki/example)

### 视频简介

本示例用于展示程序保留并压缩展示 UP 主原始简介。

<details class="video-note-source-details">
<summary>UP 主原始简介</summary>

原始简介内容……

</details>
```

这里使用“怎么做 / 容易踩坑”是因为视频本身是操作教程，不代表它们是固定章节。播放器和来源资料放在正文之后，避免占据首屏；“资料获取方式 / UP 主资源 / 视频简介”只有在来源中实际存在对应信息时才出现。

## 示例 B：知识密集型模型百科

```md
> [!summary] 先看结论
> 这类视频的价值不在单一操作步骤，而在模型规格、输入方式、提示词、加速方案和兼容性之间的系统关系。正文应保留可复查的参数、限制、方案差异与作者明确建议。

## 01 · 核心规格

| 项目 | 视频给出的信息 |
| --- | --- |
| 推荐分辨率 | 原则 + 典型可直接使用值 |
| 帧数规则 | …… |
| 建议时长 | …… |

## 02 · 两种模型路线

> [!grid-2]
>
> > [!card] FL2VA
> > **适合**：……
> >
> > **限制 / 特点**：……
>
> > [!card] Ref2VA
> > **适合**：……
> >
> > **限制 / 特点**：……

## 03 · 输入与提示词

| 输入 | 能力 | 数量 / 时长限制 | 关键区别 |
| --- | --- | --- | --- |
| 文本 | …… | …… | …… |
| 图片 | …… | …… | …… |
| 视频 | …… | …… | …… |
| 音频 | …… | …… | …… |

## 04 · 三条加速路线

> [!grid-3]
>
> > [!card] Attention
> > SageAttention · Sol-Attn
>
> > [!card] Turbo / LoRA
> > larryvrh · drbaph · Abiray · LightX2V
>
> > [!card] Cache / Prediction
> > 适合后测，注意稳定性与质量损失。

<div class="ll-chip-row">
  <span class="ll-chip">EasyCache</span>
  <span class="ll-chip">LazyCache</span>
  <span class="ll-chip">TeaCache</span>
  <span class="ll-chip">MagCache</span>
  <span class="ll-chip">FirstBlockCache</span>
  <span class="ll-chip">Spectrum</span>
</div>

> [!risk] 兼容性
> 互斥、冲突、画质损失等真正影响选择的条件在这里单独强调。

## 05 · 提示词结构

……

> [!resource]- 当前章节的关键资源
> 只在正文确实需要时引用相关 GitHub / 模型 / 工作流入口；程序已在文末保留完整 UP 主资源，不重复抄整份清单。

## 视频资料

### 原视频

<iframe ...></iframe>
```

这里没有强制“我来实践”，因为视频核心是知识百科。章节数量、表格和分组都由实际字幕决定。

## 质量判断

无论采用哪种结构，都必须满足：

- 事实只来自当前字幕与 UP 主原始简介；
- 高价值参数、限制、比较、专名、兼容性和重要资源不能因为追求简短而丢失；
- 如果来源只说明“三连 / 充电 / 评论关键词”等条件后可领取资料，只记录获取条件与来源原话；资料本体未采集到时不得由智能体补写；
- 不确定的信息宁可省略或判定来源不足，不得用模型常识补全；
- 成稿后完成覆盖复核；
- runtime 的 `analysis.json`、marker、内部路径和采集状态不进入正式笔记。
