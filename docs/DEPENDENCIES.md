# 依赖说明

## 运行时必需

| 依赖 | 用途 | 配置方式 |
| --- | --- | --- |
| Python 3.10+ | 运行核心 package 和 Hermes 兼容脚本 | 使用 Hermes/本机已有 Python 环境 |
| Hermes | 接收链接、调用 skill、填写 AI 内容区域 | 独立安装；本项目不复制 Hermes 本体 |
| yt-dlp | 采集元数据、简介和字幕，不下载媒体 | `BILI_LEARNING_YTDLP` 或系统 PATH |
| Bilibili Cookie | 获取需要登录态的字幕/元数据 | `BILI_LEARNING_COOKIE_FILE` |

默认 Cookie 相对项目根目录为 `key/bilibili_cookies.txt`。Cookie 是凭据，只允许把文件路径传给 yt-dlp；不要读取、打印或写入示例配置。

## yt-dlp 查找顺序

1. `BILI_LEARNING_YTDLP`；
2. 系统 PATH 中的 `yt-dlp`；

公开文档和新环境必须使用前两种方式之一。

## 项目配置

默认 taxonomy：`config/bilibili-note-taxonomy.json`。

可覆盖：

- `BILI_LEARNING_TAXONOMY`
- `BILI_LEARNING_NOTES_ROOT`
- `BILI_LEARNING_YTDLP`
- `BILI_LEARNING_COOKIE_FILE`

## 开发依赖

通过：

```powershell
python -m pip install -e ".[dev]"
```

安装：

- `pytest`：自动测试；
- `ruff`：静态检查。

公共 CI 不需要 Cookie，也不访问真实 Bilibili 账号。

## 可选 / 历史依赖

- [Rimagination/bili-note](https://github.com/Rimagination/bili-note)：旧 Chrome/CDP 流程使用；当前默认 yt-dlp 路线不调用。
- [eze-is/web-access](https://github.com/eze-is/web-access)：旧 Chrome/CDP 流程使用；当前默认路线不调用。

这两个本地副本不属于当前项目源码。重新启用前应单独确认版本、许可证、接口和安全边界，不能作为默认流程的静默 fallback。
