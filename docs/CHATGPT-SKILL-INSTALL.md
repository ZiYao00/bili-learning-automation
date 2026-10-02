# ChatGPT Skill 安装教程

ChatGPT Web 使用项目唯一的独立 Skill ZIP。本地 Codex、Hermes、WorkBuddy 不使用该 ZIP，它们通过 Junction 直接安装 canonical Skill。

## 1. 运行边界

ChatGPT Skill 负责识别意图、通过已授权的本地工作区桥接访问项目、调用共享 `bili-learning` 核心、读取当前 Job 来源并完成笔记 AI 区域，最后调用 finalizer 发布。

ChatGPT 远程沙箱不能直接访问本机 Windows 项目。端到端运行必须连接能够打开工作区、读写文本文件并运行项目命令的本地桥接；已连接 CodexPro 时可直接使用。

没有本地桥接时，Skill 可以安装，但不能操作本机项目或 Obsidian。

## 2. 真源与安装包

唯一人工维护的本地 Skill：

```text
<repo-root>\skill\bili-learning-automation
```

ChatGPT 构建器：

```text
<repo-root>\scripts\build_chatgpt_skill.py
```

它生成：

```text
<repo-root>\dist\bili-learning-automation-chatgpt.zip
```

包内只有：

```text
bili-learning-automation-chatgpt/
├── SKILL.md
├── agents/
│   └── openai.yaml
└── references/
    └── <批准的公开项目文档快照>
```

不包含 Python core、local bridge、Cookie、`config/local.json`、runtime 或私人笔记。references 只是构建时快照；连接本地项目后，以根目录 `AGENTS.md`、当前 Job `agent_handoff.md` 与本地项目文档为运行事实源。

## 3. 构建与检查

在项目根目录运行：

```powershell
python .\scripts\build_chatgpt_skill.py --check
python .\scripts\build_chatgpt_skill.py
```

成功后只需要上传：

```text
dist\bili-learning-automation-chatgpt.zip
```

不要手工压缩整个仓库。Git ignore 只能阻止文件被提交，不能阻止手工 ZIP 把本机私有文件打进去。

## 4. 安装

在 ChatGPT 的插件 / 技能界面通过 ZIP 安装：

```text
bili-learning-automation-chatgpt.zip
```

安装后应看到：

```text
B站视频转笔记 · ChatGPT
```

如果历史上安装过 Hermes、WorkBuddy、Codex 的静态 Skill 副本，可在 ChatGPT 中移除那些旧条目；不要因此删除本机 Agent 的 Junction。

## 5. 第一次验收

先连接并授权本地工作区桥接，然后在新对话中要求：

```text
请使用 bili-learning-automation-chatgpt 检查本地项目连接、Skill 安装状态和运行环境，暂时不要转换视频。
```

正确验收分三层：

1. **Skill 已安装**：ChatGPT 能读取专用 `SKILL.md`；
2. **本地桥接已连接**：ChatGPT 能打开项目并读取根目录 `AGENTS.md`；
3. **运行环境 ready**：共享 onboarding 返回 `ready`。

只有三层都通过，才表示可以直接生成笔记。Cookie 只提供文件路径，不把内容发送到聊天。

## 6. 日常使用

ChatGPT 通过本地桥接调用共享入口：

```powershell
python scripts/run_bili_learning.py <command> [args]
```

所有 runtime、草稿和正式笔记都留在本机，不复制到远程沙箱。

## 7. 什么时候需要重新安装 ZIP

普通 Python core、collector、taxonomy、finalizer 等更新只需要更新本地仓库。

下列内容变化时重新构建并安装 ZIP：

- `skill/bili-learning-automation/SKILL.md`；
- ChatGPT 专用 metadata / 宿主边界；
- 希望刷新 ZIP 内的 references 文档快照。

流程：

```powershell
python .\scripts\build_chatgpt_skill.py --check
python .\scripts\build_chatgpt_skill.py
```

然后在 ChatGPT 中更新或重新安装新的 ZIP，并在新对话重新做一次本地桥接与 onboarding 验收。
