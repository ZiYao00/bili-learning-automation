# 文档中心

第一次使用从 [新手快速上手](QUICKSTART.md) 开始。按任务选择文档，不需要从头通读整个 `docs/`。

## 安装与首次使用

| 任务 | 文档 |
| --- | --- |
| 从零配置项目并生成第一篇笔记 | [QUICKSTART.md](QUICKSTART.md) |
| 获取、保存、更新 Bilibili Cookie | [BILIBILI-COOKIE.md](BILIBILI-COOKIE.md) |
| 安装 Codex / Hermes / WorkBuddy | [LOCAL-AGENT-INSTALL.md](LOCAL-AGENT-INSTALL.md) |
| 安装 ChatGPT Web Skill | [CHATGPT-SKILL-INSTALL.md](CHATGPT-SKILL-INSTALL.md) |
| 安装 Obsidian CSS | [OBSIDIAN-STYLING.md](OBSIDIAN-STYLING.md) |
| 学习后整理与归档 | [NOTE-ORGANIZATION.md](NOTE-ORGANIZATION.md) |

本地 Codex、Hermes、WorkBuddy 共用：

```text
skill/bili-learning-automation/
```

通过用户级 Junction 直接安装。ChatGPT Web 单独使用：

```text
dist/bili-learning-automation-chatgpt.zip
```

## 配置与行为参考

- [CONFIGURATION.md](CONFIGURATION.md)：`config/local.json`、Vault、Cookie、yt-dlp、workflow mode、环境变量与 doctor。
- [ARCHITECTURE.md](ARCHITECTURE.md)：核心链路、模块职责、Job lifecycle 与 Skill 分发架构。
- [AGENT-INTEGRATION.md](AGENT-INTEGRATION.md)：Agent 的授权边界、来源事实边界、handoff、finalizer、恢复与整理协议。
- [DEPENDENCIES.md](DEPENDENCIES.md)：运行时与开发依赖。
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)：按状态 / 症状定位问题。
- [../SECURITY.md](../SECURITY.md)：Cookie、本机配置、私人数据与 Git 安全边界。

## 内容标准

默认写作模式：

- [standards/LIGHT-WORKFLOW.md](standards/LIGHT-WORKFLOW.md)

严格模式与质量回归：

- [standards/CODEX-VIDEO-NOTE-GUIDE.md](standards/CODEX-VIDEO-NOTE-GUIDE.md)
- [standards/KNOWLEDGE-DENSE-WORKFLOW.md](standards/KNOWLEDGE-DENSE-WORKFLOW.md)
- [standards/STANDARD-VIDEO-NOTE-EXAMPLE.md](standards/STANDARD-VIDEO-NOTE-EXAMPLE.md)

普通用户通常不需要单独阅读这些标准；它们主要服务 Agent 和维护者。

## 开发与发布

- [MAINTENANCE-HANDOFF.md](MAINTENANCE-HANDOFF.md)：其它 Agent / 开发者接手时的必读架构、数据拓扑、安全边界与验证顺序。
- [DEVELOPMENT.md](DEVELOPMENT.md)：开发环境、测试、Ruff、内容质量回归和提交前检查。
- [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md)：正式发布 / push 前的可复用验收门禁。
- `reports/`：历史验收记录。当前行为以代码、README、QUICKSTART、CONFIGURATION 和现行 standards 为准。

## 常用入口

环境检查：

```powershell
python .\scripts\run_bili_learning.py onboarding
python .\scripts\run_bili_learning.py doctor
```

ChatGPT Web 包检查与构建：

```powershell
python .\scripts\build_chatgpt_skill.py --check
python .\scripts\build_chatgpt_skill.py
```

本地 Agent 安装后不需要再次生成 Skill 副本；更新仓库即可通过 Junction 读取 canonical Skill。

## 推荐阅读路径

第一次使用：

```text
QUICKSTART
→ BILIBILI-COOKIE（需要时）
→ LOCAL-AGENT-INSTALL 或 CHATGPT-SKILL-INSTALL
→ OBSIDIAN-STYLING
```

配置 / 运行异常：

```text
CONFIGURATION
→ doctor
→ TROUBLESHOOTING
```

修改项目：

```text
../AGENTS.md
→ MAINTENANCE-HANDOFF
→ ARCHITECTURE
→ DEVELOPMENT / AGENT-INTEGRATION
→ 对应 standards
```
