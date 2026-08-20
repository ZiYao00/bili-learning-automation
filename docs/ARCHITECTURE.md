# 架构说明

## 主链路

```text
Hermes 私聊中的复制链接 / BV 号 / 受支持短链
→ input_resolver 规范化 BVID 与 canonical URL
→ yt-dlp 仅采集元数据、UP 主简介、ai-zh/zh 字幕
→ taxonomy 分类并生成唯一 note path
→ Python 写入确定性 Markdown 骨架
→ Hermes 只填写四个 AI 内容区域
→ finalizer 强校验真实元数据与结构
→ navigation 原子刷新
→ 清理临时 job
```

## 代码分层

- `src/bili_learning/`：可测试的核心逻辑。
- `hermes-skills/bilibili-learning/SKILL.md`：Hermes 行为约束。
- `hermes-skills/bilibili-learning/scripts/`：保留原调用路径的兼容入口。
- `config/bilibili-note-taxonomy.json`：分类规则、模型别名和默认 `notes_root`。
- `docs/standards/`：人类可读的笔记质量标准。

## 确定性边界

程序负责：

- canonical URL；
- BVID 唯一文件名；
- Frontmatter；
- H1；
- 原始简介；
- iframe；
- tags；
- 输出路径；
- 导航。

Hermes 只负责根据字幕和原始简介生成：

- 先看结论；
- 怎么做；
- 容易踩坑；
- 我来实践。

这样避免 LLM 重写元数据、简介或路径。

## 数据边界

- 长期产物：私人 Markdown 笔记与导航页，默认不入 Git。
- 临时产物：`.runtime/bilibili-learning`；成功、失败或 failsafe 后清理。
- 敏感数据：`key/` 中的 Cookie 文件；程序只把路径传给 yt-dlp，不读取内容。
- 历史资料：`archive/`、`materials/` 及本机 legacy 依赖，不属于公开源码主链路。

## 配置边界

`notes_root` 从 taxonomy 统一读取，也可用 `BILI_LEARNING_NOTES_ROOT` 覆盖。collector、判重、finalizer、navigation 使用同一 settings loader。

## 可靠性原则

- 笔记文件名包含 BVID，防止同 taxonomy route 冲突。
- 同一 BVID 的 collector 使用独占锁；残留锁超过 1 小时可自动恢复。
- Finalizer 校验真实值，而非仅检查字段名；无效笔记改名为 `.md.invalid` 保留现场并释放正式路径。
- 导航采用临时文件后原子替换。
- 外部 yt-dlp 调用有超时。
- cleanup 只允许作用于 runtime root 的子目录，并且不把 `locks/` 当作 job 清理。
