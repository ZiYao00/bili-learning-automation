---
author: 南极来の企鹅
published: 2026-08-11
duration: 07:05
source: https://www.bilibili.com/video/BV1TXua68EYi/
tags:
  - ComfyUI
  - MiniMax-H3
  - 工作流
---

# 打破15秒限制！H3分段参考生成工作流

> **视频简介**
>
> 【必填：这里必须放入从 Bilibili 视频信息中获取到的 UP 主原始简介全文。】
>
> - 不允许用 AI 摘要替代原简介。
> - 不允许因为抓取失败而直接省略。
> - 简介中的 GitHub、网盘、模型、工作流、文档等 URL 应转换成可点击链接。
> - 如果当前抓取失败，本篇笔记应标记为“资料不完整”，而不是当作完成品。
>
> 说明：本标准样例使用的上一版测试资料没有包含真实 `desc` 字段，因此这里故意不虚构原文。
> 实际生产笔记中，此处必须被真实视频简介替换。

<iframe
  src="https://player.bilibili.com/player.html?bvid=BV1TXua68EYi&autoplay=0&danmaku=0"
  style="width:100%;aspect-ratio:16/9;border:0;"
  allowfullscreen>
</iframe>

> [!summary] 先看结论
> **用途：** H3 单段最多 15 秒，通过“分段生成 + 上一段末帧作为下一段首帧”实现更长的连续视频。
> **适合：** 正在使用 H3 做长视频时值得实践。
> **记住：** 每段 ≤ 15 秒 · 提示词数量 = 分段数量 · 上一段末帧 → 下一段首帧。

## 怎么做

1. 把目标总时长拆成多个不超过 15 秒的片段。
2. 每个片段准备一条对应提示词，提示词数量必须与分段数量一致。
3. 第一段使用初始参考图。
4. 从第二段开始，把上一段末帧作为下一段首帧参考。
5. 生成完成后到输出目录检查实际片段，再决定是否拼接。

**例子：** 60 秒可以用 `4 × 15 秒` 或 `5 × 12 秒`；不能用 `3 × 20 秒`。

[00:34 时长与提示词校验](https://player.bilibili.com/player.html?bvid=BV1TXua68EYi&t=34) ·
[02:34 末帧桥接](https://player.bilibili.com/player.html?bvid=BV1TXua68EYi&t=154) ·
[03:14 参考图编号变化](https://player.bilibili.com/player.html?bvid=BV1TXua68EYi&t=194) ·
[05:20 输出目录与内存](https://player.bilibili.com/player.html?bvid=BV1TXua68EYi&t=320)

## 容易踩坑

- **单段超过 15 秒** → 增加分段数或缩短单段时长。
- **提示词数量不一致** → 提示词数量必须等于分段数量。
- **第二段开始主体变化** → 检查上一段末帧是否正确传入，以及参考图编号是否变化。
- **任务队列只看到一段** → 先到输出目录确认实际落盘片段。

**我来实践**

- [ ] 先用 `2 × 10 秒` 做最小测试。
- [ ] 检查第一段与第二段的衔接。
- [ ] 检查参考图编号是否错位。
- [ ] 成功后再尝试 `4 × 15 秒`。
