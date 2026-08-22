# WorkBuddy Skill 安装教程

这份文档用于把项目自带的 **WorkBuddy 薄适配层**安装到本机 WorkBuddy，并保持它与仓库源码同步。

如果 yt-dlp、Cookie、Obsidian 还没有配置，请先看 [新手快速上手](QUICKSTART.md)。

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

先在 PowerShell 进入你实际克隆的项目目录，例如：

```powershell
Set-Location 'G:\GitHub\bili-learning-automation'
```

这里的 `G:\GitHub\...` **只是示例**。项目可以放在任何目录；新版 WorkBuddy Skill 不再依赖这个绝对路径。

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
C:\Users\...\GitHub\bili-learning-automation
D:\AI\bili-learning-automation
G:\GitHub\bili-learning-automation
```

都不需要修改 SKILL.md。

## 5. 第一次使用与 Vault 绑定

在 WorkBuddy 会话中发送：

```text
帮我把这个视频转成学习笔记：
https://www.bilibili.com/video/BVxxxxxxxxxx/
```

如果你还没有配置 Obsidian Vault，核心会返回：

```text
configuration_required
```

这时 WorkBuddy 应询问你的 **Vault 根目录**，也就是直接包含 `.obsidian` 的目录，例如：

```text
D:\Notes\MyVault
```

它随后通过共享配置入口写入：

```json
{
  "vault_root": "D:\\Notes\\MyVault",
  "notes_subdir": "bilibili"
}
```

然后重新执行刚才的视频请求。

这个设计避免第三方用户首次使用时把私人笔记静默写进克隆仓库内部。

如果你希望使用自己的 Vault 目录体系，也可以明确告诉 WorkBuddy，例如：

```text
我的 Vault 是 D:\Notes\MyVault，B站笔记放到 03-Resources\Bilibili
```

此时 `notes_subdir` 可以使用 `03-Resources\Bilibili`。

## 6. CSS 需要另外安装吗

需要把仓库中的：

```text
obsidian\snippets\learning-lab.css
obsidian\snippets\video-note.css
```

放到：

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

同一个 BV 号如果已经由某个入口启动，其他入口再次请求会收到：

```text
in_progress
```

这是共享 reservation 的并发保护。不要为了让第二个入口强行继续而手工删除 reservation 或 lock。

## 8. 更新仓库以后怎么办

如果 WorkBuddy 适配层通过 Junction 安装，更新仓库后它直接看到新文件。

通常只需要：

```powershell
git pull
```

然后重新开启 / 刷新 WorkBuddy 会话，让它重新读取当前 Skill。

不需要重新复制适配层，也不需要重新修改项目绝对路径。

如果 CSS 有版本更新，是否覆盖 Vault 中已有 CSS 应由用户明确决定。

## 9. WorkBuddy 特有的 `PYTHONPATH` 问题

WorkBuddy 的 Bash 环境可能注入自己的 safe-delete Python 垫片。它会影响 runtime 清理，因此所有调用都先进入 `bridge.ps1`；该启动壳会清除 `PYTHONPATH`，并优先使用项目自己的 `.venv`：

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$runner" ...
```

普通用户不需要自己修改核心 `cleanup_job`、finalizer 或删除策略。

如果出现：

- collector 已采集完成但清理报错；
- finalizer 已发布但 runtime 还在；
- Python 环境相关错误；

优先让 WorkBuddy 重新读取当前适配层，再运行 doctor。不要手工批量删除 job、reservation 或 lock。

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
