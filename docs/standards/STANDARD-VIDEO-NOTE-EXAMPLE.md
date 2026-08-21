---
author: "示例UP主"
published: "2026-08-11"
duration: "07:05"
source: "https://www.bilibili.com/video/BV1EXAMPLE01/"
tags:
  - "视频生成"
  - "工作流"
  - "MiniMax-H3"
---

# H3 分段工作流：连续片段生成

<small>BV号：BV1EXAMPLE01</small>

## 视频简介

本示例用于展示程序保留并压缩展示 UP 主原始简介。

## UP 主资源

- [示例资源](https://example.com/resource)

<details>
<summary>UP 主原始简介</summary>

本示例用于展示“程序保留 UP 主原始简介”的位置。真实笔记中这里必须是 collector 取得的原始简介，智能体不得改写。
https://example.com/resource

</details>

<iframe
  src="https://player.bilibili.com/player.html?bvid=BV1EXAMPLE01&autoplay=0&danmaku=0"
  style="width:100%;aspect-ratio:16/9;border:0;"
  allowfullscreen>
</iframe>

> [!summary] 先看结论
> **用途：** 把单段时长受限的视频拆成多个片段连续生成。
> **适合：** 已有首帧或参考图，需要制作更长连续视频的人。
> **记住：** 每段控制在模型允许时长内，并让上一段末帧参与下一段生成。

## 怎么做

1. 根据目标总时长拆分片段。
2. 为每个片段准备对应提示词。
3. 第一段使用初始参考图。
4. 后续片段以上一段末帧作为连续性参考。
5. 检查输出片段后再决定是否拼接。

[02:34 末帧桥接](https://player.bilibili.com/player.html?bvid=BV1EXAMPLE01&t=154)

## 容易踩坑

- **单段超过模型限制** → 增加分段数或缩短单段时长。
- **提示词数量与片段数不一致** → 先确认每个片段都有对应提示词。
- **主体在后续片段发生明显变化** → 检查上一段末帧是否正确作为下一段参考。

**我来实践**

- [ ] 先做两个短片段的最小测试。
- [ ] 检查两段之间的主体和动作衔接。
- [ ] 确认流程稳定后再增加总时长。
