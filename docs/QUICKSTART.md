# 新手快速上手

> 文档类型：**操作教程**。适合第一次安装和第一次生成笔记。

这份文档只解决“怎样从零跑通一次”的问题。内部架构、完整配置字段和开发细节分别放在其它说明文档中。

完成本教程后，应能够跑通：

```text
发送 B站链接 / BV号
→ 按当前消息明确意图选择字幕 / ASR / 纯简介资源来源
→ 智能体按标准 Job 整理笔记
→ 写入 Obsidian
```

默认流程字幕优先且**不会下载视频或音频**。只有用户明确要求 ASR 才下载临时音轨转写；只有当前消息明确要求“纯资源分享 / 只整理简介 / 不用字幕”才跳过字幕请求。三个入口共用同一 Job lifecycle。

### 可选：部署 `local-ASR-service`

`local-ASR-service` 是本项目推荐的**可选本地转写服务**，适合经常处理“已确认没有可提取字幕”的视频。它不是首次安装的必需依赖，也不会被 collector 自动调用或自动下载媒体。

可在本项目首次配置后，按 [local-ASR-service](https://github.com/ZiYao00/local-ASR-service) 的说明预先部署到本机；但只有用户明确要求继续 ASR 时，才用它取得纯文本 transcript，并通过现有入口交回本项目：

```powershell
bili-learning prepare-transcript "https://www.bilibili.com/video/BV..." --transcript "C:\path\to\transcript.txt"
```

不要把服务部署、音频下载或 ASR 调用加入默认字幕优先链路。项目只接收真实纯文本，继续沿用统一 Job、handoff 与 finalizer 流程。

---

## 1. 使用前需要准备什么

Windows 用户准备下面几项即可：

| 需要 | 用途 | 是否必须 |
| --- | --- | --- |
| Python 3.10+ | 运行核心脚本 | 是 |
| yt-dlp | 获取视频元数据、简介、字幕 | 是 |
| Bilibili Cookie 文件 | 提供已登录 Bilibili 的会话凭据，用于字幕 / 元数据访问 | **是** |
| Obsidian Vault | 保存学习笔记；Vault 根目录需直接包含 `.obsidian` | 是 |
| ChatGPT / Codex / Hermes / WorkBuddy | 负责阅读来源并写正文；ChatGPT 需本地桥接 | 至少一种 |

> Cookie 是账号凭据。项目只需要 Cookie **文件路径**，不要把 Cookie 内容写进 README、Issue、聊天记录或 Git。

---

## 2. 下载项目

```powershell
git clone https://github.com/ZiYao00/bili-learning-automation.git
cd bili-learning-automation
```

如果只是通过 Hermes / WorkBuddy 使用，核心运行时没有第三方 Python 包依赖；如果还要开发、运行测试，建议创建项目虚拟环境：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

---

## 3. 首次使用：让 Agent 先做环境检查

普通用户不需要先猜路径或逐项编辑配置。ChatGPT、Codex、Hermes 与 WorkBuddy 的入口都应在正式采集前运行统一 onboarding；核心 `prepare` 也有同一门禁，避免某个 Agent 漏掉首次配置。ChatGPT 还必须先连接本地工作区桥接。

统一检查会自动判断 Python、yt-dlp、Cookie、Obsidian Vault 和 CSS 状态，只对真正缺失的项目采取动作：

- Vault 未配置：询问直接包含 `.obsidian` 的 Vault 根目录；笔记子目录默认 `bilibili`；
- Cookie 未配置：只询问 Netscape 格式 Cookie **文件路径**，不要在聊天中粘贴 Cookie 内容；
- yt-dlp 未检测到：项目不会自动安装或复制可执行文件，Windows 默认推荐 `winget install yt-dlp`；只有已经安装在自定义目录时才需要提供可执行文件路径；
- CSS 缺失：只提醒，不阻塞笔记生成，也不会静默复制或覆盖用户文件。

手动检查可运行：

```powershell
python .\scripts\run_bili_learning.py onboarding
```

返回 `ready` 后即可正式采集；返回 `action_required` 时按 `actions` 中的缺失项处理，再重新检查。

### Bilibili Cookie：第一次使用必须先准备

如果 onboarding 返回：

```text
cookie_file_required
```

说明项目还没有找到可用的 Bilibili Cookie 文件。

Cookie 可以理解为浏览器已经登录 Bilibili 的凭据。本项目需要的是 **Mozilla / Netscape 格式的完整 `cookies.txt` 文件**，不是单独复制一个 `SESSDATA`，也不是 JSON 或浏览器请求头。

最适合普通用户的流程是：

```text
浏览器正常登录 Bilibili
→ 打开 bilibili.com
→ 使用可信、支持 Netscape cookies.txt 的导出工具
→ 尽量只导出当前 bilibili.com 站点
→ 保存为 bilibili_cookies.txt
→ 只把“文件路径”告诉 Agent
```

`yt-dlp` 官方 FAQ 提到的浏览器导出工具示例包括 Chromium / Chrome 的 `Get cookies.txt LOCALLY` 与 Firefox 的 `cookies.txt`。安装浏览器扩展时务必确认来源和权限；名称相似的旧扩展不一定安全。

导出的文件第一行应该是：

```text
# Netscape HTTP Cookie File
```

或：

```text
# HTTP Cookie File
```

个人本机最省事的保存位置是：

```text
<repo-root>\key\bilibili_cookies.txt
```

`key/` 已被 Git 忽略。也可以放在项目外的私密目录，例如 `D:\Private\bilibili_cookies.txt`，再把这个路径配置给 Agent。

> **不要把真实 Cookie 内容发送给 Agent。** Agent 只需要文件路径。不要把 Cookie 提交到 Git、Issue、PR、日志、截图或公开网盘。

如果不想安装浏览器扩展，yt-dlp 也可以使用 `--cookies-from-browser` 导出，但官方说明这种方式会把该浏览器中**所有网站的 Cookie**写入目标文件，因此生成的文件敏感程度更高，不建议新手把它长期放在项目目录中。

完整的 Cookie 获取、格式检查、`Failed to decrypt with DPAPI` 处理和失效后重新导出说明见：**[Bilibili Cookie 获取与安全配置](BILIBILI-COOKIE.md)**。

### 手工配置方式

如需自行维护配置，最适合普通用户的是 `config/local.json`。`yt-dlp` 不要求预先写死路径：onboarding / doctor 会自动检测，缺失时只给安装指引，不会自动安装。

先复制模板：

```powershell
Copy-Item .\config\local.json.example .\config\local.json
```

然后修改成本机路径，例如：

```json
{
  "vault_root": "D:\\Notes\\MyVault",
  "notes_subdir": "bilibili",
  "cookie_file": "D:\\Private\\bilibili_cookies.txt",
  "workflow_mode": "light"
}
```

几个字段分别表示：

- `vault_root`：Obsidian Vault 根目录，也就是直接包含 `.obsidian` 的目录；
- `notes_subdir`：本项目在 Vault 内使用的相对子目录，默认推荐 `bilibili`；
- `cookie_file`：Netscape 格式 Bilibili Cookie 文件的位置；
- `workflow_mode`：默认 `light`，让智能体完整读字幕后直接写笔记，再做一次排版优化；需要严格分阶段审计时改为 `strict`。

最终笔记目录会自动计算为 `<vault_root>/<notes_subdir>`。例如上面的配置会写入 `D:\Notes\MyVault\bilibili\00-待整理\`。

`config/local.json` 已被 Git 忽略，适合保存本机路径。旧版 `notes_root` 仍然兼容，但新安装建议使用 `vault_root + notes_subdir`，这样程序才能准确检查 Obsidian 和 CSS。

### yt-dlp 不需要复制进项目

项目不会携带 `yt-dlp.exe`，也不会替用户自动下载安装。首次运行 doctor 时会依次检查环境变量、本机 `local.json` 覆盖和系统 PATH。Windows 如果未检测到 yt-dlp，按官方方式安装即可：

```powershell
winget install yt-dlp
```

安装后重新运行 doctor。只有你把 yt-dlp 放在自定义目录、且没有加入 PATH 时，才需要在 `local.json` 增加例如 `"ytdlp": "D:\\Tools\\yt-dlp.exe"`。

如果不想使用 `local.json`，也可以通过环境变量配置，详见 [配置说明](CONFIGURATION.md)。

---

## 4. 检查配置是否正确

正式测试前先运行 doctor：

```powershell
python .\scripts\run_bili_learning.py doctor
```

如果环境正确，你应该看到 yt-dlp、Cookie、taxonomy、Vault、notes/runtime 写权限等检查通过。doctor 还会检查 `learning-lab.css` 与 `video-note.css` 是否位于当前 Vault 的 `.obsidian/snippets/`。

如果看到 `notes_repository_fallback`，说明还没有显式绑定 Vault。此时新的视频采集会被 onboarding 门禁拦住，并返回 `onboarding_required`；不会把私人笔记静默写入代码仓库。你可以修改 `config/local.json`，也可以运行：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\configure_bilibili_learning.py --vault 'D:\Notes\MyVault' --notes-subdir 'bilibili'
```

该命令只写本机 `config/local.json`，并要求 `--vault` 真正包含 `.obsidian`。

如果要让智能体读取结构化诊断结果：

```powershell
python .\scripts\run_bili_learning.py doctor --json
```

> doctor 不访问 Bilibili、不读取 Cookie 内容，也不会留下测试文件。

---

## 5. 安装 Obsidian 样式

本项目使用共享 [Obsidian Learning Snippets](https://github.com/ZiYao00/obsidian-learning-snippets)；所需的 `learning-lab.css` 与 `video-note.css` 已在 [`config/obsidian-style.json`](../config/obsidian-style.json) 声明。本项目不再保存这两份 CSS 副本。

把共享仓库中的两份 CSS 安装到当前 Obsidian Vault 的：

```text
.obsidian/snippets/
```

然后打开：

```text
Obsidian → 设置 → 外观 → CSS 代码片段
```

刷新并同时启用：

```text
learning-lab
video-note
```

`video-note.css` 依赖 `learning-lab.css`，两个都需要启用。

完整说明见 [Obsidian 样式教程](OBSIDIAN-STYLING.md)。

---

## 6. 选择一个智能体入口

核心流程与智能体无关。目前主要支持：

| 入口 | 适合场景 | 使用方式 |
| --- | --- | --- |
| ChatGPT Work | 在 ChatGPT 中调用本机项目 | 安装专用 ZIP，并连接本地工作区桥接 |
| Codex | 本地生成、开发与测试 | 使用仓库级 Codex Skill 或独立安装包 |
| Hermes | 手机 / 微信直接发 B站链接 | 安装 Hermes Skill 后私聊发送链接 |
| WorkBuddy | WorkBuddy 会话中转笔记 | 安装 WorkBuddy 适配层后发送链接 |

### ChatGPT Work

ChatGPT 使用独立适配层：

```text
chatgpt-skills/bili-learning-automation-chatgpt/
```

不要上传整个仓库，也不要把 Hermes、WorkBuddy 或 Codex ZIP 装进 ChatGPT。完整步骤见 [ChatGPT Skill 安装教程](CHATGPT-SKILL-INSTALL.md)。

### Codex

Codex 仓库级 Skill 位于：

```text
.agents/skills/bili-learning-automation-codex/
```

进入项目后 Codex 可自动发现，也可以用 Junction 或独立 ZIP 安装。完整步骤见 [Codex Skill 安装教程](CODEX-SKILL-INSTALL.md)。

### Hermes

Hermes 使用：

```text
hermes-skills/bili-learning-automation/
```

建议使用 Junction 安装，更新仓库后无需再次复制文件。完整步骤见 [Hermes Skill 安装教程](HERMES-SKILL-INSTALL.md)。
如果需要静态副本，使用 Release 中的 `bili-learning-automation-hermes.zip`；该 ZIP 只包含独立指令，运行时仍需明确指定本机项目根目录。

### WorkBuddy

WorkBuddy 适配层位于：

```text
workbuddy-skills/bili-learning-automation/
```

它只是入口适配层，实际仍调用同一套 Source Mode、`_prepare_materials`、Job、source manifest、finalizer 和笔记标准。第一次安装见 [WorkBuddy Skill 安装教程](WORKBUDDY-SKILL-INSTALL.md)。
如果需要静态副本，使用 Release 中的 `bili-learning-automation-workbuddy.zip`；该 ZIP 只包含独立指令，运行时仍需明确指定本机项目根目录。

---

## 7. 第一次测试

安装好智能体入口以后，最简单的测试方式就是直接发送：

```text
https://www.bilibili.com/video/BVxxxxxxxxxx/
```

也支持：

```text
BVxxxxxxxxxx
```

以及受支持的 Bilibili 复制文本和 `b23.tv` 短链。

来源模式只根据当前消息明确选择：

```text
转换这条链接                          → 默认 subtitle_srt
纯资源分享，只整理简介，不用字幕      → description_only
（默认流程无字幕后）ASR，下载音频转文字 → asr_text
```

不得只凭标题、视频类型猜测或历史 memory 自动跳过字幕。三个入口都会先按 BVID 检查是否已经发布过：发现重复时先询问“更新已有笔记 / 重新执行一次 / 取消”，不会先生成 `（2）` 再事后提醒。更新保留原路径并用 runtime 快照 + SHA-256 防止覆盖用户刚做的人工修改；只有明确选择重新执行时，同标题才继续使用递增序号。正常情况下，你不需要输入底层命令、指定文件名或手工处理 runtime。

智能体会自动完成：

```text
识别链接和当前消息的明确来源意图
→ 按 source_mode 采集 metadata / 简介 / 字幕或接入 ASR 纯文本
→ 生成统一 source manifest（description-only 不伪造 chunk）
→ 判断当前允许来源是否足够
→ 写“先看结论 + 正文”；description-only 保持纯资源分享短记
→ 内容完成后做一次版式优化
→ 回看当前允许来源完成覆盖复核
→ finalizer 校验
→ 写入 Obsidian
→ runtime Job 退出活动区并 retire
```

---

## 8. 长视频需要额外操作吗？

不需要。

长字幕会自动整理到当前任务的临时工作区：

```text
.runtime/bilibili-learning/<job>/agent-work/
```

程序会自动生成：

```text
source-manifest.json
source/source-01.txt
source/source-02.txt
...
```

subtitle / ASR 模式会生成 source chunks：短文本通常一个，长文本按 cue 或确定性文本段自动切块，极小尾块自动合并。description-only 只生成 manifest，`chunks` 为空，因为正文来源直接位于 Job 的标题、metadata、简介和用户补充材料中。

这些文件属于 runtime 数据。任务结束后，finalizer / failsafe 会把 Job 从活动区 retire 到 `.runtime/bilibili-learning/retired/`；物理删除属于后续维护，不是笔记成功的前提。用户不需要手工删除。

---

## 9. 生成后的笔记在哪里？

新笔记默认先进入：

```text
<notes_root>/00-待整理/
```

这是“还没正式学习和归档”的统一收件箱。

文件名默认使用原视频标题：

```text
H3智能一体化节点重磅升级.md
```

如果用户明确选择“重新执行一次”，且同名文件已经存在，会生成：

```text
H3智能一体化节点重磅升级（2）.md
```

不会覆盖旧笔记。

笔记主要结构是：

```text
标题 / 作者 · 日期 · 时长 · BV号
→ 先看结论
→ 播放器与来源区（资料获取 / UP 主资源 / 视频简介 / 原文折叠）
→ 知识正文
```

---

## 10. 学完以后怎么整理？

“转成笔记”和“学习后归档”是两个阶段。普通链接转换只负责把资料放到 `00-待整理`，**不会自动整理**。

只有你明确要求整理时，智能体才进入整理流程。如果你已经指定某一篇，直接使用 `single`；如果只说“整理笔记”却没有给出对象，智能体才需要询问：

```text
要整理指定的一篇、最近一篇，还是全部待整理笔记？
```

你选择范围后，智能体会逐篇完整阅读，只决定两件事：

- 更短、更容易长期检索的**文件名**；
- 最适合的**目标目录**，通常采用最多两层的“领域 / 对象”。

归档阶段不会修改 H1、Summary、正文、Frontmatter、Tags、视频简介或 UP 主资源。

统一命令是：

```powershell
bili-learning organize `
  --note '<现有笔记路径>' `
  --filename '<新的简短文件名>' `
  --destination '<领域/对象>' `
  --confirmed-scope '<single|latest|all>'
```

普通用户通常不需要手工运行命令，完整规则见 [笔记整理与归档教程](NOTE-ORGANIZATION.md)。

---

## 11. 常见状态是什么意思

| 状态 | 含义 | 用户通常怎么做 |
| --- | --- | --- |
| `onboarding_required` | 首次环境仍缺少 Vault / Cookie / yt-dlp 等必需配置 | 按返回的 `actions` 处理，再重新检查并重试原链接 |
| `materials_ready` | 当前 `source_mode` 的标准 Job 已准备好 | 按 `source_manifest_path` 和 handoff 继续；`recovered: true` 表示核心已恢复同一来源模式的旧 Job |
| `existing_note_found` | 当前 BVID 已经发布过笔记 | 先选择更新、重新执行或取消；选择后继续使用触发提示时的原始完整消息 |
| `update_target_required` | 同一 BVID 有多篇笔记，尚未指定更新目标 | 明确选择要更新的具体笔记，不自动猜最新一篇 |
| `update_conflict` | 更新期间原笔记又发生了修改 | 不覆盖现有文件；重新发起更新 |
| `in_progress` | 同一 BV 号仍有真实活动任务 | 不要重复启动，也不要手工处理 reservation / lock |
| `subtitle_unavailable` | 没有取得可用中文字幕 | 本次不会生成笔记，也不会下载音视频 |
| `source_insufficient` | 当前来源模式不足以写可靠笔记 | 默认/ASR 可换更完整文字；description-only 应补充简介资料或改走字幕流程 |
| `note_ready` | finalizer 已校验并正式发布 | 完成；runtime retire/维护状态不改变发布结果 |
| `note_invalid` | 草稿没有通过最终校验 | 查看错误，不要绕过 finalizer |
| `failed` | 采集、配置或运行过程失败 | 先运行 doctor，再看故障排查 |

> `in_progress` 是并发保护，不代表视频以后不能再次转换。进程异常结束但材料完整时，核心会自动恢复为 `materials_ready + recovered: true`；正常任务完成并 retire 后，同一个视频仍然可以重新生成另一篇笔记。

---

## 12. 更新项目以后要做什么

代码更新后通常只需要：

```powershell
git pull
```

如果使用 Hermes，并且当前 Gateway / 微信会话已经运行，再发送：

```text
/reload-skills
```

因为 Hermes Skill 推荐通过 Junction 指向仓库源码，所以不需要重新复制 Skill。

如果共享 `obsidian-learning-snippets` 仓库中的 CSS 有更新，按 [Obsidian 样式教程](OBSIDIAN-STYLING.md) 将所需两份 CSS 同步到 Vault，再在 Obsidian 中刷新代码片段。

---

## 13. 出问题时先做什么

第一步永远建议先运行：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

然后查看：

[故障排查](TROUBLESHOOTING.md)

不要优先尝试：

- 手工删除 `.runtime` job；
- 手工删除 reservation / lock；
- 绕过 finalizer 直接复制草稿；
- 把 Cookie 内容贴进聊天或日志；
- 为了字幕失败而自动下载视频做 ASR。

这些操作容易破坏并发保护、Job 恢复 / retire 生命周期或隐私边界。

---

## 14. 下一步阅读

如果你已经成功生成第一篇笔记，可以按需要继续看：

- [Bilibili Cookie 获取与安全配置](BILIBILI-COOKIE.md)：第一次导出 Cookie、格式检查、DPAPI 问题和失效更新；
- [配置说明](CONFIGURATION.md)：换电脑、换 Vault、换 Cookie / yt-dlp 路径；
- [Hermes Skill 安装](HERMES-SKILL-INSTALL.md)：Hermes 安装、更新、验证；
- [Obsidian 样式教程](OBSIDIAN-STYLING.md)：CSS 安装和样式问题；
- [故障排查](TROUBLESHOOTING.md)：状态和错误怎么处理；
- [智能体接入协议](AGENT-INTEGRATION.md)：给开发者 / 新适配层使用；
- [开发说明](DEVELOPMENT.md)：测试、代码维护和 CI。
