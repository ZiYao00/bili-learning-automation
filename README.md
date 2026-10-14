# B站视频转笔记

[简体中文](README.md) | [English](README.en.md)

`bili-learning-automation` 用于把 Bilibili 视频的字幕、明确授权后的 ASR 纯文本，或明确指定的 UP 主简介资源信息整理为 Obsidian 笔记。

默认 `prepare` 使用字幕优先，并通过 `yt-dlp --skip-download` **不下载视频或音频**。用户明确授权 ASR 时用 `prepare-transcript` 回流纯文本；用户当前消息明确要求“纯资源分享 / 只整理简介 / 不用字幕”时用 `prepare-description`。三个入口共用同一 Job、校验、发布、恢复、并发保护与 retire 生命周期。

> 第一次使用：直接阅读 **[新手快速上手](docs/QUICKSTART.md)**。
> 不知道该看哪份文档：打开 **[文档中心](docs/README.md)**。

---

## 1. 项目用途

正常使用流程：

```text
B站链接 / BV号
→ 按当前消息明确意图选择 subtitle_srt / asr_text / description_only
→ 生成统一 source manifest；subtitle / ASR 按需分块，description-only 不伪造 chunk
→ Agent 判断现有来源是否足够
→ 整理“先看结论 + 知识正文”
→ 回看当前 Job 允许的来源做覆盖复核
→ finalizer 校验
→ 发布到 Obsidian 的 00-待整理
→ runtime Job 退出活动区并 retire
```

生成笔记时重点保留来源中具有长期参考价值的信息，例如：

- 参数、数值、公式、上下限；
- 模型、节点、插件、LoRA、版本；
- 操作步骤和前置条件；
- A/B 差异、兼容关系、互斥关系；
- 实测耗时、质量变化和失败表现；
- UP 主简介中的 GitHub、模型、工作流等资源；
- 来源明确说明的限制、风险和选择条件。

正文事实只来自当前 Job 允许的来源：

- `subtitle_srt`：当前视频字幕、UP 主原始简介、当前 Job 已确定性采集的 UP 主置顶一级评论（如存在）和明确用户补充来源；
- `asr_text`：用户明确授权后的 ASR 纯文本、UP 主原始简介、已采集置顶一级评论（如存在）和明确用户补充来源；
- `description_only`：标题、metadata、UP 主原始简介、已采集置顶一级评论（如存在）和明确用户补充来源，不推断视频口播或画面事实。

如果字幕缺失严重、重要信息只能依赖画面判断，或现有文字不足以形成可信笔记，Agent 可以停止任务并返回 `source_insufficient`，不会使用模型常识补齐具体事实。

---

## 2. 运行条件

本项目面向 Windows 10/11 x64，以 **Agent 代替普通用户完成安装**。运行需要 Python 3.10+、Obsidian Vault、有效的 Bilibili Netscape Cookie 文件，以及至少一种能操作本地项目的 Agent（Codex、Hermes、WorkBuddy 或具备本地桥接的 ChatGPT）。

仓库自带官方单文件 `tools/yt-dlp.exe`，只调用该固定路径；无需安装 yt-dlp 源码、运行 `winget` 或配置系统 PATH。当前随仓库固定版本与校验值记录于 `tools/yt-dlp.release.json`。默认字幕优先，调用 `yt-dlp --skip-download`，不会下载视频或音频。

`local-ASR-service` 是**可选的独立服务**，不是基础安装项。只有默认入口发现无可用字幕且用户明确同意 ASR 后才会调用。使用说明见 [配置手册](docs/CONFIGURATION.md)。

## 3. 安装：直接交给 Agent

不提供双击安装向导。用户只需要把项目地址和安装请求发给已授权的本地 Agent：

```text
请帮我安装并验收 bili-learning-automation：
https://github.com/ZiYao00/bili-learning-automation

请先阅读项目 AGENTS.md、docs/QUICKSTART.md 和 docs/LOCAL-AGENT-INSTALL.md。
由你检测环境、配置本地路径、安装需要的 Skill 并运行 onboarding。
不要让我手工编辑 JSON 或执行命令。
操作现有 Vault 目录、用户级 Skill 目录之前先检查是否冲突，得到授权后再修改。
只接受 Cookie 文件路径，不索取 Cookie 内容；不要覆盖旧笔记或已有目录。
```

Agent 负责下载或更新项目、使用 `scripts/install_agent_skill.ps1` 规划/安装 Codex、Hermes、WorkBuddy 的 Junction，使用 `configure-obsidian` / `configure-cookie` 保存本机配置，并通过 `scripts/ensure_junction.ps1` 安全建立 Obsidian Vault → 项目 notes 的映射。**只有 onboarding 返回 `ready` 且所选 Skill 可用，才算安装完成。**

ChatGPT Web 需要独立 Skill ZIP 及已授权的本地工作区桥接；普通 Python 核心本身不能代替 ChatGPT 平台上的 Skill 安装和授权。

详细步骤和非破坏式恢复：[Agent 安装快速上手](docs/QUICKSTART.md) · [本地 Agent 安装](docs/LOCAL-AGENT-INSTALL.md) · [ChatGPT 安装](docs/CHATGPT-SKILL-INSTALL.md)。

---

## 4. 日常使用

安装完成后，在已接入的 Agent 中发送：

```text
https://www.bilibili.com/video/BVxxxxxxxxxx/
```

或者：

```text
BVxxxxxxxxxx
```

也支持受支持的 Bilibili 复制文本和 `b23.tv` 短链。

来源路由只看当前消息的明确意图：

```text
转换这条链接                          → 默认字幕优先
纯资源分享，只整理简介，不用字幕      → description_only
（默认流程无字幕后）ASR，下载音频转文字 → asr_text
```

项目不会仅凭标题、历史 memory 或“看起来像资源分享”自动跳过字幕。

三个来源入口都会先按 BVID 检查已发布笔记。已经转换过时，默认**不会立刻再生成一篇**，而是先询问：更新已有笔记、重新执行一次或取消。更新保留原文件路径并在 runtime 保存旧笔记快照；finalizer 会用 SHA-256 检查更新期间是否发生人工修改。只有用户明确选择“重新执行一次”时，才创建独立新笔记并在同标题后使用 `（2）`、`（3）` 等序号。

正常情况下，用户不需要手工：

- 下载字幕；
- 拆分长字幕；
- 指定输出文件名；
- 指定 `00-待整理` 路径；
- 直接操作 runtime 文件。

任务完成后，新笔记默认进入：

```text
<notes_root>/00-待整理/
```

用户明确选择“重新执行一次”后，同名文件已存在时会生成 `（2）`、`（3）` 等序号，不覆盖旧笔记；选择“更新”则保留原路径和原文件名。

---

## 5. 生成的笔记结构

正式笔记通常按下面的阅读顺序生成：

```text
标题
作者 · 发布日期 · 时长 · BVID

先看结论

Bilibili 播放器
UP 主资源 / 资料获取条件 / 视频简介 / UP 主原文

知识正文
```

知识正文没有固定章节数量。Agent 根据当前视频实际内容决定使用标题、表格、步骤、列表和 Callout。

subtitle / ASR 来源可能包含自动转写噪声；遇到无法确认的模型名、插件名等专有名词时要保留不确定性，不允许把模型记忆静默改写成来源事实。description-only 没有音频来源，不得据此反推视频口播。

---

## 6. 两种写作模式

### `light`：默认

```text
按 source manifest 读取当前允许来源
→ 来源充分性判断
→ 直接完成正文（description-only 保持纯资源短记）
→ 独立排版优化
→ 回看当前允许来源做覆盖复核
→ finalizer
```

这是普通使用的默认模式。

### `strict`：可选

在默认流程之外增加：

```text
Fact Ledger
→ knowledge_outline
→ Semantic Draft
→ Layout Plan
→ Source Recheck
```

主要用于：

- 调试知识遗漏；
- 检查中间过程；
- 内容质量回归测试；
- 需要明确阶段产物的任务。

普通用户不需要主动切换到 `strict`。

---

## 7. Agent 与模型说明

本项目**不绑定特定 LLM**。只人工维护 `skill/bili-learning-automation/SKILL.md` 一份 canonical Skill；Codex、Hermes、WorkBuddy 的用户级 Skill 目录都直接 Junction 到它，不在仓库生成宿主副本。ChatGPT Web ZIP 由 `scripts/build_chatgpt_skill.py` 单独构建，并附带从当前项目文档生成的安全 references 快照；来源采集、Source Mode、source manifest、taxonomy、内容标准、validator 和 finalizer 仍共用同一套核心逻辑。

不同模型可能在以下方面表现不同：

- 长上下文理解；
- 参数和专有名词事实保真；
- 多方案关系整理；
- 实测证据保留；
- 写作与信息组织。

项目会使用固定视频做质量回归，但 **README 不维护固定模型排名**。模型版本、Agent 宿主、代理后端、价格和能力会变化，需要比较模型时应使用相同 BVID、相同项目版本和相同内容标准重新测试。

---

## 8. 常见状态

| 状态 | 含义 | 处理方式 |
| --- | --- | --- |
| `onboarding_required` | 首次环境仍缺少 Vault / Cookie / yt-dlp 等必需配置 | 按 `actions` 处理后重新检查并重试原链接 |
| `materials_ready` | 当前 `source_mode` 的标准 Job 已准备完成 | Agent 按 `source_manifest_path` 和 handoff 继续；`recovered: true` 表示核心已恢复同一来源模式的旧 Job |
| `existing_note_found` | 当前 BVID 已有已发布笔记 | 停止采集，先让用户选择更新、重新执行或取消；重试时保留原始完整消息 |
| `update_target_required` | 同一 BVID 有多篇笔记且尚未指定更新目标 | 让用户明确选择要更新的具体笔记，不猜最新或最旧 |
| `update_conflict` | 更新期间目标笔记被人工修改 | 不覆盖现有文件；报告冲突并重新发起更新 |
| `in_progress` | 同一 BV 仍有真实活动任务 | 不要重复采集或手工处理 runtime |
| `subtitle_unavailable` | 没有取得可用中文字幕 | 本次停止 |
| `source_insufficient` | 当前来源模式不足以形成可信笔记 | 默认/ASR 可换更完整来源；description-only 应补充简介资料或改走字幕流程 |
| `note_ready` | Finalizer 校验通过并已发布 | 业务完成；runtime retire/维护状态不改变发布结果 |
| `note_invalid` | 草稿未通过最终校验 | 按错误信息修复，不绕过 finalizer |
| `failed` | 配置、采集或运行失败 | 先运行 doctor，再查故障排查 |

核心会自动恢复“进程已结束但材料完整”的 Job，并重建缺失的 handoff；正常锁、reservation 和 Job 生命周期不依赖删除权限。更完整的症状、原因和处理方式见：[疑难解答 / 故障排查](docs/TROUBLESHOOTING.md)。

---

## 9. 数据与隐私

下列内容默认不进入 Git：

```text
key/                 # Cookie / 本机凭据
notes/**             # 私人学习笔记；真实 Markdown 可保存在项目内，但不进 Git
config/local.json    # 本机路径配置
.runtime/            # 活动 / retired runtime 任务
```

公开仓库只应保存通用配置示例和空目录占位文件，例如 `config/local.json.example`、`key/.gitkeep`、`notes/.gitkeep`。

详细说明见：[SECURITY.md](SECURITY.md)。

---

## 10. 文档导航

完整文档索引见：**[docs/README.md](docs/README.md)**。其它 Agent / 开发者第一次接手项目时，先读 **[维护交接文档](docs/MAINTENANCE-HANDOFF.md)**，再按任务进入架构、配置或集成文档。

### 新手与操作教程

- [新手快速上手](docs/QUICKSTART.md)：从下载项目到生成第一篇笔记；
- [Bilibili Cookie 获取与安全配置](docs/BILIBILI-COOKIE.md)：第一次导出 Cookie、格式检查、安全保存和失效处理；
- [本地 Agent Skill 安装](docs/LOCAL-AGENT-INSTALL.md)：用同一个 canonical Skill 安装 Codex、Hermes、WorkBuddy；
- [ChatGPT Skill 安装教程](docs/CHATGPT-SKILL-INSTALL.md)：构建并安装 ChatGPT Web 专用 ZIP；
- [Obsidian 样式教程](docs/OBSIDIAN-STYLING.md)：安装 CSS、启用样式和排查显示问题；
- [学习后归档](docs/NOTE-ORGANIZATION.md)：只改文件名和路径，采用最多两层的“领域 / 对象”目录，并保留原笔记内容不变。

### 使用说明与参考

- [配置手册](docs/CONFIGURATION.md)：`local.json`、环境变量、Vault、Cookie、yt-dlp；
- [依赖说明](docs/DEPENDENCIES.md)：运行时依赖和开发依赖；
- [架构说明](docs/ARCHITECTURE.md)：collector、transcript、Agent、finalizer 的职责；
- [Agent 接入协议](docs/AGENT-INTEGRATION.md)：接入新的 Agent 或维护适配层。

### 疑难解答

- [疑难解答 / 故障排查](docs/TROUBLESHOOTING.md)：按状态和症状定位问题；
- [安全说明](SECURITY.md)：Cookie、本机路径、Git 提交和公开仓库边界。

### 开发与维护

- [开发说明](docs/DEVELOPMENT.md)：测试、质量回归和 CI；
- [Release Checklist](docs/RELEASE-CHECKLIST.md)：正式版本发布前检查。

---

## 11. 开发与测试

开发环境：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
```

公共测试不需要真实 Cookie，也不应访问真实 Bilibili 账号。

---

## 12. 许可证

本项目采用 [PolyForm Noncommercial 1.0.0](LICENSE)。

允许个人学习、研究、测试和兴趣项目等非商业使用；商业用途不在当前许可证授权范围内。第三方依赖继续遵循各自许可证。
