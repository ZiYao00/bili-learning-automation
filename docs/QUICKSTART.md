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
2. **检查基础运行环境**：Python 3.10+；`tools/yt-dlp.exe` 存在，且直接执行 `--version` 成功。只使用项目内 EXE，不查找系统 PATH、不安装 yt-dlp 源码。
3. **检查配置**：运行 `python scripts/run_bili_learning.py onboarding`；根据 `actions` 补齐缺失项，不能仅凭文件存在就宣布成功。
4. **安装所选本地 Agent Skill**：通过下文的安全辅助脚本先计划、再按授权应用。Codex/Hermes/WorkBuddy 共享同一 canonical Skill；不复制多套 `SKILL.md`。
5. **绑定 Obsidian**：确认真实 Vault 根目录包含 `.obsidian`；让核心写入配置，然后建立并验证 Vault → 项目 notes 的 Junction。
6. **配置 Cookie**：用户自己通过可信方式取得 Netscape `cookies.txt`，Agent 只接收路径、检查文件存在，绝不读取或打印凭据。
7. **复验**：运行 `onboarding`；只有返回 `ready` 且 Skill 安装有效，才向用户报告可直接转换视频。

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
python .\scripts\run_bili_learning.py configure-obsidian --vault '<vault-root>' --notes-subdir 'bilibili'
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
python .\scripts\run_bili_learning.py configure-cookie --file '<private-netscape-cookie-file>'
```

不要把 Cookie 内容放进聊天、日志、项目配置或 Git。格式和个人安全操作见 [Bilibili Cookie 教程](BILIBILI-COOKIE.md)。Doctor 只确认文件存在，不验证浏览器会话是否过期。

### 2.4 验收（Agent 执行）

```powershell
python .\scripts\run_bili_learning.py onboarding
python .\scripts\run_bili_learning.py doctor --json
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
