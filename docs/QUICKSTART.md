# 快速上手：由 Agent 完成安装

> 面向 Windows 10/11 x64。本项目不提供双击安装向导；**普通用户只向 Agent 描述目标、提供必要路径和授权，不手工执行安装命令。** 以下命令是给 Agent 的操作参考。

## 1. 用户只需要说什么

在能够访问本地工作区的 Codex、Hermes、WorkBuddy 或 ChatGPT（需本地桥接）中发送：

```text
请安装并验证 bili-learning-automation：
https://github.com/ZiYao00/bili-learning-automation

请阅读 AGENTS.md、docs/QUICKSTART.md 和 docs/LOCAL-AGENT-INSTALL.md，
检查 Python、项目内 tools/yt-dlp.exe、Obsidian 和 Cookie 文件路径，
按需安装我正在使用的 Agent Skill，配置并验证 Junction，
最后运行 onboarding，汇报已就绪项和未完成项。
你负责执行，不让我手工修改配置。不要覆盖任何已有笔记、目录或 Skill。
需要写入我的 Vault / 用户级 Skill 目录时，先说明位置并取得授权。
Cookie 只使用本地文件路径，不读取或发送内容。
```

如果尚未下载项目，Agent 可以在获得项目工作区创建权限后自行克隆或获取源码。安装前不假设本机有 CodexPro；任何能执行相同操作且已获授权的本地 Agent 均可使用。远程 ChatGPT 沙箱不能直接读取本机 Windows 磁盘路径。

## 2. Agent 的安装顺序

1. **识别项目根**：确认 `AGENTS.md`、`pyproject.toml`、`scripts/run_bili_learning.py`、`config/bilibili-note-taxonomy.json` 全部存在；只操作已授权路径。
2. **先检查 Python，不依赖 Python 自身启动预检**：由 Agent 运行 `scripts/run_bili_learning.ps1 -ProbeOnly`；返回 `python_required` 时，先核查 Python 是否已安装，只有取得用户对系统安装的授权后才从官方渠道准备 Python 3.12，不静默安装、不要求用户手工操作。`BILI_LEARNING_PYTHON` 可临时指定现成的可信外部解释器；无需把 `.venv` 复制进仓库。再检查项目内 `tools/yt-dlp.exe --version`。
3. **检查配置**：预检 `ready` 后由 Agent 运行 `scripts/run_bili_learning.ps1 onboarding`；该命令与 canonical Skill 桥接复用同一解释器检测逻辑。根据 `actions` 补齐缺失项，不能仅凭文件存在就宣布成功。
4. **安装所选本地 Agent Skill**：通过下文的安全辅助脚本先计划、再按授权应用。Codex/Hermes/WorkBuddy 共享同一 canonical Skill；不复制多套 `SKILL.md`。
5. **绑定 Obsidian**：确认真实 Vault 根目录包含 `.obsidian`；让核心写入配置，然后建立并验证 Vault → 项目 notes 的 Junction。
6. **配置 Cookie**：用户自己通过可信方式取得 Netscape `cookies.txt`，Agent 只接收路径、检查文件存在，绝不读取或打印凭据。
7. **复验**：运行 `onboarding`；只有返回 `ready` 且 Skill 安装有效，才向用户报告可直接转换视频。

### 2.0 Python 环境预检（Agent 执行）

```powershell
.\scripts\run_bili_learning.ps1 -ProbeOnly
```

仅执行只读检查，输出 `ready`（包括版本、解释器来源）或 `python_required`。如果缺少 Python，Agent 应从 [Python 官方 Windows 下载页](https://www.python.org/downloads/windows/) 确认可用安装方式，说明需要的安装范围并得到用户授权后执行；推荐 Python 3.12，已有兼容的 3.10+ 可继续用。不向 Git 提交 `.venv`，不打包 Python。对于未加入 PATH 的可信解释器，Agent 可在自己的 PowerShell 会话临时设置 `$env:BILI_LEARNING_PYTHON = '<absolute-python.exe>'`，**该变量只控制 Python，与固定的 yt-dlp 路径无关**。环境变量指定错误时应停止，不静默回退到另一解释器。

### 2.1 本地 Agent Skill 安装（Agent 执行）

以下命令 **默认只做只读计划，不修改用户目录**：

```powershell
.\scripts\install_agent_skill.ps1 -Agent Codex
.\scripts\install_agent_skill.ps1 -Agent Hermes
.\scripts\install_agent_skill.ps1 -Agent WorkBuddy
```

只针对用户实际使用的 Agent 执行。取得相应**用户级 Skill 目录**的明确写入许可后，再调用：

```powershell
.\scripts\install_agent_skill.ps1 -Agent Codex -Apply
```

其它宿主替换 `-Agent` 值即可。现有正确 Junction 会返回 `already_installed`；目标已有普通目录、静态副本或指向其他位置时返回 `conflict`，**不得删除或自动替换**。细节见 [本地 Agent 安装](LOCAL-AGENT-INSTALL.md)。

### 2.2 Obsidian 配置与 Junction（Agent 执行）

确认 Vault 路径属于用户已授权范围后：

```powershell
.\scripts\run_bili_learning.ps1 configure-obsidian --vault '<vault-root>' --notes-subdir 'bilibili'
```

全新配置自动使用项目内 `notes/bilibili` 作为真实物理存储，不改变已有直接写 Vault 的旧配置模式。由 Agent 从设置和实际路径确定两个**绝对路径**：

```text
Source = <repo-root>\notes\bilibili
Target = <vault-root>\bilibili
```

先计划；确认授权和无冲突后才执行：

```powershell
.\scripts\ensure_junction.ps1 -Source '<source-absolute-path>' -Target '<target-absolute-path>'
.\scripts\ensure_junction.ps1 -Source '<source-absolute-path>' -Target '<target-absolute-path>' -Apply
```

如 `Target` 已经有普通文件夹或原有笔记，脚本**不会替换、迁移或删除**；应停止并请用户决定如何处理。真实方向始终是 **Vault 子目录 → 项目内 notes**，不可反向设置。完成后 `onboarding` 必须显示 `obsidian_notes_mapping` 通过。

### 2.3 Cookie 路径（Agent 执行）

```powershell
.\scripts\run_bili_learning.ps1 configure-cookie --file '<private-netscape-cookie-file>'
```

不要把 Cookie 内容放进聊天、日志、项目配置或 Git。格式和个人安全操作见 [Bilibili Cookie 教程](BILIBILI-COOKIE.md)。Doctor 只确认文件存在，不验证浏览器会话是否过期。

### 2.4 验收（Agent 执行）

```powershell
.\scripts\run_bili_learning.ps1 onboarding
.\scripts\run_bili_learning.ps1 doctor --json
```

`ready` 表示运行环境已就绪；Skill 是否在当前宿主可发现仍需单独确认。CSS 缺失是提醒，不阻塞转换。缺失样式时参考 [Obsidian 样式说明](OBSIDIAN-STYLING.md)，不可覆盖已有 CSS。

## 3. ChatGPT Web 安装边界

ChatGPT Web 使用 `dist/bili-learning-automation-chatgpt.zip`，不是用户级 Junction。Agent 可以从 canonical Skill 构建 ZIP，但 ChatGPT 页面中的 Skill 安装和本地连接授权必须通过受支持的操作方式完成；没有自动化入口时由用户在界面确认。**没有本地桥接的 ChatGPT 仅能安装 Skill，无法执行本机笔记转换。** 详见 [ChatGPT Skill 安装](CHATGPT-SKILL-INSTALL.md)。

## 4. 完成后怎么使用

在已经接入项目的 Agent 中直接发送 Bilibili 链接或 BV 号，例如：

```text
帮我将这个 B 站视频转成 Obsidian 学习笔记：
https://www.bilibili.com/video/BVxxxxxxxxxx/
```

默认先取字幕且**不下载音视频**。如果没有可用字幕，Agent 会报告 `subtitle_unavailable`，不会自动 ASR。已转换过的 BVID 默认先询问是否更新、重做或取消；成功发布以 `note_ready` 为准，笔记保存在 `00-待整理`。

`local-ASR-service` 是可选独立服务；本项目**不安装、不启动、不复制 ASR 模型**。用户主动要求 ASR 时，Agent 按 [配置手册](CONFIGURATION.md) 检查已部署的服务；如果没有安装，提供其独立项目的安装说明，不影响正常字幕流程。

## 5. 更新与故障恢复

Agent 更新仓库时必须保护本机 `config/local.json`、`key/`、`notes/`、`.runtime/` 和现有 Junction。禁止为了升级删除整个项目目录或将私人笔记加入 ZIP/Git。重复执行安装助手应安全返回 `already_installed` 或 `conflict`，不进行破坏性修复。

故障优先运行 `doctor` 并查询 [故障排查](TROUBLESHOOTING.md)。开发与平台兼容问题请阅读 [文档中心](README.md)。
