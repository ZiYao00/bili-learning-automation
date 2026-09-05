# 依赖说明

## 运行时必需

| 依赖 | 用途 | 配置方式 |
| --- | --- | --- |
| Python 3.10+ | 运行核心 package 与平台适配脚本 | 使用本机或接入智能体的 Python 环境 |
| 统一 Skill / 宿主安装出口 | 接收链接、调用核心流程、填写 AI 内容区域 | 只维护 `skill/bili-learning-automation/SKILL.md`；ChatGPT / Codex / Hermes / WorkBuddy 安装出口由构建脚本生成 |
| yt-dlp | 采集元数据、简介和字幕，不下载媒体 | 默认自动检测系统 PATH；环境变量 / `local.json` 只用于自定义路径覆盖 |
| Bilibili Cookie | 获取需要登录态的字幕/元数据 | `BILI_LEARNING_COOKIE_FILE` |

默认 Cookie 相对项目根目录为 `key/bilibili_cookies.txt`。当前正常采集要求存在 Mozilla / Netscape 格式的完整 Cookie 文件；不要只配置单个 `SESSDATA`。正常字幕/简介采集把 Cookie **文件路径**传给 yt-dlp；仅命中用户主动配置的 `config/pinned-comment-whitelist.local.json` 时，核心才会在本机读取同一 Netscape 文件并构造一次只读评论请求。Cookie 值与本地名单不得向 Agent 暴露、打印、写入示例/Job/笔记或提交。第一次获取和导出方法见 [Bilibili Cookie 获取与安全配置](BILIBILI-COOKIE.md)。

## yt-dlp 检测与安装边界

项目**不内置 `yt-dlp.exe`，也不自动安装 yt-dlp**。首次使用由 doctor 只做检测；Windows 未检测到时会提示官方推荐命令：

```powershell
winget install yt-dlp
```

安装完成后重新运行 doctor。查找顺序：

1. `BILI_LEARNING_YTDLP`；
2. `config/local.json` 的 `ytdlp`；
3. 系统 PATH 中的 `yt-dlp`；

普通用户通常只需要系统 PATH；环境变量和 `local.json` 的 `ytdlp` 只用于自定义安装位置。doctor 会验证 executable 实际可运行并返回版本，而不只检查文件存在。官方安装说明：<https://github.com/yt-dlp/yt-dlp/wiki/Installation>。

## 项目配置

默认 taxonomy：`config/bilibili-note-taxonomy.json`。

可覆盖：

- `BILI_LEARNING_TAXONOMY`
- `BILI_LEARNING_VAULT_ROOT`
- `BILI_LEARNING_NOTES_SUBDIR`
- `BILI_LEARNING_NOTES_ROOT`（旧版兼容）
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
