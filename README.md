# B站视频转笔记

将 Bilibili 视频自动整理为**字幕优先的 Obsidian 学习笔记**。默认流程只采集视频元数据、UP 主原始简介和可用中文字幕，不下载音视频；确定性内容由程序生成，接入的智能体只负责根据字幕提炼结论、步骤、坑点和实践清单。

> 内部 Skill 标识保持 `bilibili-learning`，中文展示名统一为「B站视频转笔记」。

## 核心特点

- 支持 BV 号、标准 Bilibili 视频链接、包含 BV 的复制文本，以及受控的 `b23.tv` 短链解析。
- 默认使用 `yt-dlp --skip-download`，不下载视频或音频。
- 保留 UP 主原始简介；简介获取状态区分 `present`、`confirmed_empty`、`failed`。
- 一视频一笔记，文件名带 BVID，避免同分类视频互相覆盖。
- Python 生成 Frontmatter、H1、简介、iframe、tags 和输出路径，Hermes 只填写四个 AI 内容区域。
- Finalizer 校验真实元数据、简介、iframe、文件名和 AI 区域后才刷新导航。
- 临时字幕和元数据只保存在 `.runtime/bilibili-learning`，任务结束后清理。
- Cookie 内容不进入日志、笔记或 Git。

## 工作流程

```text
复制链接 / BV / b23.tv
→ 输入解析与规范化
→ yt-dlp 仅采集 metadata / description / subtitles
→ taxonomy 分类
→ 程序生成确定性 Markdown 骨架
→ 接入智能体仅填写 AI 内容区域
→ finalizer 强校验
→ 刷新 Obsidian 导航
→ 清理临时 job
```

## 环境要求

- 可执行本地脚本的智能体运行环境；
- Python 3.10+；
- `yt-dlp`；
- 本机 Bilibili Netscape Cookie 文件；
- Obsidian 或其他可读取 Markdown 的知识库。

项目不会提交 Cookie、私人笔记和运行时资料。

## 安装（Windows）

普通使用者需要智能体运行环境、Python、yt-dlp、Cookie 和一个笔记目录。运行 skill 不要求安装测试工具；如需在本机运行 CLI、开发或测试，再创建项目独立环境：

```powershell
git clone https://github.com/ZiYao00/bili-learning-automation.git
cd bili-learning-automation
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

`.venv` 仅用于当前机器，已被 Git 忽略。当前已提供 Hermes 适配层，安装位置与验收见 [Hermes skill 安装](docs/HERMES-SKILL-INSTALL.md)。

## 多智能体使用

核心脚本、taxonomy、笔记标准和 finalizer 是智能体无关的；任何能够运行本地脚本、读取临时字幕并写入 Markdown 的智能体都可接入。统一输入/输出、清理和内容边界见 [智能体接入协议](docs/AGENT-INTEGRATION.md)。

- **Hermes**：已有微信私聊适配和已安装 skill。
- **Codex**：当前在本项目目录中工作时读取 `AGENTS.md`、接入协议和标准即可使用核心流程；目前不安装独立 Codex skill。
- **其他智能体**：只需增加薄适配层，不能复制或改写核心流程与标准。

## Quick Start

### 1. 配置笔记目录

默认笔记根目录是项目内的 `notes/bilibili`。新机器可以直接创建该目录，也可以指向现有 Obsidian Vault：

```powershell
$env:BILI_LEARNING_NOTES_ROOT = 'D:\YourObsidianVault\bilibili'
```

这个路径是本机配置，不要提交到 Git。不要把其他人的盘符或目录链接当作通用默认值。

### 2. 配置 yt-dlp

优先顺序：

1. 环境变量 `BILI_LEARNING_YTDLP`；
2. 系统 `PATH` 中的 `yt-dlp`；

建议优先把 `yt-dlp` 加入 PATH，或显式设置环境变量。

### 3. 配置 Cookie

默认位置：

```text
key/bilibili_cookies.txt
```

也可以设置：

```text
BILI_LEARNING_COOKIE_FILE
```

只检查文件是否存在；不要把 Cookie 内容提交到仓库。

### 4. 检查配置

无需安装 package，可直接运行：

```powershell
python .\hermes-skills\bilibili-learning\scripts\doctor_bilibili_learning.py
```

开发环境也可以：

```powershell
python -m pip install -e ".[dev]"
bili-learning doctor
```

### 5. 使用

在已接入智能体的允许入口中发送：

```text
BV1xxxxxxxxxx
```

或 Bilibili 的复制链接 / 受支持短链。Hermes 当前限定为 owner 私聊；其他智能体须遵守 [智能体接入协议](docs/AGENT-INTEGRATION.md) 的授权与输入边界。

正式 collector 入口仍然是：

```powershell
python .\hermes-skills\bilibili-learning\scripts\prepare_ytdlp_bilibili_note.py "<复制链接或 BV>"
```

## 笔记命名

采用一视频一笔记：

```text
{canonical_title}__{bvid}.md
```

例如：

```text
MiniMax-H3 分段生成__BV1TXua68EYi.md
```

H1 仍保持简短：

```md
# MiniMax-H3 分段生成
```

这样同类视频不会因为 taxonomy 得到相同短标题而互相覆盖。

## 配置

默认 taxonomy：

```text
config/bilibili-note-taxonomy.json
```

其中 `notes_root` 是 collector、duplicate detection、finalizer 和 navigation 共用的唯一默认笔记根目录。

可覆盖：

- `BILI_LEARNING_TAXONOMY`
- `BILI_LEARNING_NOTES_ROOT`
- `BILI_LEARNING_YTDLP`
- `BILI_LEARNING_COOKIE_FILE`

详见 [配置说明](docs/CONFIGURATION.md)。

## 数据与隐私边界

长期数据：

- 私人 Markdown 笔记；
- 自动生成的 Obsidian 导航。

临时数据：

```text
.runtime/bilibili-learning/
```

本地敏感数据：

```text
key/
```

默认不进入 Git：Cookie、私人笔记、runtime、历史 archive、materials、测试抓取输出、本地 `bili-note` / `web-access` 副本。

## 开发与测试

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
```

公共测试不需要真实 Cookie，也不应访问真实 Bilibili 账号。GitHub Actions 在 Windows 和 Linux 上执行 compile、Ruff 和 pytest。

详见 [开发说明](docs/DEVELOPMENT.md)。

## Legacy

`hermes-skills/bilibili-learning/scripts/prepare_bilibili_learning.py` 是旧的 Chrome/CDP / `bili-note` / `web-access` 路线，不是当前默认流程。本轮保留文件仅用于历史兼容，不应作为新集成入口。

详见 [Legacy 说明](docs/LEGACY.md)。

## 故障排查

优先运行：

```powershell
python .\hermes-skills\bilibili-learning\scripts\doctor_bilibili_learning.py
```

常见问题见 [故障排查](docs/TROUBLESHOOTING.md)。

## 项目结构

```text
config/                         taxonomy
src/bili_learning/              可测试的核心 Python package
hermes-skills/bilibili-learning/ Hermes Skill 与兼容入口脚本
docs/                           架构、配置、标准和维护文档
tests/                          无账号依赖的自动测试
notes/                          私人 Obsidian 笔记，默认不提交
.runtime/                       临时 job，默认不提交
```

## 许可证

本项目尚未选择发布许可证。仓库公开不等于授权他人使用或再分发；第三方依赖遵循各自许可证。选择 LICENSE 前应由仓库所有者单独确认。
