# 本地 Agent Skill 安装（Agent 自动操作）

适用宿主：Codex、Hermes、WorkBuddy；需要 Windows 本机工作区和用户授权。**没有双击安装向导，也不要求普通用户运行 PowerShell 或修改 JSON。**

## 1. 安装模型

仓库只保留一个需要人工维护的 canonical Skill：

```text
<repo-root>\skill\bili-learning-automation\
```

三个本地宿主通过 Junction 指向它，不复制独立副本：

| Agent | Junction 目标目录 |
| --- | --- |
| Codex | `%USERPROFILE%\.agents\skills\bili-learning-automation` |
| Hermes | `%LOCALAPPDATA%\hermes\skills\bili-learning-automation` |
| WorkBuddy | `%USERPROFILE%\.workbuddy\skills\bili-learning-automation` |

ChatGPT Web 不使用本地 Junction，需安装独立 ZIP + 授权本地工作区桥接，参阅 [ChatGPT Skill 安装](CHATGPT-SKILL-INSTALL.md)。

## 2. Agent 推荐执行顺序

1. 确认用户授权的本地项目根目录（至少 `AGENTS.md`、`pyproject.toml`、`scripts/run_bili_learning.py`、taxonomy）。
2. 阅读根 `AGENTS.md` 和本教程，运行 `python scripts/run_bili_learning.py onboarding` 收集缺失信息。
3. 确定用户选择的宿主；**不要擅自为所有 Agent 安装**。
4. 调用下述安装脚本（默认只读）查看目标和冲突；目标在项目目录之外时，取得用户对该**具体路径**的写入授权。
5. 经授权使用 `-Apply`，脚本自行创建父目录和 Junction，随即验证目标。
6. 若出现 `conflict`，必须停下。不得自动迁移、覆盖或删除已有静态 Skill 或 Junction。
7. 最后验证宿主能读取 canonical `SKILL.md`，并运行项目 `onboarding`。**Skill 可发现与运行环境 ready 是两项独立验收**。

## 3. 唯一 Agent 安装入口

在项目根目录，由 Agent 执行：

```powershell
# 计划，不写用户目录
.\scripts\install_agent_skill.ps1 -Agent Codex
.\scripts\install_agent_skill.ps1 -Agent Hermes
.\scripts\install_agent_skill.ps1 -Agent WorkBuddy
```

经具体目录授权后，仅为用户已选择的 Agent 执行：

```powershell
.\scripts\install_agent_skill.ps1 -Agent Codex -Apply
```

脚本内部复用 `scripts/ensure_junction.ps1`；不用在文档中为每个宿主维护一套 `New-Item` 命令。

### 返回状态

| 状态 | 含义 | 下一步 |
| --- | --- | --- |
| `planned` | 链接尚不存在；这是只读计划 | 确认目标和用户授权后 `-Apply` |
| `installed` | 新链接已建立并验证 | 检查宿主发现 Skill |
| `already_installed` | 原 Junction 已正确指向项目 | 不重复写入 |
| `conflict` | 目标有现有文件夹、不同目标或旧副本 | 保留原状，向用户报告 |
| `failed` | 输入、权限或文件系统操作失败 | 保留现场，修复原因后重试 |

严格区分返回状态，不能把 `planned` 当作已安装。安装脚本不会安装 Python、yt-dlp 或其它 Agent 程序，也不会触碰用户的笔记和 Cookie。

### 被其它宿主注入 PYTHONPATH

canonical Skill 中仅有两种通用 bridge：

```text
skill/bili-learning-automation/scripts/local_bridge.py
skill/bili-learning-automation/scripts/local_bridge.ps1
```

bridge 只处理宿主的路径、Junction 和进程兼容；业务命令统一调用：

```powershell
python <repo-root>\scripts\run_bili_learning.py onboarding
```

## 4. Obsidian 目录映射也由 Agent 执行

新用户配置 `configure-obsidian` 会选择项目内 `notes/bilibili` 作为真实笔记路径；随后 Agent 根据当前 settings 确认：

```text
Source: <repo-root>\notes\bilibili
Target: <vault-root>\bilibili
```

先调用 `ensure_junction.ps1` 只读计划，再在获得外部 Vault 目标目录授权之后 `-Apply`。目标如果已经有普通目录或文件，必须返回冲突并停止，不得覆盖。

这一步和 Agent Skill Junction 都**只进行链接，不搬运或复制原有文件**。不得把项目 notes 反向链接到项目之外。

## 5. 更新 / 重新安装

升级仓库代码时，正确 Junction 会自动引用新的 canonical Skill，不需要再次安装或复制。若宿主缓存旧内容，让 Agent按其实际支持的机制刷新 Skill 或重新进入会话，然后再运行 onboarding。

只有项目根移动、宿主目录变化或链接损坏时，才需要重新规划；不能自动删除用户级目标以“修复”。对于 ChatGPT，核心变更只需更新本地仓库；若 canonical `SKILL.md` 或 ZIP references 有更新，需重新构建并在 ChatGPT 更新专用 ZIP。

## 6. 用户真正需要知道的事

用户不用执行这些命令，只需告诉 Agent：正在使用哪个宿主，是否允许它在其用户级 Skill 目录创建 Junction，Obsidian Vault 在哪里，以及 Bilibili Cookie 文件放在哪里（**仅提供文件路径**）。缺少信息或权限时 Agent 报告 `action_required`，不猜路径、不假装安装成功。
