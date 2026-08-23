# B站视频转笔记

[简体中文](README.md) | [English](README.en.md)

把一个 Bilibili 视频链接，自动整理成**可长期检索、复习和继续整理的 Obsidian 学习笔记**。

项目采用 **字幕优先（subtitle-first）** 的方式：默认只获取中文字幕、UP 主原始简介和元数据，不下载视频或音频；再由 Agent 完成知识提取、覆盖复核和正文整理，最后由程序校验并发布到 Obsidian。

> **一句话理解：** 不是“把视频压成几句摘要”，而是尽量保住参数、版本、工具、步骤、对比、失败案例、限制和资源，把“看过的视频”变成以后还能查的知识。

**License：** [PolyForm Noncommercial 1.0.0](LICENSE)，允许非商业使用；商业使用不在当前许可证授权范围内。

> 第一次安装建议直接看 **[新手快速上手](docs/QUICKSTART.md)**。当前教程以 Windows 为主。

---

## 为什么做这个项目

很多视频摘要工具适合快速知道“视频大概讲了什么”，但教程类、技术类和知识密集型视频真正有价值的内容往往是：

- 参数、数值、上下限和典型配置；
- 模型、节点、插件、LoRA、版本和安装前提；
- A/B 差异、兼容性、互斥关系和选择条件；
- 作者实测中的耗时、质量变化、失败表现和取舍；
- UP 主简介里的 GitHub、模型、工作流等资源；
- “什么情况下该用 / 不该用”的能力边界。

`bili-learning-automation` 的目标是**优先保护这些可以长期复用的知识**，而不是为了短而短。

---

## 30 秒了解工作流

```text
B站链接 / BV号
        ↓
yt-dlp 获取字幕、简介、元数据
        ↓
生成 transcript / 长字幕自动分块
        ↓
Agent 判断来源是否足够
        ↓
提取知识 + 生成“先看结论 + 知识正文”
        ↓
回看字幕做覆盖复核
        ↓
finalizer 校验
        ↓
发布到 Obsidian 的 00-待整理
```

默认流程使用 `yt-dlp --skip-download`，**不下载视频或音频**。

---

## 它和普通视频摘要器有什么不同

### 1. 字幕不足时宁可停止

正文事实只允许来自：

- 当前视频字幕；
- UP 主原始简介。

如果字幕严重缺失、关键参数只能依赖画面判断，或者专有名词损坏到无法支撑可信笔记，Agent 可以返回 `source_insufficient`，而不是用模型常识补一篇“看起来合理”的笔记。

### 2. 长视频不是先压缩再写

长字幕会被转换成有顺序的 transcript manifest 和 chunk。分块只解决 Agent 读取问题，不做语义摘要、关键词过滤或提前压缩。

因此 20～40 分钟甚至更长的教程，可以继续保留参数、方案关系和实测细节，而不是只剩几个主题标题。

### 3. 不确定专名保留检索线索，但不乱猜

视频字幕经常来自音频自动转写。遇到模型名、插件名等错字时：

- 来源能确认：使用可确认名称；
- 高度疑似但无法确认：保留“字幕原音 / 名称未确认 / 待核实”；
- 完全无法判断：保留用途、参数、关系和实测结果，省略具体拼写。

这样既不会因为一个错字丢掉整条知识，也不会把模型记忆偷偷升级成“来源事实”。

### 4. LLM 只负责该负责的内容

程序负责确定性内容：

- Frontmatter；
- H1 与作者 / 日期 / 时长 / BVID；
- Bilibili 播放器；
- UP 主简介与资源链接；
- tags / cssclasses；
- 文件名、路径和防覆盖；
- finalizer 校验与 runtime 清理。

Agent 主要负责两个区域：

- **先看结论**：快速判断视频价值；
- **知识正文**：根据当前视频真实内容动态组织。

### 5. 新笔记先进入 Inbox，而不是自动冒充“已学会”

所有新笔记先进入：

```text
00-待整理/
```

等真正学习过以后，再执行“学习后整理”，生成短标题、一句简介、建议分类并安全移动。

---

## 生成的笔记大致是什么样

```text
标题
作者 · 发布日期 · 时长 · BVID

先看结论

Bilibili 播放器
UP 主资源 / 资料获取条件 / 原始简介

动态知识正文
├── 参数与配置
├── 方案对比
├── 操作步骤
├── 实测结果
├── 失败案例
├── 风险与限制
└── 其它真正值得保留的知识
```

正文不套固定五段式，也不限制 H2 数量、字数或文件大小。短视频可以很短，百科型教程可以很长。

项目使用共享的 [Obsidian Learning Snippets](https://github.com/ZiYao00/obsidian-learning-snippets) 视觉系统；即使关闭 CSS，Markdown 本身仍保持可读。

---

## 适合什么场景

比较适合：

- B站教程、课程、技术分享；
- ComfyUI、AI、生图 / 视频生成、本地模型、编程等参数密集内容；
- 需要长期查阅，而不是只想看一段摘要；
- 想把手机里看到的视频链接交给电脑 Agent 自动处理；
- 已经使用 Obsidian，希望视频学习内容进入自己的知识库。

不太适合：

- 完全没有可用中文字幕的视频；
- 主要信息只存在画面、字幕几乎不描述操作的教程；
- 目标是下载或归档视频媒体本身；
- 希望模型脱离来源自动补齐完整教程的场景。

---

## 核心能力

- 支持 BV 号、标准 Bilibili 链接、包含 BV 的复制文本和受支持的 `b23.tv` 短链；
- 使用 `yt-dlp --skip-download`，默认不下载音视频；
- 保留 UP 主原始简介、资源链接和明确的资料领取条件；
- 不生成来源中没有出现的模板、工作流或具体参数；
- 自动处理长字幕和极小尾块；
- 同一 BVID 可以重复转换，文件名自动加 `（2）`、`（3）`，不会覆盖旧笔记；
- 支持 `light` 默认工作流和可选 `strict` 审计工作流；
- Finalizer 通过后才正式发布，并清理 runtime 临时任务；
- Hermes、WorkBuddy、Codex 共用同一个核心，不为每个 Agent 复制一套实现；
- Cookie、私人笔记和本机配置默认不进入 Git。

---

## 快速开始

### 1. 准备环境

普通 Windows 用户需要：

| 需要 | 用途 |
| --- | --- |
| Python 3.10+ | 运行核心脚本 |
| yt-dlp | 获取字幕、简介和元数据 |
| Bilibili Cookie 文件 | 通常用于登录态字幕 / 元数据访问 |
| Obsidian Vault | 保存学习笔记 |
| Hermes / WorkBuddy / Codex | 负责阅读 transcript 并写知识正文 |

项目**不会内置或自动安装 `yt-dlp.exe`**。Windows 可按官方方式安装：

```powershell
winget install yt-dlp
```

### 2. 克隆项目

```powershell
git clone https://github.com/ZiYao00/bili-learning-automation.git
cd bili-learning-automation
```

### 3. 创建本机配置

```powershell
Copy-Item .\config\local.json.example .\config\local.json
```

示例：

```json
{
  "vault_root": "D:\\Notes\\MyVault",
  "notes_subdir": "bilibili",
  "cookie_file": "D:\\Private\\bilibili_cookies.txt",
  "workflow_mode": "light"
}
```

`config/local.json` 已被 Git 忽略，用于保存每台电脑自己的路径。

### 4. 运行 doctor

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

Doctor 会检查 Python、yt-dlp、Cookie 文件、Vault、CSS、taxonomy 和写权限，但**不会读取 Cookie 内容，也不会访问 Bilibili**。

### 5. 安装 Obsidian 样式

按 [Obsidian 视觉样式](docs/OBSIDIAN-STYLING.md) 把：

```text
learning-lab.css
video-note.css
```

安装到当前 Vault 的：

```text
.obsidian/snippets/
```

并在 Obsidian 中启用。

### 6. 选择 Agent 入口

| 入口 | 适合场景 | 文档 |
| --- | --- | --- |
| Hermes | 手机 / 私聊发送 B站链接，电脑自动处理 | [安装教程](docs/HERMES-SKILL-INSTALL.md) |
| WorkBuddy | 在 WorkBuddy 会话里直接转笔记 | [安装教程](docs/WORKBUDDY-SKILL-INSTALL.md) |
| Codex | 开发、测试、直接操作项目 | 先读取 `AGENTS.md` |

### 7. 发送链接

```text
https://www.bilibili.com/video/BVxxxxxxxxxx/
```

或者：

```text
BVxxxxxxxxxx
```

正常情况下不需要再手动指定字幕、文件名或笔记路径。

完整安装流程见 **[新手快速上手](docs/QUICKSTART.md)**。

---

## Agent 与模型

本项目**不绑定特定 LLM**。Agent 只是薄适配层，collector、transcript、taxonomy、内容标准、validator 和 finalizer 都由共享核心负责。

不同模型的最终质量仍会受到以下能力影响：

- 长上下文理解；
- 参数和专有名词事实保真；
- 多方案关系重建；
- 实测证据保留；
- 写作与信息组织。

项目已经使用多个 Agent / LLM 环境做过长视频和同视频 A/B 回归，但 README 不维护固定模型排名，因为模型版本、代理后端、价格和能力都会变化。需要做模型 Benchmark 时，建议使用固定 BVID 和相同 Skill 版本重新测试。

---

## 两种写作模式

### `light`：默认

```text
完整读取 transcript
→ 来源充分性判断
→ 直接完成正文
→ 独立排版优化
→ 回看字幕做覆盖复核
→ finalizer
```

适合日常使用，限制少，Agent 有更大的内容组织自由。

### `strict`：可选

增加：

```text
Fact Ledger
→ knowledge_outline
→ Semantic Draft
→ Layout Plan
→ Source Recheck
```

适合需要中间过程审计、调试内容丢失或做质量回归的场景。

普通用户保持默认 `light` 即可。

---

## 数据与隐私

默认不会进入 Git 的内容包括：

```text
key/                 # Cookie / 本机凭据
config/local.json    # 本机路径配置
notes/**             # 私人学习笔记
.runtime/            # 临时任务
.codex-backups/      # 本地备份
archive/ materials/  # 本地资料
```

公开仓库只保留通用示例，例如 `config/local.json.example`。

> Cookie 是账号凭据。不要把 Cookie 内容复制到 README、Issue、PR、日志或 Agent 对话里。

更多说明见 [SECURITY.md](SECURITY.md)。

---

## 常见状态

| 状态 | 含义 |
| --- | --- |
| `configuration_required` | 尚未绑定真实 Obsidian Vault，采集不会启动 |
| `materials_ready` | 字幕、简介和元数据已经准备完成 |
| `in_progress` | 同一 BV 正在被其它活动任务处理 |
| `subtitle_unavailable` | 没有取得可用中文字幕 |
| `source_insufficient` | 当前字幕 / 简介不足以生成可信笔记 |
| `note_ready` | Finalizer 校验通过，笔记已正式发布 |
| `note_invalid` | 草稿未通过最终校验 |
| `failed` | 配置、采集或运行失败 |

同一个 BV 在活动任务结束后仍然可以再次转换；`in_progress` 只是并发保护，不是永久去重。

---

## 文档导航

| 文档 | 用途 |
| --- | --- |
| [新手快速上手](docs/QUICKSTART.md) | 从零完成第一次转换 |
| [配置说明](docs/CONFIGURATION.md) | Vault、Cookie、yt-dlp、环境变量 |
| [Hermes Skill 安装](docs/HERMES-SKILL-INSTALL.md) | Hermes 接入 |
| [WorkBuddy Skill 安装](docs/WORKBUDDY-SKILL-INSTALL.md) | WorkBuddy 接入 |
| [Obsidian 视觉样式](docs/OBSIDIAN-STYLING.md) | CSS 安装与排查 |
| [故障排查](docs/TROUBLESHOOTING.md) | 常见错误状态 |
| [智能体接入协议](docs/AGENT-INTEGRATION.md) | 新 Agent / 适配层开发 |
| [架构说明](docs/ARCHITECTURE.md) | collector → transcript → Agent → finalizer |
| [开发说明](docs/DEVELOPMENT.md) | 测试、质量回归和维护 |
| [Release Checklist](docs/RELEASE-CHECKLIST.md) | 正式版本发布检查 |

---

## 开发与测试

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
```

公共测试不需要真实 Cookie，也不应访问真实 Bilibili 账号。

---

## Legacy

旧的 Chrome/CDP、`bili-note`、`web-access` 路线仍保留历史兼容材料，但**不是当前默认入口**。

新接入统一使用 yt-dlp 的字幕优先主链。详见 [Legacy 说明](docs/LEGACY.md)。

---

## 许可证

本项目采用 [PolyForm Noncommercial 1.0.0](LICENSE)。

允许个人学习、研究、测试和兴趣项目等非商业使用；商业用途不在当前许可证授权范围内。第三方依赖继续遵循各自许可证。
