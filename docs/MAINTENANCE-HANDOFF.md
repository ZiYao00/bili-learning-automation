# Maintenance Handoff

本文件给第一次接手 `bili-learning-automation` 的 Agent / 开发者使用。目标是让接手者在不依赖历史聊天的情况下，快速理解当前架构、数据边界和验证流程。

## 1. 接手时先读什么

按顺序阅读：

1. 项目根 `AGENTS.md`：当前运行规则与安全边界；
2. `skill/bili-learning-automation/SKILL.md`：本地 Agent 的唯一 canonical Skill；
3. 本文件：架构与维护交接；
4. 按任务读取：
   - `docs/ARCHITECTURE.md`
   - `docs/CONFIGURATION.md`
   - `docs/AGENT-INTEGRATION.md`
   - `docs/RELEASE-CHECKLIST.md`

不要从 Git 历史、旧报告或模型记忆推断当前规则；当前文件优先。

## 2. 当前架构

核心 Python：

```text
src/bili_learning/
```

共享 CLI：

```text
scripts/run_bili_learning.py
```

唯一人工维护的本地 Skill：

```text
skill/bili-learning-automation/
```

Codex、Hermes、WorkBuddy 的用户级 Skill 目录都应直接使用 Windows Junction 指向该 canonical Skill。仓库不再维护三套宿主副本。

ChatGPT Web 是唯一例外：它安装独立 ZIP，由：

```powershell
python .\scripts\build_chatgpt_skill.py
```

生成：

```text
dist/bili-learning-automation-chatgpt.zip
```

ZIP 是生成物，不是规则真源。

## 3. 本机数据拓扑

推荐并在维护者机器上使用的模式：

```text
<repo-root>\notes\bilibili        # 真实 Markdown，Git ignored
             ↑
             │ Junction target
             │
<vault-root>\bilibili              # Obsidian 看到的目录
```

配置语义：

```text
notes_root    = 真实物理写入位置
vault_root    = 直接包含 .obsidian 的 Vault 根目录
notes_subdir  = Vault 中映射本项目笔记的相对子目录
```

推荐 `config/local.json`：

```json
{
  "notes_root": "notes/bilibili",
  "vault_root": "D:\\Notes\\MyVault",
  "notes_subdir": "bilibili",
  "cookie_file": "key/bilibili_cookies.txt",
  "workflow_mode": "light"
}
```

关键不变量：

- Junction 方向必须是 **Vault → 项目 notes**；
- 不要把项目 `notes/bilibili` 反向链接到工作区外；
- Agent 只使用 Settings / Job 返回的 `notes_root` 路径执行写作、finalize、查重和整理；
- onboarding 的 `obsidian_notes_mapping` 必须为 OK；
- `notes/**`、`key/*`、`config/local.json`、`.runtime/*` 都是本机数据，不提交；
- 只跟踪 `notes/.gitkeep`、`key/.gitkeep` 与公开 example。

兼容模式仍支持：

- 只配置 `vault_root + notes_subdir`：直接写 Vault；
- 只配置 `notes_root`：可写笔记，但无法完整检查 Vault/CSS。

## 4. 本地 Agent 安装

统一 Skill 名：

```text
bili-learning-automation
```

推荐用户级安装位置见 `docs/LOCAL-AGENT-INSTALL.md`。

不要恢复以下旧架构：

```text
.agents/skills/bili-learning-automation-codex/
hermes-skills/
workbuddy-skills/
chatgpt-skills/
scripts/build_agent_skill_packages.py
```

这些已经退役。

canonical Skill 中的：

```text
scripts/local_bridge.py
scripts/local_bridge.ps1
```

只处理 Junction、Python、PYTHONPATH 和 cleanup runner 兼容，不承载业务规则。

## 5. 稳定业务流程

默认入口：

```text
prepare             -> subtitle_srt
prepare-transcript  -> asr_text，必须先有用户明确 ASR 授权
prepare-description -> description_only，必须由当前消息明确要求跳过字幕
```

三个入口共用同一个 Job lifecycle、finalizer、reservation、恢复和 retire 逻辑。

重复 BVID：

- 默认返回 `existing_note_found`；
- `update` 必须指定目标并使用 SHA-256 冲突保护；
- `rerun` 才允许创建序号新笔记；
- 不自动猜测用户选择。

默认写作模式是 `light`。严格模式才加载完整阶段性工作文件。

## 6. 接手后的第一组检查

如果任务涉及安装、生成笔记、环境状态或结构修改，优先执行：

```powershell
python .\scripts\run_bili_learning.py onboarding
```

预期：

```text
status = ready
actions = []
obsidian_notes_mapping = OK   # 使用混合 notes_root + Vault 模式时
```

再检查：

```powershell
git status --short
```

如果工作区已有用户或其他 Agent 的未提交改动，保留无关改动，不做 reset/clean。

## 7. 修改前后的验证

结构或核心代码改动至少运行：

```powershell
python -m ruff check .
python -m compileall -q src scripts skill/bili-learning-automation/scripts
python -m pytest -q
python .\scripts\build_chatgpt_skill.py --check
git diff --check
```

需要刷新 ChatGPT Web 包时再运行：

```powershell
python .\scripts\build_chatgpt_skill.py
```

正式 commit / push / Release 前再阅读 `docs/RELEASE-CHECKLIST.md`。

## 8. 安全与操作边界

- 不读取、打印、复制或提交 Cookie 内容；
- 不把私人笔记、runtime、local config 加入 Git；
- 不递归清理未知目录；
- 退役本机历史数据时优先送 Windows 系统回收站，不永久删除；
- 不安装、卸载或替换依赖，除非任务明确要求；
- 不 commit / push / release，除非用户明确授权；
- 不把旧 Chrome/CDP collector 或旧宿主 wrapper 恢复为默认链路；
- 不把 CSS 真源复制回本仓库；CSS 唯一共享真源见 `config/obsidian-style.json`。

## 9. 旧会话与 Skill 刷新

Codex、Hermes、WorkBuddy 使用 Junction，因此仓库内 canonical Skill 更新后通常不需要重新安装。

但旧会话可能已经缓存此前读取的 `SKILL.md` 或项目规则。重大 Skill / AGENTS 变更后：

1. 新建会话或让 Agent 重新加载 Skill / 项目；
2. 再运行 onboarding；
3. 确认 `ready` 后继续。

ChatGPT Web 不使用 Junction。只有重新构建并由用户手动更新 ZIP 后，网页端才会获得新的 Skill / references 快照。
