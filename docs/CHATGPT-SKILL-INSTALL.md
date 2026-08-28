# ChatGPT Skill 安装教程

这份文档用于把项目的 ChatGPT 专用薄适配层安装到 ChatGPT Work。它不会把 Hermes、WorkBuddy 或 Codex Skill 一起装入，也不会把本机核心代码、Cookie 和私人笔记上传到 ChatGPT。

## 1. 先理解运行边界

ChatGPT Skill 只负责：

- 识别用户意图；
- 通过已连接的本地工作区桥接打开项目；
- 调用共享 `bili-learning` 核心；
- 读取当前 Job 来源并完成笔记 AI 区域；
- 调用 finalizer 发布。

ChatGPT 网页或桌面端的远程沙箱不能直接访问本机 Windows 盘符目录。要完成端到端笔记流程，必须连接一个能够打开工作区、读写文本文件并运行项目命令的本地桥接工具。已安装 CodexPro 时可直接使用；其他环境可使用具备等价能力的受信任桥接。

如果没有本地桥接，Skill 可以安装成功，但不能把本机 B站资料写入 Obsidian。

## 2. 专用 Skill 源码

ChatGPT 适配层只有一份：

```text
<repo-root>\chatgpt-skills\bili-learning-automation-chatgpt
```

该目录包含且只包含一个 `SKILL.md`，名称为：

```text
bili-learning-automation-chatgpt
```

Hermes、WorkBuddy 和 Codex 的 Skill 不会进入 ChatGPT ZIP。

## 3. 生成独立 ZIP

在项目根目录运行：

```powershell
python .\scripts\build_agent_skill_packages.py
```

成功后生成：

```text
<repo-root>\dist\bili-learning-automation-chatgpt.zip
<repo-root>\dist\bili-learning-automation-codex.zip
<repo-root>\dist\bili-learning-automation-hermes.zip
<repo-root>\dist\bili-learning-automation-workbuddy.zip
```

安装 ChatGPT 时只选择：

```text
bili-learning-automation-chatgpt.zip
```

打包脚本使用白名单，只允许 Skill 的 `SKILL.md`、`agents`、`assets`、`references` 和 `scripts`。它还会拒绝嵌套 `SKILL.md`、Cookie、本机配置和 Python 缓存。

不要把整个仓库压缩后上传。Git 忽略只能阻止文件被提交，不能阻止手工压缩包包含 `key/`、`config/local.json`、`.runtime/` 或私人笔记。

## 4. 清理旧的重复安装

如果 ChatGPT 的“插件 → 技能”中同时出现 Hermes 版和 WorkBuddy 版：

1. 分别打开这两个旧条目；
2. 在界面中卸载或移除；
3. 不要删除本机 Hermes / WorkBuddy 的 Junction；
4. 确认旧条目不再显示后，再安装新的 ChatGPT ZIP。

旧重复条目的典型特征是名称相同，但说明分别出现 Hermes 或 WorkBuddy。

## 5. 在 ChatGPT 中安装

1. 打开左侧“插件”；
2. 进入“技能”；
3. 选择通过 ZIP 安装；
4. 上传 `bili-learning-automation-chatgpt.zip`；
5. 安装完成后确认只出现一个：

```text
B站视频转笔记 · ChatGPT
```

不要把 Codex ZIP 也安装到 ChatGPT 的技能页面。

## 6. 第一次验收

先连接并授权本地工作区桥接，然后在新对话中调用该 Skill：

```text
请使用 bili-learning-automation-chatgpt 检查本地项目连接、Skill 安装状态和运行环境，暂时不要转换视频。
```

正确验收分为三层：

1. **Skill 已安装**：ChatGPT 能读取专用 `SKILL.md`；
2. **本地桥接已连接**：ChatGPT 能打开克隆的项目并读取根目录 `AGENTS.md`；
3. **运行环境已就绪**：共享 onboarding 返回 `ready`。

只有三层都通过，才能说“当前可以直接使用”。如果 onboarding 返回 `action_required`，只处理返回的 Vault、Cookie 路径、yt-dlp 等实际缺失项。Cookie 只提供文件路径，不把内容发到对话。

## 7. 日常使用

安装和验收通过后，可直接调用 Skill 并发送 Bilibili 链接或 BV 号。ChatGPT 会通过本地桥接运行：

```powershell
python scripts/run_bili_learning.py <command> [args]
```

所有 runtime、草稿和正式笔记仍保留在本机；ChatGPT 不应把这些文件复制到远程沙箱。

## 8. 更新

ChatGPT 通过 ZIP 安装的是副本，不会随着仓库 `git pull` 自动更新。项目更新后：

1. 重新运行打包脚本；
2. 检查生成结果；
3. 在 ChatGPT 中更新或重新安装新的 ChatGPT ZIP；
4. 新建对话重新做一次安装与 onboarding 验收。

如果使用的 ZIP 曾经由整个本地仓库手工制作，应检查是否包含凭据或本机配置。若包含 Bilibili Cookie，应移除该安装包并重新导出 Cookie。
