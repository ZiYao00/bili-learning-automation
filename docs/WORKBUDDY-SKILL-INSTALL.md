# WorkBuddy Skill 安装教程

这份文档用于把项目自带的 **WorkBuddy 适配层**安装到本机 WorkBuddy，并保持它和仓库源码同步。

如果 yt-dlp、Cookie、Obsidian 还没有配置，请先看 [新手快速上手](QUICKSTART.md)。

---

## 1. WorkBuddy 适配层在哪里

源码目录：

```text
<project-root>\workbuddy-skills\bili-learning-automation
```

它只是 WorkBuddy 的入口适配层。

真正的：

- collector；
- transcript；
- taxonomy；
- finalizer；
- 笔记标准；

仍然使用项目共享核心，不会单独复制一套实现。

---

## 2. 推荐使用 Junction 安装

WorkBuddy Skill 目录：

```text
~\.workbuddy\skills\
```

推荐结构：

```text
~\.workbuddy\skills\bili-learning-automation
        ↓ Junction
<project-root>\workbuddy-skills\bili-learning-automation
```

这样以后更新仓库，不需要再手工复制 WorkBuddy Skill。

---

## 3. Windows 安装示例

假设项目位于：

```text
G:\GitHub\bili-learning-automation
```

先确认源码存在：

```powershell
Test-Path 'G:\GitHub\bili-learning-automation\workbuddy-skills\bili-learning-automation'
```

应该返回：

```text
True
```

然后设置路径：

```powershell
$source = 'G:\GitHub\bili-learning-automation\workbuddy-skills\bili-learning-automation'
$target = Join-Path $HOME '.workbuddy\skills\bili-learning-automation'
```

如果目标不存在，可以创建 Junction：

```powershell
New-Item -ItemType Junction -Path $target -Target $source
```

如果目标已经存在，先检查：

```powershell
Get-Item $target | Format-List FullName,LinkType,Target
```

不要在不了解现有内容时直接删除旧目录。

---

## 4. 安装完成后检查什么

正确状态应该类似：

```text
FullName : C:\Users\<你>\.workbuddy\skills\bili-learning-automation
LinkType : Junction
Target   : {G:\GitHub\bili-learning-automation\workbuddy-skills\bili-learning-automation}
```

重点确认：

```text
LinkType = Junction
Target   = 当前仓库的 workbuddy-skills/bili-learning-automation
```

---

## 5. 第一次使用

在 WorkBuddy 会话中明确发送一个 B站链接或 BV 号，例如：

```text
帮我把这个视频转成学习笔记：
https://www.bilibili.com/video/BVxxxxxxxxxx/
```

WorkBuddy 会调用项目共享流程。

正常情况下你不需要：

- 手工运行 collector；
- 手工拆字幕；
- 手工创建 transcript；
- 手工执行 finalizer；
- 手工移动最终笔记。

---

## 6. WorkBuddy 和 Hermes 会不会互相影响

不会，只要它们都使用当前项目的薄适配层。

结构可以理解为：

```text
Hermes ─────┐
WorkBuddy ──┼→ bili-learning core → Obsidian
Codex ──────┘
```

同一个 BV 号如果已经由某个入口启动，其他入口再次请求时会收到：

```text
in_progress
```

这是共享 reservation 的并发保护。

不要为了让第二个入口强行继续而手工删除 reservation 或 lock。

---

## 7. 更新仓库以后怎么办

如果 WorkBuddy 适配层通过 Junction 安装，更新仓库后它看到的就是新文件。

通常只需要：

```powershell
git pull
```

然后重新开启 / 刷新 WorkBuddy 会话，让它重新读取当前 Skill。

不需要把适配层再复制一次。

---

## 8. 一个 WorkBuddy 特有注意点

WorkBuddy 的执行环境可能带有自己的 Python / Bash 安全垫片。

项目适配层已经负责规避这些平台差异，普通用户不要为了“让脚本能删 runtime”而自行修改核心 `cleanup_job`、finalizer 或删除策略。

如果出现：

- collector 已经采集完成但清理报错；
- finalizer 已发布但 runtime 还在；
- WorkBuddy 报 Python 环境相关错误；

优先让 WorkBuddy 重新读取当前适配层规则，再检查项目 doctor 和任务状态，不要手工批量删除 job。

---

## 9. 相关文档

- [新手快速上手](QUICKSTART.md)
- [配置说明](CONFIGURATION.md)
- [故障排查](TROUBLESHOOTING.md)
- [智能体接入协议](AGENT-INTEGRATION.md)
