# 文档中心

这里按“要完成什么”来组织 `bili-learning-automation` 的文档。

如果是第一次使用，不需要先读架构、Agent 协议或开发说明，直接从 **[新手快速上手](QUICKSTART.md)** 开始。

---

## 一、教程：照着做即可

### [新手快速上手](QUICKSTART.md)

适合第一次安装。

内容包括：

- 下载项目；
- 安装 / 检查 yt-dlp；
- 配置 Obsidian Vault 与 Cookie；
- 运行 doctor；
- 安装 Obsidian CSS；
- 选择 Hermes / WorkBuddy / Codex；
- 完成第一次 B站链接转笔记；
- 确认输出位置和常见状态。

### [Hermes Skill 安装教程](HERMES-SKILL-INSTALL.md)

只处理 Hermes 接入问题：

- Skill 放在哪里；
- 如何使用 Junction；
- 如何验证加载路径；
- 项目更新后如何 reload；
- Hermes 仍使用旧 Skill 时怎么检查。

### [WorkBuddy Skill 安装教程](WORKBUDDY-SKILL-INSTALL.md)

只处理 WorkBuddy 接入问题：

- 适配层位置；
- 本机安装方式；
- 如何验证；
- 更新项目后如何同步。

### [Obsidian 样式教程](OBSIDIAN-STYLING.md)

用于安装和维护：

```text
learning-lab.css
video-note.css
```

也包括 CSS 不显示、Vault 路径不对等问题的检查方法。

### [笔记整理与归档教程](NOTE-ORGANIZATION.md)

只在用户主动要求整理时使用。说明：

- 为什么新笔记默认只进入 `00-待整理`；
- 为什么整理不会自动执行；
- “最近一篇 / 全部”的范围确认门禁；
- 短知识标题的命名规则；
- 视频生成按模型生态分类的规则；
- 分类目录与 Tags 的职责分工；
- Organizer 的安全调用方式。

---

## 二、说明 / 参考：需要查参数或理解行为时阅读

### [配置手册](CONFIGURATION.md)

查这些内容时看这里：

- `config/local.json`；
- `vault_root` / `notes_subdir` / `notes_root`；
- Cookie 路径；
- yt-dlp 自定义路径；
- `workflow_mode`；
- 环境变量；
- 配置解析优先级；
- doctor 会检查什么。

### [依赖说明](DEPENDENCIES.md)

说明运行时依赖、开发依赖、yt-dlp 与历史依赖的关系。

### [架构说明](ARCHITECTURE.md)

说明主链路和各模块职责：

```text
input
→ collector
→ transcript
→ Agent
→ finalizer
→ Obsidian
```

适合需要理解源码或定位模块责任的人。

### [Agent 接入协议](AGENT-INTEGRATION.md)

用于 Hermes / WorkBuddy / Codex 之外的新 Agent 接入，也用于维护现有适配层。

包含：

- Agent 允许修改什么；
- 哪些内容由 Python 固定生成；
- 来源事实边界；
- `analysis.json` / coverage review；
- finalizer 与清理要求。

### [内容质量标准](standards/LIGHT-WORKFLOW.md)

默认 `light` 模式的内容整理规则。

普通用户通常不需要单独阅读；主要供 Agent 和维护者使用。

### [严格模式内容标准](standards/CODEX-VIDEO-NOTE-GUIDE.md)

主要服务 `workflow_mode: strict`，用于需要中间阶段审计和内容质量回归的任务。

---

## 三、疑难解答：出现问题时阅读

### [疑难解答 / 故障排查](TROUBLESHOOTING.md)

建议先看任务返回的状态，再按症状查找。

覆盖：

- `configuration_required`；
- `in_progress`；
- yt-dlp 未找到；
- Cookie 文件不存在；
- `subtitle_unavailable`；
- UP 主简介获取失败；
- `note_invalid`；
- Hermes Skill 未更新；
- Hermes 只分析不执行；
- 长视频读取慢；
- Obsidian 无样式；
- 短链解析失败；
- `organize` 失败。

遇到未知问题时，先运行：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

需要把诊断结果交给 Agent 分析时使用：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py --json
```

### [安全说明](../SECURITY.md)

处理下面问题时阅读：

- Cookie 如何保存；
- 什么内容不能进入公开仓库；
- 本机路径和私人笔记；
- Git author / committer 邮箱；
- 安全问题如何反馈。

---

## 四、开发与维护

### [开发说明](DEVELOPMENT.md)

包含：

- 开发环境；
- pytest / Ruff；
- 内容质量 Benchmark；
- 提交前检查；
- CI。

### [Release Checklist](RELEASE-CHECKLIST.md)

正式发布版本前使用，不是普通用户安装教程。

### [Legacy 说明](LEGACY.md)

记录旧 Chrome/CDP、`bili-note`、`web-access` 路线。

当前默认流程使用 yt-dlp 字幕优先链路，新用户不需要从 Legacy 开始。

### `reports/`

这里保存开发过程中的验收、实验和交接记录。

这些文件用于追溯项目决策，不代表当前用户教程；当报告与 README、QUICKSTART、CONFIGURATION 或现行标准冲突时，以现行正式文档和代码为准。

---

## 推荐阅读顺序

### 第一次安装

```text
QUICKSTART
→ 对应 Agent 安装教程
→ OBSIDIAN-STYLING
→ 第一次发送 B站链接
```

### 配置有问题

```text
CONFIGURATION
→ doctor
→ TROUBLESHOOTING
```

### Agent 运行异常

```text
TROUBLESHOOTING
→ 对应 Agent 安装教程
→ AGENT-INTEGRATION（维护者）
```

### 修改项目

```text
../AGENTS.md
→ ARCHITECTURE
→ DEVELOPMENT
→ 对应 standards
```
