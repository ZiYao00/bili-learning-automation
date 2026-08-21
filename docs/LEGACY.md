# Legacy 流程

当前正式流程是 `prepare_ytdlp_bilibili_note.py`：仅使用 yt-dlp 获取元数据、简介和字幕，不下载媒体，不启动 Chrome/CDP。

`hermes-skills/bili-learning-automation/scripts/prepare_bilibili_learning.py` 属于旧流程，依赖本机 `bili-note`、`web-access`、Chrome/CDP、materials/archive。它保留在本地仓库用于历史兼容和排查，但：

- 不应作为新的 Hermes 接入入口；
- README 和 SKILL 不再引用它作为默认流程；
- 不要把本机 `bili-note` / `web-access` 副本重新提交到公开仓库；
- 如果未来重新启用，需要单独设计 backend 接口和测试，而不是在默认流程中静默 fallback。

本轮不删除 legacy 文件，避免破坏本机历史工作流。是否彻底移除应由仓库所有者单独决定。
