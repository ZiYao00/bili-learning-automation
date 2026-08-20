# 视频学习笔记规范包

本压缩包包含两份核心文档：

- `STANDARD-VIDEO-NOTE-EXAMPLE.md`：最终成品示例。Agent 和 Codex 生成笔记时先看这个。
- `CODEX-VIDEO-NOTE-GUIDE.md`：生成规则，包含必填字段、视频简介、层级控制、iframe 与插件原则。

最重要的一条：**视频简介必须获取并写入笔记；不能因为字幕抓到了就忽略简介。**

本规范面向 Obsidian 内的 Bilibili 学习笔记，默认采用：

- 原视频链接 + iframe 播放；
- 视频简介紧跟标题；
- 简短结论、怎么做、踩坑、实践清单；
- 不把机器索引、证据 JSONL、抓取状态堆到正文。
