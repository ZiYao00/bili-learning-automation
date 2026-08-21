# 故障排查

优先执行：

```powershell
python .\hermes-skills\bilibili-learning\scripts\doctor_bilibili_learning.py
```

## 未找到 yt-dlp

设置 `BILI_LEARNING_YTDLP`，或把 `yt-dlp` 加入 PATH。

## Cookie 文件不存在

确认 `BILI_LEARNING_COOKIE_FILE`，或在本机提供默认的 `key/bilibili_cookies.txt`。不要把 Cookie 内容复制到日志、Issue 或 README。

## `subtitle_unavailable`

表示没有取得 `ai-zh` 或 `zh.*` 字幕。默认流程不会因此下载音视频，也不会自动转 ASR。

## `failed: 无法确认 UP 主原始简介`

元数据没有提供可确认的 description 状态。根据项目规则，这不能当成“视频确实没有简介”，任务必须停止。

## `note_invalid`

Finalizer 会检查真实 Frontmatter 值、原视频 H1、H1 下方 BVID 小字、完整简介结构、iframe、规范 tags 和四个 AI 内容区域。无效草稿不会发布；job 会在清理阶段从 runtime 精确删除，同时释放正式路径，便于重新发起任务。不要绕过 finalizer。

## `already_exists`

系统按 canonical source URL 判重，也兼容 H1 下方的 BVID 小字和旧的 BVID 文件名。

## `organize` 失败

确认 `--note` 是 notes root 内的正式笔记、`--title` 与 `--intro` 非空、`--category`（如提供）是项目内相对目录。不要手动移动文件；核心会在安全发布后删除旧位置并重建导航。

## 短链无法解析

只允许 Bilibili 官方域名，且限制重定向次数和超时。无法解析时重新从 Bilibili 使用“复制链接”。
