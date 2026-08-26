# B站视频转笔记

[简体中文](README.md) | [English](README.en.md)

`bili-learning-automation` 用于把 Bilibili 视频的字幕、UP 主简介和元数据整理为 Obsidian 学习笔记。

默认流程使用 `yt-dlp --skip-download`，**不下载视频或音频**。Agent 负责阅读字幕和整理知识，程序负责元数据、文件路径、校验、发布，以及 runtime 任务的恢复、并发保护与 retire 生命周期。

> 第一次使用：直接阅读 **[新手快速上手](docs/QUICKSTART.md)**。
> 不知道该看哪份文档：打开 **[文档中心](docs/README.md)**。

---

## 1. 项目用途

正常使用流程：

```text
B站链接 / BV号
→ 获取中文字幕、UP 主简介和元数据
→ 生成 transcript；长字幕自动分块
→ Agent 判断现有来源是否足够
→ 整理“先看结论 + 知识正文”
→ 回看字幕做覆盖复核
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

正文事实默认只来自：

- 当前视频字幕；
- UP 主原始简介。

如果字幕缺失严重、重要信息只能依赖画面判断，或现有文字不足以形成可信笔记，Agent 可以停止任务并返回 `source_insufficient`，不会使用模型常识补齐具体事实。

---

## 2. 使用前准备

普通 Windows 用户需要：

| 需要 | 用途 |
| --- | --- |
| Python 3.10+ | 运行核心脚本 |
| yt-dlp | 获取字幕、简介和元数据 |
| Bilibili Cookie 文件 | 提供已登录 Bilibili 的会话凭据；当前正常采集必需 |
| Obsidian Vault | 保存生成的学习笔记 |
| Hermes / WorkBuddy / Codex | 读取 transcript 并整理正文 |

项目不会内置或自动安装 `yt-dlp.exe`。Windows 可使用：

```powershell
winget install yt-dlp
```

Cookie 是账号凭据。项目需要 **Mozilla / Netscape 格式的完整 `cookies.txt` 文件**，不是只复制 `SESSDATA`。项目只接收 Cookie **文件路径**，不要把 Cookie 内容写入 README、Issue、PR、日志或 Agent 对话。第一次不知道怎样获取时，直接阅读 [Bilibili Cookie 获取与安全配置](docs/BILIBILI-COOKIE.md)。

---

## 3. 第一次安装

完整步骤见：[新手快速上手](docs/QUICKSTART.md)。

最基本的安装过程如下。

### 3.1 克隆项目

```powershell
git clone https://github.com/ZiYao00/bili-learning-automation.git
cd bili-learning-automation
```

### 3.2 本机配置

普通用户可以直接让 Agent 在 onboarding 时补齐缺失配置，不必先手工编辑 JSON。如果希望自己维护本机配置，可复制模板：

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

其中：

- `vault_root`：直接包含 `.obsidian` 的 Obsidian Vault 根目录；
- `notes_subdir`：本项目在 Vault 中保存笔记的相对子目录；
- `cookie_file`：Netscape 格式 Bilibili Cookie 文件路径；
- `workflow_mode`：默认使用 `light`。

`config/local.json` 已被 Git 忽略，用于保存当前电脑自己的路径配置。

更完整的字段和优先级见：[配置手册](docs/CONFIGURATION.md)。

### 3.3 准备 Bilibili Cookie

第一次使用时，先在浏览器正常登录 Bilibili，再导出 **Netscape `cookies.txt`**。不要只从 F12 里复制 `SESSDATA`；`yt-dlp --cookies` 需要完整 Cookie 文件。

普通用户建议使用可信、支持 Netscape 格式的浏览器导出工具，尽量只导出 `bilibili.com` 当前站点，然后保存为例如：

```text
bilibili_cookies.txt
```

可以放在项目的 `key/bilibili_cookies.txt`，也可以放在项目外的私密目录，再把路径配置到 `cookie_file`。Cookie 内容不要发送给 Agent；Agent 只需要文件路径。

完整教程，包括浏览器导出方式、格式判断、yt-dlp `--cookies-from-browser` 的安全注意事项、Windows `Failed to decrypt with DPAPI` 和 Cookie 失效处理，见：**[Bilibili Cookie 获取与安全配置](docs/BILIBILI-COOKIE.md)**。

### 3.4 首次环境检查

接入 Hermes / WorkBuddy / Codex 后，Agent 应在第一次正式采集前自动执行 onboarding，只向用户询问无法自动确定的缺失项。手动检查可运行：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\onboarding_bilibili_learning.py
```

`action_required` 会返回需要处理的 Vault、Cookie、yt-dlp 等配置；CSS 缺失只作为非阻塞提醒。完整诊断仍可运行：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

Doctor 会检查：

- Python；
- yt-dlp；
- Cookie 文件是否存在；
- Obsidian Vault；
- CSS；
- taxonomy；
- notes / runtime 写权限；
- 项目关键文件。

Doctor **不会读取 Cookie 内容，也不会访问 Bilibili**。

### 3.5 安装 Obsidian 样式

本项目使用共享 [Obsidian Learning Snippets](https://github.com/ZiYao00/obsidian-learning-snippets)。

需要把：

```text
learning-lab.css
video-note.css
```

放入当前 Vault 的：

```text
.obsidian/snippets/
```

然后在 Obsidian 的“设置 → 外观 → CSS 代码片段”中启用两项。

详细步骤见：[Obsidian 样式教程](docs/OBSIDIAN-STYLING.md)。

### 3.6 安装或选择 Agent

| Agent | 使用方式 | 教程 |
| --- | --- | --- |
| Hermes | 手机 / 私聊发送 B站链接，电脑处理 | [Hermes Skill 安装教程](docs/HERMES-SKILL-INSTALL.md) |
| WorkBuddy | 在 WorkBuddy 会话中发送链接 | [WorkBuddy Skill 安装教程](docs/WORKBUDDY-SKILL-INSTALL.md) |
| Codex | 在项目目录中直接执行、测试或维护 | 先阅读 `AGENTS.md` |

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

同名文件已经存在时，会生成 `（2）`、`（3）` 等序号，不覆盖旧笔记。

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

视频字幕可能来自音频自动转写。遇到无法确认的模型名、插件名等专有名词时，当前内容标准要求保留不确定性，不允许把模型记忆静默改写成来源事实。

---

## 6. 两种写作模式

### `light`：默认

```text
完整读取 transcript
→ 来源充分性判断
→ 直接完成正文
→ 独立排版优化
→ 回看 transcript 做覆盖复核
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

本项目**不绑定特定 LLM**。Hermes、WorkBuddy 和 Codex 是不同入口，采集、transcript、taxonomy、内容标准、validator 和 finalizer 共用同一套核心逻辑。

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
| `materials_ready` | 字幕、简介和元数据已经准备完成 | Agent 继续处理；若同时有 `recovered: true`，表示核心已恢复旧 Job，不会重复采集 |
| `in_progress` | 同一 BV 仍有真实活动任务 | 不要重复采集或手工处理 runtime |
| `subtitle_unavailable` | 没有取得可用中文字幕 | 本次停止 |
| `source_insufficient` | 现有字幕 / 简介不足以形成可信笔记 | 更换资料更完整的视频 |
| `note_ready` | Finalizer 校验通过并已发布 | 业务完成；runtime retire/维护状态不改变发布结果 |
| `note_invalid` | 草稿未通过最终校验 | 按错误信息修复，不绕过 finalizer |
| `failed` | 配置、采集或运行失败 | 先运行 doctor，再查故障排查 |

核心会自动恢复“进程已结束但材料完整”的 Job，并重建缺失的 handoff；正常锁、reservation 和 Job 生命周期不依赖删除权限。更完整的症状、原因和处理方式见：[疑难解答 / 故障排查](docs/TROUBLESHOOTING.md)。

---

## 9. 数据与隐私

下列内容默认不进入 Git：

```text
key/                 # Cookie / 本机凭据
config/local.json    # 本机路径配置
notes/**             # 私人学习笔记
.runtime/            # 活动 / retired runtime 任务
.codex-backups/      # 本地备份
archive/ materials/  # 本地资料
```

公开仓库只应保存通用配置示例，例如 `config/local.json.example`。

详细说明见：[SECURITY.md](SECURITY.md)。

---

## 10. 文档导航

完整文档索引见：**[docs/README.md](docs/README.md)**。

### 新手与操作教程

- [新手快速上手](docs/QUICKSTART.md)：从下载项目到生成第一篇笔记；
- [Bilibili Cookie 获取与安全配置](docs/BILIBILI-COOKIE.md)：第一次导出 Cookie、格式检查、安全保存和失效处理；
- [Hermes Skill 安装教程](docs/HERMES-SKILL-INSTALL.md)：安装、更新和验证 Hermes 入口；
- [WorkBuddy Skill 安装教程](docs/WORKBUDDY-SKILL-INSTALL.md)：安装、更新和验证 WorkBuddy 入口；
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
- [Release Checklist](docs/RELEASE-CHECKLIST.md)：正式版本发布前检查；
- [Legacy 说明](docs/LEGACY.md)：旧 Chrome/CDP 路线的历史兼容信息。

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
