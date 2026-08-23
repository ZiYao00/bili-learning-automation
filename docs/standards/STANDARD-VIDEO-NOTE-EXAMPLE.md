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

<iframe class="video-note-player" src="https://player.bilibili.com/player.html?bvid=BV1EXAMPLE01&autoplay=0&danmaku=0" allowfullscreen></iframe>

**资料获取**

> [!resource] 提示词模板 · 三连
> 来源：字幕；当前采集内容未包含该资料本体，本笔记不自行补写。
> <small>原始说明：三连后可领取本期提示词模板。</small>

### UP 主资源

- [GitHub 插件 · 示例节点](https://github.com/example/example-node)
- [工作流（夸克网盘）](https://pan.quark.cn/s/example)
- [模型提示词指令（飞书）](https://example.feishu.cn/wiki/example)

<p class="video-note-overview"><strong>视频简介</strong>：本示例用于展示程序保留并压缩展示 UP 主原始简介。</p>

<details class="video-note-source-details">
<summary>UP 主原文（完整说明与链接）</summary>

原始简介内容……

</details>

## 怎么做

1. 根据目标总时长拆分片段。
2. 为每个片段准备对应提示词。
3. 第一段使用初始参考图。
4. 后续片段以上一段末帧作为连续性参考。
5. 检查输出片段后再决定是否继续增加总时长。

## 容易踩坑

- **主体在后续片段发生明显变化** → 检查上一段末帧是否正确作为下一段参考。
```

这里使用“怎么做 / 容易踩坑”是因为视频本身是操作教程，不代表它们是固定章节。来源入口放在“先看结论”后、正文前；播放器不再使用额外“视频资料”标题。资料获取提示、UP 主资源与视频简介都采用紧凑形式，完整原始简介以“UP 主原文（完整说明与链接）”继续折叠。

## 示例 B：知识密集型模型百科

这类视频先在 runtime 建立事实清单，再合并成 `knowledge_outline`。事实清单不是最终文章目录，而是防止把具体成员、参数、兼容关系和例外条件提前压成几个大主题。

```md
> [!summary] 先看结论
> 这类视频的价值不在单一操作步骤，而在模型规格、输入方式、提示词、加速方案和兼容性之间的系统关系。正文应保留可复查的参数、限制、方案差异与作者明确建议。

<iframe class="video-note-player" src="https://player.bilibili.com/player.html?bvid=BV1EXAMPLE02&autoplay=0&danmaku=0" allowfullscreen></iframe>

### UP 主资源

- ……

<p class="video-note-overview"><strong>视频简介</strong>：……</p>

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

| 路线 | 具体成员 | 成员关系 / 条件 | 质量与冲突 |
| --- | --- | --- | --- |
| Attention | SageAttention · Sol-Attn | 保留各自接入和组合关系 | …… |
| Turbo / LoRA | larryvrh · drbaph · Abiray · LightX2V | 保留来源、原生兼容、模型路线和步数差异 | …… |
| Cache / Prediction | EasyCache · LazyCache · TeaCache · MagCache · FirstBlockCache · Spectrum | 保留互斥/冲突关系 | …… |

> [!risk] 兼容性
> 互斥、冲突、画质损失等真正影响选择的条件在这里单独强调。

## 05 · 提示词结构

……
```

知识密集型笔记可以用表格、Grid、Chip 等压缩版面，但不能通过“只留类别名”来压缩事实。比如保留 `larryvrh · drbaph · Abiray · LightX2V` 还不够；如果字幕明确讲了它们之间的来源、原生兼容或 4 / 8 步对应关系，这些关系也必须进入正文。

## 质量判断

无论采用哪种结构，都必须满足：

- 事实只来自当前字幕与 UP 主原始简介；Learning Lab、模型记忆、联网查询或第三方下载资料不自动并入本视频笔记；
- 高价值参数、限制、比较、专名、兼容性和重要资源不能因为追求简短而丢失；
- 知识密集型内容先建立原子事实清单，再形成 `knowledge_outline`，避免“主题正确、细节关系丢失”；
- 如果来源只说明“三连 / 充电 / 评论关键词”等条件后可领取资料，只记录获取条件与来源原话；资料本体未采集到时不得由智能体补写；
- 不确定的信息宁可省略或判定来源不足，不得用模型常识补全；
- 成稿后必须重新回到原 transcript 做覆盖复核，不能只检查自己生成的 outline；
- runtime 的 `analysis.json`、marker、内部路径和采集状态不进入正式笔记。
