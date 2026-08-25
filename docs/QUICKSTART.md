# 新手快速上手

> 文档类型：**操作教程**。适合第一次安装和第一次生成笔记。

这份文档只解决“怎样从零跑通一次”的问题。内部架构、完整配置字段和开发细节分别放在其它说明文档中。

完成本教程后，应能够跑通：

```text
发送 B站链接 / BV号
→ 自动获取字幕、简介和元数据
→ 智能体整理为学习笔记
→ 写入 Obsidian
```

默认流程**不会下载视频或音频**，主要使用 Bilibili 字幕、视频简介和元数据生成学习笔记。

---

## 1. 使用前需要准备什么

Windows 用户准备下面几项即可：

| 需要 | 用途 | 是否必须 |
| --- | --- | --- |
| Python 3.10+ | 运行核心脚本 | 是 |
| yt-dlp | 获取视频元数据、简介、字幕 | 是 |
| Bilibili Cookie 文件 | 提供已登录 Bilibili 的会话凭据，用于字幕 / 元数据访问 | **是** |
| Obsidian Vault | 保存学习笔记；Vault 根目录需直接包含 `.obsidian` | 是 |
| Hermes / WorkBuddy / Codex | 负责阅读字幕并写正文 | 至少一种 |

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

普通用户不需要先猜路径或逐项编辑配置。Hermes、WorkBuddy 与 Codex 的入口都应在正式采集前运行统一 onboarding；核心 `prepare` 也有同一门禁，避免某个 Agent 漏掉首次配置。

统一检查会自动判断 Python、yt-dlp、Cookie、Obsidian Vault 和 CSS 状态，只对真正缺失的项目采取动作：

- Vault 未配置：询问直接包含 `.obsidian` 的 Vault 根目录；笔记子目录默认 `bilibili`；
- Cookie 未配置：只询问 Netscape 格式 Cookie **文件路径**，不要在聊天中粘贴 Cookie 内容；
- yt-dlp 未检测到：项目不会自动安装或复制可执行文件，Windows 默认推荐 `winget install yt-dlp`；只有已经安装在自定义目录时才需要提供可执行文件路径；
- CSS 缺失：只提醒，不阻塞笔记生成，也不会静默复制或覆盖用户文件。

手动检查可运行：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\onboarding_bilibili_learning.py
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
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

如果环境正确，你应该看到 yt-dlp、Cookie、taxonomy、Vault、notes/runtime 写权限等检查通过。doctor 还会检查 `learning-lab.css` 与 `video-note.css` 是否位于当前 Vault 的 `.obsidian/snippets/`。

如果看到 `notes_repository_fallback`，说明还没有显式绑定 Vault。此时新的视频采集会被 onboarding 门禁拦住，并返回 `onboarding_required`；不会把私人笔记静默写入代码仓库。你可以修改 `config/local.json`，也可以运行：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\configure_bilibili_learning.py --vault 'D:\Notes\MyVault' --notes-subdir 'bilibili'
```

该命令只写本机 `config/local.json`，并要求 `--vault` 真正包含 `.obsidian`。

如果要让智能体读取结构化诊断结果：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py --json
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
| Hermes | 手机 / 微信直接发 B站链接 | 安装 Hermes Skill 后私聊发送链接 |
| WorkBuddy | WorkBuddy 会话中转笔记 | 安装 WorkBuddy 适配层后发送链接 |
| Codex | 开发、测试、手动执行 | 在项目目录中按共享协议调用核心流程 |

### Hermes

Hermes 使用：

```text
hermes-skills/bili-learning-automation/
```

建议使用 Junction 安装，更新仓库后无需再次复制文件。完整步骤见：

[Hermes Skill 安装教程](HERMES-SKILL-INSTALL.md)

### WorkBuddy

WorkBuddy 适配层位于：

```text
workbuddy-skills/bili-learning-automation/
```

它只是入口适配层，实际仍调用同一套核心 collector、transcript、finalizer 和笔记标准。

第一次安装见 [WorkBuddy Skill 安装教程](WORKBUDDY-SKILL-INSTALL.md)。

### Codex

Codex 不需要额外复制一份 Skill。进入项目后先读取：

```text
AGENTS.md
```

再按 collector 返回的 `workflow_mode` 选择 `LIGHT-WORKFLOW.md` 或严格流程文档。普通使用默认采用 `light`。

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

正常情况下，你不需要再输入命令、指定文件名或手动处理字幕。

智能体会自动完成：

```text
识别链接
→ yt-dlp 获取字幕 / 简介 / 元数据
→ 生成 transcript
→ 判断资料是否足够
→ 完整读字幕并写“先看结论 + 知识正文”
→ 内容完成后做一次版式优化
→ 回看字幕完成覆盖复核
→ finalizer 校验
→ 写入 Obsidian
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
transcript-manifest.json
transcript/transcript-01.txt
transcript/transcript-02.txt
...
```

短字幕通常直接读取一个 chunk；长字幕会按完整字幕 cue 自动切块。极小尾块会自动并入前一块，避免智能体为了几十个字符再多执行一次读取。

这些文件只是临时数据，任务结束后由 finalizer / failsafe 清理。用户不需要手工删除。

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

如果同名文件已经存在，会自动生成：

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
| `materials_ready` | 字幕、简介等材料已经准备好 | 等智能体继续写笔记 |
| `in_progress` | 同一 BV 号已有活动任务 | 不要重复启动；Hermes 可在安全条件下续做陈旧未完成 job |
| `subtitle_unavailable` | 没有取得可用中文字幕 | 本次不会生成笔记，也不会下载音视频 |
| `source_insufficient` | 字幕 / 简介不足以写可靠笔记 | 换资料更完整的视频 |
| `note_ready` | finalizer 已校验并正式发布 | 完成 |
| `note_invalid` | 草稿没有通过最终校验 | 查看错误，不要绕过 finalizer |
| `failed` | 采集、配置或运行过程失败 | 先运行 doctor，再看故障排查 |

> `in_progress` 是并发保护，不代表视频以后不能再次转换。当前任务结束后，同一个视频仍然可以重新生成另一篇笔记。

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

这些操作容易破坏并发保护、清理机制或隐私边界。

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
