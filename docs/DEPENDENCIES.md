# 依赖说明

## 必需

| 依赖 | 用途 | 本机覆盖方式 |
| --- | --- | --- |
| Hermes | 接收链接、调用 skill、生成笔记 | 独立安装；本项目不复制 Hermes 本体 |
| yt-dlp | 采集元数据、简介和字幕 | `BILI_LEARNING_YTDLP` |
| Bilibili Cookie | 获取需登录的字幕 | `BILI_LEARNING_COOKIE_FILE` |

默认 Cookie 相对项目根目录为 `key/bilibili_cookies.txt`。Cookie 是凭据，不能提交或写入示例配置。

## 项目默认配置

分类配置默认位于 `config/bilibili-note-taxonomy.json`，可通过 `BILI_LEARNING_TAXONOMY` 指向另一份本机配置。

## 可选/历史依赖

- [Rimagination/bili-note](https://github.com/Rimagination/bili-note)：MIT。旧 Chrome/CDP 流程使用；当前默认 yt-dlp 流程不调用。
- [eze-is/web-access](https://github.com/eze-is/web-access)：旧 Chrome/CDP 流程使用；当前默认 yt-dlp 流程不调用。其许可证应在重新启用或重新分发前单独核对。

不要把这两个本地副本当作项目源码提交；如未来需要重新启用，应记录获取版本与本地修改原因。
