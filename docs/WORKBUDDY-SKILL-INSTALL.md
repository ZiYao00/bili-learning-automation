# WorkBuddy Skill 安装教程

这份文档用于把项目自带的 **WorkBuddy 薄适配层**安装到本机 WorkBuddy，并保持它与仓库源码同步。

如果 yt-dlp、Cookie、Obsidian 还没有配置，请先看 [新手快速上手](QUICKSTART.md)；如果卡在 Cookie 获取，直接看 [Bilibili Cookie 获取与安全配置](BILIBILI-COOKIE.md)。

## 1. WorkBuddy 适配层在哪里

源码目录：

```text
<project-root>\workbuddy-skills\bili-learning-automation
```

它只负责：

- WorkBuddy 会话触发；
- 调用 `scripts/bridge.py`；
- 处理 WorkBuddy 特有的 Bash / `PYTHONPATH` 差异；
- 把状态翻译成用户可理解的回复。

真正的 collector、transcript、taxonomy、finalizer、配置解析与笔记标准仍由共享核心负责。

## 2. 推荐使用 Junction 安装

WorkBuddy Skill 目录：

```text
%USERPROFILE%\.workbuddy\skills\
```

推荐结构：

```text
%USERPROFILE%\.workbuddy\skills\bili-learning-automation
        ↓ Junction
<project-root>\workbuddy-skills\bili-learning-automation
```

这样以后更新仓库，不需要再次复制 WorkBuddy Skill。

## 3. Windows 安装

先在 PowerShell 进入你实际克隆的项目目录：

```powershell
Set-Location '<repo-root>'
```

将 `<repo-root>` 替换为你的实际路径。项目可以放在任何目录；新版 WorkBuddy Skill 不依赖固定绝对路径。

然后：

```powershell
$source = Join-Path (Get-Location) 'workbuddy-skills\bili-learning-automation'
$target = Join-Path $HOME '.workbuddy\skills\bili-learning-automation'
Test-Path $source
```

确认返回 `True` 后，如果目标不存在：

```powershell
New-Item -ItemType Junction -Path $target -Target $source
```

如果目标已经存在，先检查：

```powershell
Get-Item $target | Format-List FullName,LinkType,Target
```

不要在不了解现有内容时直接删除旧目录。

正确状态类似：

```text
FullName : C:\Users\<你>\.workbuddy\skills\bili-learning-automation
LinkType : Junction
Target   : {<project-root>\workbuddy-skills\bili-learning-automation}
```

## 4. 为什么现在不需要写死项目路径

适配层包含：

```text
workbuddy-skills\bili-learning-automation\scripts\bridge.ps1
workbuddy-skills\bili-learning-automation\scripts\bridge.py
```

WorkBuddy 实际调用的是安装目录中的 bridge：

```bash
$HOME/.workbuddy/skills/bili-learning-automation/scripts/bridge.ps1
```

`bridge.ps1` 负责解析 Junction、优先选择项目 `.venv` 并清除 WorkBuddy 注入的 `PYTHONPATH`；随后 `bridge.py` 使用真实源码位置调用共享核心。路径解析关系是：

```text
当前 WorkBuddy Skill
→ workbuddy-skills
→ 项目根目录
→ src/bili_learning
```

因此仓库无论位于：

```text
<repo-root>
```

都不需要修改 SKILL.md。

## 5. 安装完成后：先做一次可用性验收

WorkBuddy 能读取 `SKILL.md`、目录链接有效，只能证明 **Skill 已安装**，还不能证明当前电脑已经可以生成笔记。

安装后可以直接在新的 WorkBuddy 会话里说：

```text
请读取 bili-learning-automation Skill，检查安装状态，并确认当前是否已经可以直接使用。
```

新版 Skill 会先检查安装入口，再运行统一 onboarding，并分别反馈：

```text
Skill 安装状态
运行环境状态
```

只有 onboarding 返回 `ready`，才应告诉你“当前可以直接使用”。它会检查 Python、yt-dlp、Bilibili Cookie、Obsidian Vault 与 CSS；Cookie 只检查配置与文件存在，不读取或展示内容。

如果返回 `action_required`，WorkBuddy 会只处理真正缺失的项目，例如：

- Vault 未配置：询问直接包含 `.obsidian` 的 Vault 根目录；
- Cookie 未配置：只询问 Netscape Cookie **文件路径**；不知道如何获取时看 [Bilibili Cookie 获取与安全配置](BILIBILI-COOKIE.md)；
- yt-dlp 未检测到：Windows 默认提示 `winget install yt-dlp`；
- CSS 缺失：提醒安装，但不阻塞笔记生成。

配置完成后会重新运行 onboarding。这样不会出现“Skill 链接已经健康，但第一次真正发视频时才发现环境没准备好”的情况。

如果你希望使用自己的 Vault 目录体系，也可以明确告诉 WorkBuddy，例如：

```text
我的 Vault 是 D:\Notes\MyVault，B站笔记放到 03-Resources\Bilibili
```

此时 `notes_subdir` 可以使用 `03-Resources\Bilibili`。

## 6. CSS 需要另外安装吗

需要把共享 <https://github.com/ZiYao00/obsidian-learning-snippets> 中、由 `config\obsidian-style.json` 声明的 `learning-lab.css` 与 `video-note.css` 放到：

```text
<vault_root>\.obsidian\snippets\
```

并在 Obsidian：

```text
设置 → 外观 → CSS 代码片段
```

同时启用 `learning-lab` 和 `video-note`。

WorkBuddy 可以通过 doctor 检测这两份 CSS 是否存在，但**不会静默覆盖**用户已经修改过的 CSS。完整教程见 [Obsidian 样式](OBSIDIAN-STYLING.md)。

## 7. WorkBuddy 和 Hermes 会不会互相影响

不会，只要都使用当前项目的薄适配层：

```text
Hermes ─────┐
WorkBuddy ──┼→ bili-learning core → Obsidian
Codex ──────┘
```

同一个 BV 号如果仍由某个入口真实运行，其他入口再次请求会收到：

```text
in_progress
```

这是共享 reservation 的并发保护。reservation 使用 `active / released` 状态，并由 OS 文件锁保证 claim / bind / release 原子性。

如果原持有进程已经退出但采集材料完整，核心会直接恢复原 Job，必要时重建 `agent_handoff.md`，并返回：

```text
materials_ready
recovered: true
```

此时 WorkBuddy 直接继续写作，不会重新运行 yt-dlp。不要为了让第二个入口强行继续而手工删除 reservation、lock 或 Job。

## 8. 更新仓库以后怎么办

如果 WorkBuddy 适配层通过 Junction 安装，更新仓库后它直接看到新文件。

通常只需要：

```powershell
git pull
```

然后重新开启 / 刷新 WorkBuddy 会话，让它重新读取当前 Skill。

不需要重新复制适配层，也不需要重新修改项目绝对路径。

如果 CSS 有版本更新，是否覆盖 Vault 中已有 CSS 应由用户明确决定。

## 9. WorkBuddy 的 safe-delete、PowerShell 与 MSYS 路径兼容

WorkBuddy 的 Bash 环境可能注入 safe-delete Python 垫片，也可能直接阻止 `powershell.exe`。当前适配层按下面的顺序处理：

1. 正常优先调用安装 Skill 中的 `bridge.ps1`；它会清除注入的 `PYTHONPATH`，并优先使用项目自己的 `.venv`；
2. 如果 WorkBuddy 沙箱明确阻止 `powershell.exe`，则解析已安装 Junction 的真实目标，直接使用仓库 `.venv\Scripts\python.exe` 调用同一适配层的 `bridge.py`；
3. 如果当前 Bash 把 Windows 路径表示成 `/g/...` 一类 MSYS 路径，先转换为真实 Windows 路径再交给 Windows Python，不能手工拼接盘符。

新版核心同时取消了正常业务链对 delete 权限的依赖：

- 文件锁使用 OS 原生锁，锁文件不需要 `unlink()`；
- reservation 使用 `active / released` 状态，不靠删除文件释放；
- 完整的死进程 Job 由核心直接恢复，不重新采集；
- Job 完成后 retire 到 `.runtime/bilibili-learning/retired/`；
- `note_ready` 与 runtime retire/维护状态解耦；
- 发布 staging 保留在 Job 内，不要求发布后删除临时文件。

因此 WorkBuddy 返回的 `windows-sandbox-recycle-bin-unavailable` 不应再让当前版本的 `prepare → 写作 → finalize` 主链失败。本轮修复已经通过 WorkBuddy 实机链接转换测试。

如果最新版本仍因 safe-delete 中断：

- 先确认仓库已更新、Junction 指向当前仓库、当前会话已重新读取最新 `SKILL.md`；
- 再运行 doctor 检查环境；
- **不要修改 WorkBuddy 内置 `sitecustomize.py`，不要为了兼容本项目关闭全局安全保护，也不要手工批量删除 job、reservation 或 lock。**

## 10. 诊断

WorkBuddy 适配层使用统一 doctor：

```bash
runner="$HOME/.workbuddy/skills/bili-learning-automation/scripts/bridge.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" doctor --json
```

重点关注：

- `notes_repository_fallback`：还没有显式绑定 Vault；
- `obsidian_vault_detected`：Vault 根是否正确；
- `obsidian_snippet_learning_lab`；
- `obsidian_snippet_video_note`；
- `ytdlp_not_configured`：只提示 `winget install yt-dlp`，WorkBuddy 不自动安装，也不向 Skill 复制 exe；
- Cookie / 写权限检查。

## 相关文档

- [新手快速上手](QUICKSTART.md)
- [配置说明](CONFIGURATION.md)
- [Obsidian 样式](OBSIDIAN-STYLING.md)
- [故障排查](TROUBLESHOOTING.md)
- [智能体接入协议](AGENT-INTEGRATION.md)
