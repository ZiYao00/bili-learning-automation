# 新手快速上手

这份文档面向第一次使用 **B站视频转笔记** 的用户。目标不是解释内部实现，而是让你从零完成一次：

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
| Bilibili Cookie 文件 | 获取需要登录态的字幕 / 元数据 | 通常需要 |
| Obsidian Vault 或 Markdown 目录 | 保存学习笔记 | 是 |
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

## 3. 配置 yt-dlp、笔记目录和 Cookie

最适合普通用户的是 `config/local.json`。

先复制模板：

```powershell
Copy-Item .\config\local.json.example .\config\local.json
```

然后修改成本机路径，例如：

```json
{
  "ytdlp": "G:\\Program\\yt-dlp\\yt-dlp.exe",
  "notes_root": "D:\\Notes\\MyVault\\bilibili",
  "cookie_file": "D:\\Private\\bilibili_cookies.txt"
}
```

三个字段分别表示：

- `ytdlp`：`yt-dlp.exe` 的位置；
- `notes_root`：生成笔记的根目录；
- `cookie_file`：Netscape 格式 Bilibili Cookie 文件的位置。

`config/local.json` 已被 Git 忽略，适合保存本机路径。

如果不想使用 `local.json`，也可以通过环境变量配置，详见 [配置说明](CONFIGURATION.md)。

---

## 4. 检查配置是否正确

正式测试前先运行 doctor：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

如果环境正确，你应该看到 yt-dlp、Cookie、taxonomy、notes/runtime 写权限等检查通过。

如果要让智能体读取结构化诊断结果：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py --json
```

> doctor 不访问 Bilibili、不读取 Cookie 内容，也不会留下测试文件。

---

## 5. 安装 Obsidian 样式

仓库已经包含两份样式：

```text
obsidian/snippets/
├── learning-lab.css
└── video-note.css
```

把它们复制到当前 Obsidian Vault 的：

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

Codex 不需要额外复制一份 Skill。进入项目后遵循：

```text
AGENTS.md
docs/AGENT-INTEGRATION.md
```

即可使用核心流程。

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
→ 提取知识
→ 写“先看结论 + 知识正文”
→ 覆盖复核
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
标题 / BV号
→ 先看结论
→ Bilibili 播放器
→ 知识正文
→ 视频资料
```

---

## 10. 学完以后怎么整理？

“转成笔记”和“学习后归档”是两个阶段。

普通链接转换只负责把资料放到 `00-待整理`。

当你已经学习完某篇笔记后，可以明确告诉智能体：

```text
帮我整理这篇笔记
```

整理流程会处理：

- 更适合长期使用的短标题；
- 一句简介摘要；
- taxonomy 建议目录；
- 安全移动文件；
- 重建导航。

核心命令是：

```powershell
bili-learning organize --note '<笔记路径>' --title '<短标题>' --intro '<一句简介摘要>'
```

普通用户通常不需要手工执行，由智能体调用即可。

---

## 11. 常见状态是什么意思

| 状态 | 含义 | 用户通常怎么做 |
| --- | --- | --- |
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

如果 `obsidian/snippets/` 中的 CSS 有更新，再覆盖 Vault 里的两份 CSS，并在 Obsidian 中刷新代码片段。

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

- [配置说明](CONFIGURATION.md)：换电脑、换 Vault、换 yt-dlp 路径；
- [Hermes Skill 安装](HERMES-SKILL-INSTALL.md)：Hermes 安装、更新、验证；
- [Obsidian 样式教程](OBSIDIAN-STYLING.md)：CSS 安装和样式问题；
- [故障排查](TROUBLESHOOTING.md)：状态和错误怎么处理；
- [智能体接入协议](AGENT-INTEGRATION.md)：给开发者 / 新适配层使用；
- [开发说明](DEVELOPMENT.md)：测试、代码维护和 CI。
