# 本地 Agent Skill 安装

Codex、Hermes 与 WorkBuddy 共用同一个本地 Skill 真源，不再维护宿主专用副本。

## 统一真源

项目内唯一需要人工维护的 Skill：

```text
<repo-root>\skill\bili-learning-automation
```

三个本地 Agent 都通过 Windows Junction 直接指向这个目录：

| Agent | 安装目录 |
| --- | --- |
| Hermes | `%LOCALAPPDATA%\hermes\skills\bili-learning-automation` |
| WorkBuddy | `%USERPROFILE%\.workbuddy\skills\bili-learning-automation` |
| Codex | `%USERPROFILE%\.agents\skills\bili-learning-automation` |

更新仓库后，三个 Agent 会直接读取最新的 canonical Skill，不需要重新复制、同步或重新打包本地 Skill。

ChatGPT Web 不使用 Junction，单独安装 `dist\bili-learning-automation-chatgpt.zip`。详见 [ChatGPT Skill 安装教程](CHATGPT-SKILL-INSTALL.md)。

## 创建 Junction

先进入实际项目根目录：

```powershell
Set-Location '<repo-root>'
$source = (Resolve-Path '.\skill\bili-learning-automation').Path
```

### Hermes

```powershell
$target = Join-Path $env:LOCALAPPDATA 'hermes\skills\bili-learning-automation'
New-Item -ItemType Junction -Path $target -Target $source
```

### WorkBuddy

```powershell
$target = Join-Path $HOME '.workbuddy\skills\bili-learning-automation'
New-Item -ItemType Junction -Path $target -Target $source
```

### Codex

```powershell
$parent = Join-Path $HOME '.agents\skills'
New-Item -ItemType Directory -Path $parent -Force | Out-Null
$target = Join-Path $parent 'bili-learning-automation'
New-Item -ItemType Junction -Path $target -Target $source
```

如果目标已经存在，不要直接覆盖。先检查：

```powershell
Get-Item $target | Format-List FullName,LinkType,Target
```

只有确认它是旧的 `bili-learning-automation` Junction 或旧静态副本后，才迁移到 canonical Skill。

## 验证安装

正确状态应满足：

1. `LinkType` 是 `Junction`；
2. `Target` 指向 `<repo-root>\skill\bili-learning-automation`；
3. 通过安装路径能读取 `SKILL.md`；
4. 运行 onboarding 返回 `ready`，才表示当前机器可直接使用。

统一 Skill 名称：

```text
bili-learning-automation
```

因此三个本地 Agent 不再使用：

```text
bili-learning-automation-codex
bili-learning-automation-hermes
bili-learning-automation-workbuddy
```

## 统一 bridge

canonical Skill 自带：

```text
skill\bili-learning-automation\scripts\local_bridge.py
skill\bili-learning-automation\scripts\local_bridge.ps1
```

它们只解决 Junction、Python、`PYTHONPATH` 与宿主进程兼容，不拥有业务规则。

普通情况下仍优先调用共享入口：

```powershell
python <repo-root>\scripts\run_bili_learning.py <command> [args]
```

如果宿主从 Skill 安装目录启动、注入了不兼容的 `PYTHONPATH`，或需要让 runtime cleanup runner 保持稳定，可以通过安装 Skill 中的 bridge 调用同一核心：

```powershell
.\scripts\local_bridge.ps1 onboarding
```

或：

```powershell
python .\scripts\local_bridge.py onboarding
```

bridge 会从真实 Skill 位置定位项目根目录，并进入同一个 `src\bili_learning` 核心。

## 更新

项目升级只需要更新仓库：

```powershell
git pull
```

Junction 不需要重建。只有下面情况才需要重新安装链接：

- 项目根目录被移动；
- Skill 真源目录被重命名；
- Agent 的用户级 Skill 目录发生变化；
- Junction 被手动删除或损坏。

仓库内 `SKILL.md` / `AGENTS.md` 发生重大更新后，**不要重新复制或重装 Skill**；Junction 已经指向最新文件。旧会话可能缓存此前规则，推荐新建会话或执行宿主的 Skill reload，然后重新运行 onboarding。ChatGPT Web 不使用 Junction，需重新构建并由用户手动更新 ZIP。

## 故障排查

### Agent 看不到 Skill

先检查 Junction：

```powershell
Get-Item '<agent-skill-path>' | Format-List FullName,LinkType,Target
```

再确认：

```text
<agent-skill-path>\SKILL.md
```

存在。

### Skill 能看到但不能运行

从项目根目录运行：

```powershell
python .\scripts\run_bili_learning.py onboarding
```

如果返回 `action_required`，按返回的缺失项处理。Skill 被发现与运行环境 ready 是两个独立状态。

### WorkBuddy 的 PowerShell / PYTHONPATH 问题

优先通过：

```text
<workbuddy-skill-path>\scripts\local_bridge.ps1
```

bridge 会清除宿主注入的 `PYTHONPATH`，优先使用项目自己的 `.venv\Scripts\python.exe`，然后调用统一 Python 核心。

## 维护原则

- 本地 Agent 只维护一个 canonical `SKILL.md`。
- 不在仓库生成 `.agents/skills`、`hermes-skills`、`workbuddy-skills` 副本。
- 不为本地 Agent 生成宿主专用 ZIP。
- ChatGPT Web ZIP 是唯一需要构建的 Skill 分发包。
- Cookie、`config/local.json`、runtime 与私人笔记永远不进入 Skill 包。
