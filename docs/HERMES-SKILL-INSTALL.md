# Hermes Skill 安装教程

这份文档只讲一件事：**怎样让 Hermes 正确加载 `B站视频转笔记` Skill，并且以后更新仓库时自动使用最新版。**

如果你还没有配置 yt-dlp、Cookie 或 Obsidian，请先看 [新手快速上手](QUICKSTART.md)；如果卡在 Cookie 获取，直接看 [Bilibili Cookie 获取与安全配置](BILIBILI-COOKIE.md)。

---

## 1. 先理解安装方式

项目里的 Hermes Skill 源码只有一份：

```text
<project-root>\hermes-skills\bili-learning-automation
```

Hermes 默认从这里加载用户 Skill：

```text
%LOCALAPPDATA%\hermes\skills\
```

推荐做法不是复制一份，而是创建 **Windows Junction**：

```text
%LOCALAPPDATA%\hermes\skills\bili-learning-automation
        ↓ Junction
<project-root>\hermes-skills\bili-learning-automation
```

这样以后 `git pull` 或本地更新项目后，Hermes 看到的就是同一份源码，不会出现“仓库已经更新，但 Hermes 还在用旧副本”的问题。

---

## 2. 确认项目目录

以下示例使用 `<repo-root>` 表示你实际克隆的项目根目录：

```text
<repo-root>
```

如果你的项目在其他位置，把路径替换成自己的即可。

先确认源目录存在：

```powershell
Test-Path '<repo-root>\hermes-skills\bili-learning-automation'
```

应该返回：

```text
True
```

---

## 3. 检查 Hermes 目标目录

目标位置：

```powershell
$target = "$env:LOCALAPPDATA\hermes\skills\bili-learning-automation"
Get-Item $target -ErrorAction SilentlyContinue | Format-List FullName,LinkType,Target
```

### 如果目标不存在

可以直接创建 Junction：

```powershell
$source = '<repo-root>\hermes-skills\bili-learning-automation'
$target = "$env:LOCALAPPDATA\hermes\skills\bili-learning-automation"
New-Item -ItemType Junction -Path $target -Target $source
```

### 如果目标已经存在

先不要直接删除。

先看：

```powershell
Get-Item $target | Format-List FullName,LinkType,Target
```

正确状态应该类似：

```text
FullName : C:\Users\<你>\AppData\Local\hermes\skills\bili-learning-automation
LinkType : Junction
Target   : {<repo-root>\hermes-skills\bili-learning-automation}
```

如果它已经指向当前仓库，就不需要再安装。

如果它是普通目录、旧副本或指向旧项目，先备份并确认旧目录用途，再重新建立 Junction；不要在不清楚内容的情况下批量删除。

---

## 4. 验证 Hermes 是否识别 Skill

运行：

```powershell
hermes skills list
```

应该能看到：

```text
bili-learning-automation
```

并且状态为启用 / enabled。

如果没有看到，优先检查：

1. Junction 路径是否正确；
2. 目标目录里是否有 `SKILL.md`；
3. Hermes Home 是否确实使用 `%LOCALAPPDATA%\hermes`；
4. 当前 Gateway 是否还没有重新加载 Skill。

---

## 5. 更新 Skill 后怎么让 Hermes 立即生效

如果 Gateway 或微信会话已经在运行，在 Hermes 会话里发送：

```text
/reload-skills
```

Hermes 会重新扫描本地 Skill。

因为使用的是 Junction，所以通常**不需要**：

- 再复制一次 `SKILL.md`；
- 再安装一份 Skill；
- 重建项目目录。

如果 Hermes 主程序本身刚升级、配置也有改动，重启一次 Gateway 会更稳妥。

---

## 6. 怎么确认现在读到的是最新版

最简单的方式是让 Hermes 重新读取当前安装的 Skill，并确认几个版本特征。

例如发送：

```text
请重新读取当前已安装的 bili-learning-automation SKILL.md，
不要根据之前对话记忆回答。
确认当前是否包含：
1. transcript_manifest_path
2. direct / chunked
3. agent_work_dir
4. in_progress 可安全续做陈旧未完成 job
5. 单个 transcript chunk 优先一次完整读取
```

如果这些规则都存在，说明当前加载的是新版 Skill。

也可以直接检查安装目录：

```powershell
Get-Content "$env:LOCALAPPDATA\hermes\skills\bili-learning-automation\SKILL.md" -Encoding UTF8
```

由于 Junction 指向仓库源码，这个文件应与：

```text
<project-root>\hermes-skills\bili-learning-automation\SKILL.md
```

完全一致。

---

## 7. 第一次测试

安装完成后，在允许的 Hermes owner 私聊里直接发送：

```text
https://www.bilibili.com/video/BVxxxxxxxxxx/
```

正常流程应该是：

```text
识别项目
→ collector
→ 首次未绑定 Vault 时返回 configuration_required
→ owner 提供包含 .obsidian 的 Vault 根目录并完成配置
→ collector 重试
→ materials_ready
→ 读取 transcript manifest
→ 阅读字幕
→ 生成 knowledge_outline
→ 写笔记
→ coverage review
→ finalizer
→ 回复完成
```

你不需要先输入命令前缀。

---

## 8. `in_progress` 是什么意思

如果同一个 BV 号已经有任务在处理，collector 会返回：

```text
in_progress
```

这是并发保护，不是错误，也不代表这个视频永久不能再次转换。

新版 Hermes 适配层会：

- 不重复采集同一个活动任务；
- 如果返回了绑定 `job_dir`，且任务已经明显陈旧、仍未开始写作、所需文件完整，则安全续做同一个 job；
- 正常活动任务不抢占；
- 只有状态异常时才运行 doctor；
- 不手工删除 job、reservation 或锁文件。

当前 job 正常结束并被 finalizer 清理后，同一个 BV 号仍然可以重新转换。

---

## 9. Hermes 更新以后要不要重新安装 Skill

通常不用。

只要 Junction 仍然正确：

```text
Hermes skills 目录
→ 当前仓库 hermes-skills/bili-learning-automation
```

Hermes 主程序升级不会改变项目中的 Skill 源码。

升级后建议做三项检查：

```powershell
hermes skills list
```

然后在会话发送：

```text
/reload-skills
```

最后发一条测试 BV / 链接确认完整流程能跑通。

---

## 10. 常见问题

### Hermes 说找不到项目

检查 Junction 的 `Target` 是否仍指向当前仓库。

### 仓库更新了，但 Hermes 汇报还是旧规则

先发送：

```text
/reload-skills
```

再让 Hermes 明确“重新读取当前安装的 `SKILL.md`，不要根据会话记忆回答”。

### Hermes 能读 Skill，但任务没有继续执行

先确认 Hermes 自身模型 / Agent 配置和 Gateway 是否正常，再运行项目 doctor。不要为了这个问题修改核心笔记规则或绕过 finalizer。

### Skill 内容正确，但 Obsidian 没有样式

这是 CSS 安装问题，不是 Hermes Skill 问题。看 [Obsidian 样式教程](OBSIDIAN-STYLING.md)。

### collector 返回 `ytdlp_not_configured`

说明当前电脑没有检测到 yt-dlp。Hermes 只应提示 owner 运行：

```powershell
winget install yt-dlp
```

Hermes 不自动安装，也不要把 `yt-dlp.exe` 复制到 Skill 或仓库。安装完成后重新发送原链接即可；自定义安装位置才需要单独配置 `ytdlp`。

### collector 返回 `subtitle_unavailable`

表示没有取得可用中文字幕。默认流程不会下载视频转 ASR。看 [故障排查](TROUBLESHOOTING.md)。

---

## 11. 安装完成后的正确状态

最终你只需要记住这一点：

```text
仓库里的 Skill = Hermes 实际读取的 Skill
```

推荐结构：

```text
<repo-root>\
└── hermes-skills\bili-learning-automation\
    └── SKILL.md

%LOCALAPPDATA%\hermes\skills\bili-learning-automation
└── Junction → 上面的源码目录
```

这样后续维护最简单，也最不容易出现版本漂移。
