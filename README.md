# B站视频转笔记

将 Bilibili 视频自动整理为**字幕优先的 Obsidian 学习笔记**。默认流程只采集视频元数据、UP 主原始简介和可用中文字幕，不下载音视频；确定性内容由程序生成，Codex/Hermes 负责判断字幕是否足以支撑可靠笔记、提取高价值知识、动态组织正文并做覆盖复核。

> Hermes Skill 标识为 `bili-learning-automation`，中文展示名统一为「B站视频转笔记」。

## 核心特点

- 支持 BV 号、标准 Bilibili 视频链接、包含 BV 的复制文本，以及受控的 `b23.tv` 短链解析。
- 默认使用 `yt-dlp --skip-download`，不下载视频或音频。
- 保留 UP 主原始简介；简介获取状态区分 `present`、`confirmed_empty`、`failed`。
- 每次成功转换生成一篇笔记；BVID 以 H1 下方的小字记录，文件名保持干净，同名时自动使用序号防覆盖。
- Python 生成 Frontmatter、H1、简介、iframe、tags、`learning-page + video-note` cssclasses、输出路径和 runtime 质量报告骨架；所有新笔记先进入 `00-待整理`。
- Codex/Hermes 先做来源充分性判断和知识清单，再填写“先看结论 + 动态知识正文”，成稿后完成覆盖复核。
- Finalizer 校验真实元数据、简介、iframe、文件名、AI 区域和质量流程状态后才原子发布并刷新导航。
- 临时字幕和元数据只保存在 `.runtime/bilibili-learning`，任务结束后清理。
- Cookie 内容不进入日志、笔记或 Git。

## 工作流程

```text
复制链接 / BV / b23.tv
→ 输入解析与规范化
→ yt-dlp 仅采集 metadata / description / subtitles
→ taxonomy 给出标签与后续整理建议
→ 程序在 runtime 生成确定性 Markdown 草稿与 analysis.json
→ Codex/Hermes 判断来源充分性并形成 knowledge_outline
→ 填写“先看结论 + 动态知识正文”并完成 coverage review
→ finalizer 校验后原子发布
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

`.venv` 仅用于当前机器，已被 Git 忽略。当前已提供 Hermes 与 WorkBuddy 适配层：Hermes 安装位置与验收见 [Hermes skill 安装](docs/HERMES-SKILL-INSTALL.md)；WorkBuddy 适配层在 `workbuddy-skills\bili-learning-automation\`，通过 junction 安装到 `~\.workbuddy\skills\bili-learning-automation`。

## 多智能体使用

核心脚本、taxonomy、笔记标准和 finalizer 保持智能体无关，但当前开发与验收优先保证 **Codex + Hermes + WorkBuddy** 三个入口可靠。统一输入/输出、清理和内容边界见 [智能体接入协议](docs/AGENT-INTEGRATION.md)。

- **Codex**：当前在本项目目录中工作时读取 `AGENTS.md`、接入协议和标准即可使用核心流程；目前不安装独立 Codex skill。
- **Hermes**：已有微信私聊适配和已安装 skill，只保留入口特有规则，内容分析复用共享标准。
- **WorkBuddy**：适配层位于 `workbuddy-skills\`，junction 安装到本机 WorkBuddy skills 目录；会话内用户提供链接/BV 号触发，复用同一套核心脚本与标准。
- **其他智能体**：属于后续扩展目标；接入时增加薄适配层，不复制或改写核心流程与标准。

## Obsidian 版式

项目已经自带可直接安装的 Core + Video Note 样式：

```text
obsidian/snippets/
├── learning-lab.css
└── video-note.css
```

第一次使用时，把这两个文件复制到**实际 Obsidian Vault 根目录**下的：

```text
.obsidian/snippets/
```

然后打开 **Obsidian → 设置 → 外观 → CSS 代码片段**，刷新列表并同时启用 `learning-lab` 与 `video-note`。`video-note.css` 依赖 `learning-lab.css`，不要只复制或只启用其中一个。

新笔记会自动写入 `learning-page + video-note` cssclasses，不需要手工修改 Frontmatter；阅读顺序固定为“先看结论 → 播放器 → 知识正文 → 视频资料”。如果 `notes_root` 只是某个 Vault 里的子目录，CSS 应安装到该 Vault 的 `.obsidian/snippets/`，不是安装到 `notes_root` 子目录。完整的新手教程、更新方式和故障排查见 [Obsidian 视觉样式](docs/OBSIDIAN-STYLING.md)。

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
2. Git 忽略的本机配置 `config/local.json`；
3. 系统 `PATH` 中的 `yt-dlp`；

新机器建议优先把 `yt-dlp` 加入 PATH，或显式设置环境变量。已部署机器可将本机路径写入 `config/local.json`，该文件不会进入 Git。详见 [配置说明](docs/CONFIGURATION.md)。

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
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

供 Hermes、Codex 或其他自动化工具解析的 JSON 诊断：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py --json
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
python .\hermes-skills\bili-learning-automation\scripts\prepare_ytdlp_bilibili_note.py "<复制链接或 BV>"
```

所有智能体也可直接使用核心 CLI：

```powershell
bili-learning prepare "<复制链接或 BV>"
bili-learning finalize --job '<job_dir>' --note '<draft_path>'
bili-learning organize --note '<已学习笔记>' --title '<短标题>' --intro '<一句简介摘要>'
```

Hermes 保留原脚本路径作为兼容启动壳，调用的是同一核心 CLI。

## 收件箱、命名与后续整理

所有新笔记先发布到：

```text
notes/bilibili/00-待整理/
```

这里是“尚未阅读”的统一收件箱。taxonomy 不再自动把新笔记直接放进模型/主题目录；它只决定 tags 与建议分类，供学习后整理。这样不会把未学习的资料伪装成已整理知识。

收集阶段保留 B站原视频标题，不做 AI 标题改写。每次成功转换生成一篇笔记：

```text
{原视频标题}.md
```

例如：

```text
H3智能一体化节点重磅升级.md
```

H1 默认使用原视频标题，BVID 以小字显示：

```md
# H3智能一体化节点重磅升级

<small>BV号：BV16g8J6AEZD</small>
```

若同目录出现相同原视频标题，系统使用 `（2）`、`（3）` 等无语义序号，绝不覆盖。重复链接可再次转换；仅在同一 BVID 仍有活动任务时返回 `in_progress`，防止并发冲突。BVID 不作为 tag 或文件名后缀。

学习后可通过统一 `organize` 命令一次完成短标题、简介摘要和目录归档；默认按 tags 推断 taxonomy 建议目录，也可显式指定目标目录。详见 [智能体接入协议](docs/AGENT-INTEGRATION.md)。

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

`hermes-skills/bili-learning-automation/scripts/prepare_bilibili_learning.py` 是旧的 Chrome/CDP / `bili-note` / `web-access` 路线，不是当前默认流程。本轮保留文件仅用于历史兼容，不应作为新集成入口。

详见 [Legacy 说明](docs/LEGACY.md)。

## 故障排查

优先运行：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

常见问题见 [故障排查](docs/TROUBLESHOOTING.md)。

## 项目结构

```text
config/                         taxonomy
src/bili_learning/              可测试的核心 Python package
hermes-skills/bili-learning-automation/ Hermes Skill 与兼容入口脚本
obsidian/snippets/               可直接复制到 Vault 的 Core + Video Note CSS
docs/                           架构、配置、标准和维护文档
tests/                          无账号依赖的自动测试
notes/                          私人 Obsidian 笔记，默认不提交
.runtime/                       临时 job，默认不提交
```

## 许可证

本项目尚未选择发布许可证。仓库公开不等于授权他人使用或再分发；第三方依赖遵循各自许可证。选择 LICENSE 前应由仓库所有者单独确认。
