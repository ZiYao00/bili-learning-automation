# B站视频转笔记：内容与格式标准

## 目标

生成给人快速阅读和实践的 Obsidian 学习笔记，而不是机器分析报告。

默认目标：

- 30 秒内判断视频讲什么、是否值得继续看；
- 3 分钟内掌握主要操作方法；
- 需要时可在 Obsidian 内直接播放原视频；
- 机器资料不进入人的主阅读页面。

## 责任边界

当前正式流程采用确定性骨架。

### 程序负责，Hermes 不得修改

- Frontmatter；
- H1；
- UP 主原始简介；
- Bilibili iframe；
- tags；
- 文件路径和文件名；
- `BILI_AI_*_START/END` marker。

### Hermes 负责

只根据字幕与原始简介填写四个 marker 区域：

1. `BILI_AI_SUMMARY`：先看结论；
2. `BILI_AI_STEPS`：怎么做；
3. `BILI_AI_PITFALLS`：容易踩坑；
4. `BILI_AI_PRACTICE`：我来实践。

不要重新生成整篇 Markdown。

## 文件名与标题

一视频一笔记。

文件名：

```text
{canonical_title}__{bvid}.md
```

H1：

```md
# {canonical_title}
```

BVID 只用于文件级唯一性，不放进 H1。

## Frontmatter

固定且只允许：

- `author`
- `published`
- `duration`
- `source`
- `tags`

这些字段由程序从 job 数据生成。Hermes 不修正、不补写、不改格式。

`source` 必须是规范化后的 Bilibili 原视频 URL，不保留分享追踪参数。

## 视频简介

视频简介是硬性核心数据，由 collector 判定状态并由程序写入。

状态：

- `present`：已取得非空原始简介；
- `confirmed_empty`：上游明确提供 description 字段且确认为空；
- `failed`：无法确认简介，任务停止。

Hermes 不得：

- 用 AI 摘要替代原简介；
- 修改原简介语义；
- 因字幕完整而省略简介；
- 把抓取失败当作“视频无简介”。

原始简介中的 URL 文本必须保留。Obsidian 可直接识别裸 URL；不要为了美化而改变目标地址。

## 视频播放

使用 Bilibili 官方 iframe，由程序生成：

```html
<iframe
  src="https://player.bilibili.com/player.html?bvid=BV...&autoplay=0&danmaku=0"
  style="width:100%;aspect-ratio:16/9;border:0;"
  allowfullscreen>
</iframe>
```

不默认安装 Obsidian 插件，不下载本地视频。

## 先看结论

保持短而有用。

建议覆盖：

- 这段视频解决什么问题；
- 适合谁；
- 最值得记住的一条结论。

不要把“怎么做”逐条重复一遍。

## 怎么做

使用清晰、可执行的步骤。

要求：

- 步骤顺序必须能从字幕或简介得到支持；
- 视频很短时不要为了模板硬凑步骤；
- 节点名、模型名、参数、资源地址不确定时不要猜。

字幕有明确关键位置时可增加少量时间点链接，例如：

```md
[02:34 末帧桥接](https://player.bilibili.com/player.html?bvid=BV...&t=154)
```

不要展示内部证据 ID。

## 容易踩坑

只保留视频真正提到或能从操作流程直接支持的风险。

推荐格式：

```md
- **问题** → 解决方式。
```

不要添加泛化的“AI 常见问题”。

## 我来实践

只列少量值得实际验证的动作：

```md
- [ ] 做一次最小测试。
- [ ] 检查关键衔接或输出。
```

避免把整篇步骤复制成 checklist。

## 内容证据边界

正文事实必须来自：

- 当前视频字幕；
- UP 主原始简介。

用户另外提供的链接或资料只有在明确要求写入时才能加入，并标记为“用户补充”。

不允许根据常识补全视频没有提供的具体参数、资源地址或结论。

## 机器资料边界

主笔记不得出现：

- `.runtime` 路径；
- `job.json`；
- `agent_handoff.md`；
- 证据 JSONL / 字幕证据编号；
- Cookie；
- 抓取日志；
- 是否下载媒体等执行噪音。

## 完成判断

Finalizer 是最终判定者。

一篇完成笔记至少满足：

- 路径和文件名符合 BVID 唯一规则；
- Frontmatter 值与 job 元数据一致；
- H1 正确；
- 原始简介按采集结果完整保留；
- iframe 使用正确 BVID；
- required tags 齐全；
- 四个 AI 区域均已填写；
- 没有机器内部信息；
- `finalize_ytdlp_bilibili_note.py` 返回 `note_ready`。

在 finalizer 返回 `note_ready` 之前，不得向用户声称任务完成。
