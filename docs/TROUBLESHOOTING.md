# 疑难解答 / 故障排查

> 文档类型：**疑难解答**。按“状态 / 症状 → 原因 → 处理方式”查找，不需要从头通读。

遇到问题时，不建议一上来就删 `.runtime`、删锁文件或重装全部环境。

先运行：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

如果需要给智能体分析：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py --json
```

doctor 不访问 Bilibili，也不读取 Cookie 内容。

快速定位：

| 你看到的问题 | 先看 |
| --- | --- |
| 返回 `onboarding_required` / `in_progress` / `note_invalid` 等状态 | [第 1 节：状态表](#1-先看状态不要先猜原因) |
| 找不到 yt-dlp | [第 3 节：未找到 yt-dlp](#3-未找到-yt-dlp) |
| Cookie 不存在或登录态失效 | [第 4 节：Cookie 文件不存在或登录态失效](#4-cookie-文件不存在或登录态失效) |
| 没有字幕 | [第 5 节：subtitle_unavailable](#5-subtitle_unavailable) |
| Hermes 更新后仍像旧版本 | [第 8 节](#8-hermes-更新了-skill但好像还在使用旧版本) |
| Hermes 只分析、不继续执行 | [第 9 节](#9-hermes-会分析但不继续执行) |
| 长视频处理慢 | [第 10 节](#10-长视频读取很慢) |
| Obsidian 有内容但没样式 | [第 11 节](#11-obsidian-笔记有内容但没有样式) |
| `organize` 失败 | [第 13 节](#13-organize-失败) |

---

## 1. 先看状态，不要先猜原因

| 状态 | 含义 | 推荐处理 |
| --- | --- | --- |
| `onboarding_required` | 首次环境仍缺少 Vault / Cookie / yt-dlp 等必需配置 | 按 `actions` 处理缺失项，重新运行 onboarding 后再重试原链接 |
| `materials_ready` | 采集完成，等待智能体写笔记 | 正常继续 |
| `in_progress` | 同 BV 已有活动任务 | 不重复采集；等待或由适配层安全续做陈旧 job |
| `subtitle_unavailable` | 没有取得可用中文字幕 | 本次停止；若人工确认视频完全无字幕，可按第 5 节使用手动 ASR 旁路 |
| `source_insufficient` | 字幕 / 简介不足以写可靠笔记 | 换资料更完整的视频 |
| `note_ready` | Finalizer 校验通过 | 完成 |
| `note_invalid` | 草稿未通过最终校验 | 看错误原因，不绕过 finalizer |
| `failed` | 配置、采集或运行失败 | 先 doctor，再按下面对应项检查 |

---

## 2. `in_progress`：为什么不能马上重新采集

`in_progress` 是并发保护。

如果 Hermes、WorkBuddy 或其他入口正在处理同一个 BV，第二个入口再次采集可能造成：

- 同一视频重复下载字幕；
- 两个 Agent 同时改 analysis / draft；
- 两个 finalizer 竞争同一输出；
- 临时 job 和锁状态混乱。

所以活动任务期间不会重复采集。

这**不代表视频以后不能再次转换**。当前 job 结束并被清理后，可以重新生成另一篇笔记。

### Hermes 遇到旧的未完成 job

新版 Hermes 适配层会优先使用 collector 返回的绑定 `job_dir`。

只有同时满足以下条件时才续做：

- reservation 已明显陈旧；
- job 必需文件完整；
- transcript manifest 和 chunks 完整；
- 草稿 AI 区仍未填写；
- `analysis.json` 仍处于 pending。

这样可以接回“会话中断但材料已经采集完成”的任务，同时避免抢占真正还在执行的任务。

不要手工删除 reservation / lock 来强制绕过。

---

## 3. 未找到 yt-dlp

常见提示：

```text
ytdlp_not_configured
ytdlp_path_invalid
ytdlp_not_executable
```

项目不会内置或自动安装 yt-dlp。第一次使用优先让 doctor 自动检测；Windows 如果返回 `ytdlp_not_configured`，先按官方方式安装：

```powershell
winget install yt-dlp
```

安装后重新运行 doctor。仍然找不到时再检查：

1. 新终端中能否直接运行 `yt-dlp --version`；
2. 当前 Agent 进程是否继承到更新后的 PATH；
3. 是否设置了错误的 `BILI_LEARNING_YTDLP`；
4. `config/local.json` 是否存在错误的自定义 `ytdlp` 路径；
5. 如果使用自定义目录，文件是否真实存在且可执行。

不要通过把 `yt-dlp.exe` 复制进 Skill 或仓库来解决。配置说明见 [CONFIGURATION.md](CONFIGURATION.md)。

---

## 4. Cookie 文件不存在或登录态失效

如果 onboarding 返回：

```text
cookie_file_required
```

先确认配置里保存的是**Cookie 文件路径**，不是 Cookie 内容。项目需要 Mozilla / Netscape 格式的完整 `cookies.txt`，不是单个 `SESSDATA`、JSON 或 `Cookie:` 请求头。

可能来源：

```text
config/local.json
BILI_LEARNING_COOKIE_FILE
key/bilibili_cookies.txt
```

第一次完全不知道怎样获得 Cookie 时，不要在 F12 里手工拼字段，直接阅读：

**[Bilibili Cookie 获取与安全配置](BILIBILI-COOKIE.md)**

里面包含浏览器导出 Netscape `cookies.txt`、文件格式判断、保存位置、安全边界和失效后的重新导出方式。

### 文件存在，但实际采集仍失败

Doctor 只检查 Cookie **文件是否存在**，不会读取凭据或登录 Bilibili 验证有效性。因此 `[OK] cookie file exists` 不代表账号会话一定仍然有效。

如果文件存在但 yt-dlp 仍然无法获取登录态资料，优先检查：

1. 浏览器里的 Bilibili 账号是否仍然登录；
2. 是否最近重新导出过 Cookie；
3. 文件首行是否为 `# Netscape HTTP Cookie File` 或 `# HTTP Cookie File`；
4. `config/local.json` 是否指向正确的新文件；
5. 是否误用了只包含 `SESSDATA` 的文本，而不是完整 `cookies.txt`。

### `Failed to decrypt with DPAPI`

如果 Windows Chrome / Chromium 直接通过 `--cookies-from-browser` 读取时出现：

```text
Failed to decrypt with DPAPI
```

不要继续尝试绕过浏览器本地加密。改用浏览器内的可信 Cookie 导出工具生成 Netscape `cookies.txt`，或者使用 Firefox 登录 Bilibili 后重新导出，再把文件路径配置给项目。

### 安全提醒

不要把 Cookie 内容复制到：

- README；
- Issue / PR；
- 日志；
- 聊天记录；
- Git；
- 截图或公开网盘。

Agent 只需要 Cookie **文件路径**。

---

## 5. `subtitle_unavailable`

这表示没有取得：

```text
ai-zh
或
zh.*
```

可用字幕。

项目默认策略是**字幕优先、宁缺毋滥**，因此正常 Skill 流程不会自动：

- 下载视频；
- 下载音频；
- 调 ASR 补字幕；
- 用模型常识代替原视频内容。

如果视频本身没有可用字幕，本次不生成笔记是正常行为。

### 已确认视频完全无字幕：手动 ASR 旁路

只有在人工确认视频确实没有可提取字幕时，才考虑项目级辅助脚本：

```powershell
python .\scripts\bili_asr_fallback.py "https://www.bilibili.com/video/BV..." `
  --output "$env:TEMP\BV-transcript.txt"
```

该脚本不属于 collector / finalizer 的正常执行链，也不会改变 `subtitle_unavailable` 的含义。它只做：

```text
B站链接 → yt-dlp 临时下载低码率音轨 → SiliconFlow STT → transcript.txt
```

默认使用 `FunAudioLLM/SenseVoiceSmall`，优先读取 `config/local.json` 中现有的 yt-dlp 路径，并可复用项目 `key/` 下已有 Cookie。API Key 默认读取本机 `config/local.json` 的 `siliconflow.api_key`；也可由 `SILICONFLOW_API_KEY` 或显式 `--api-key-file` 覆盖。`config/local.json` 已被 Git 忽略，公开仓库只能提交 `config/local.json.example` 中的占位符，真实 Key 不得进入 README、日志或 Git。

音频默认存放在系统临时目录并在脚本结束后自动清理；只有显式传入 `--keep-audio` 才会保留。输出文本和可选保留音频如果目标文件已存在都会停止，不会覆盖。当前 SiliconFlow STT 单文件限制为不超过 50MB、时长不超过 1 小时，脚本会在上传前检查这两个条件。

输出是无伪造时间戳的纯文本 transcript。它适合作为人工异常处理的事实来源；不要把整段文本伪装成单条 SRT，也不要把这条旁路描述成正常 Skill 已自动完成。

---

## 6. `failed: 无法确认 UP 主原始简介`

项目会区分：

```text
present
confirmed_empty
failed
```

只有元数据明确提供空字符串，才能认为 UP 主简介“确认为空”。

如果 description 字段缺失、类型异常或不同来源不一致，不能擅自推断“视频没有简介”，任务会停止。

这是数据完整性保护，不建议绕过。

---

## 7. `note_invalid`

Finalizer 会检查：

- Frontmatter；
- H1；
- BVID；
- 视频简介结构；
- iframe；
- tags；
- `BILI_AI_SUMMARY`；
- `BILI_AI_BODY`；
- 来源充分性；
- `knowledge_outline`；
- coverage review。

没有通过就不会正式发布。

不要为了“先生成出来再说”而绕过 finalizer，因为这样会把半成品混入正式 Obsidian 笔记。

---

## 8. Hermes 更新了 Skill，但好像还在使用旧版本

先确认安装是 Junction：

```powershell
Get-Item "$env:LOCALAPPDATA\hermes\skills\bili-learning-automation" |
  Format-List FullName,LinkType,Target
```

`Target` 应指向当前仓库：

```text
<project-root>\hermes-skills\bili-learning-automation
```

然后在 Hermes 会话发送：

```text
/reload-skills
```

再要求 Hermes：

```text
重新读取当前安装的 SKILL.md，不要根据之前会话记忆回答。
```

完整教程见 [Hermes Skill 安装](HERMES-SKILL-INSTALL.md)。

---

## 9. Hermes 会分析，但不继续执行

先不要改核心 Skill。

优先排查：

1. Hermes 主程序是否正常；
2. Gateway 是否正常；
3. 当前模型是否适合 Agent / Tool Use；
4. Hermes 的工具执行约束是否启用；
5. 当前 Skill 是否已经 reload；
6. doctor 是否全绿。

如果 Codex / WorkBuddy 可以完成同一个任务，而 Hermes 经常停在“准备做”“需要你选择下一步”，更可能是 Hermes 模型或 Agent 调度问题，而不是 collector / finalizer 本身。

---

## 10. 长视频读取很慢

新版流程不会让 Agent 自己把整份超长 SRT 硬塞进上下文。

任务准备阶段会自动生成：

```text
agent-work/
├── transcript-manifest.json
└── transcript/
    ├── transcript-01.txt
    ├── transcript-02.txt
    └── ...
```

单个 chunk 在工具限制内时应优先一次读完；只有工具明确截断时才继续读取剩余部分。

如果日志里仍看到 Agent 主动把一个正常 chunk 再拆成很多小段，优先检查适配层和模型执行行为，而不是继续缩小 transcript chunk。

---

## 11. Obsidian 笔记有内容，但没有样式

确认共享 <https://github.com/ZiYao00/obsidian-learning-snippets> 中、并由 [`config/obsidian-style.json`](../config/obsidian-style.json) 声明的 `learning-lab.css` 和 `video-note.css`，已经安装到**当前打开 Vault 根目录**的：

```text
.obsidian/snippets/
```

然后在：

```text
Obsidian → 设置 → 外观 → CSS 代码片段
```

同时启用：

```text
learning-lab
video-note
```

`video-note.css` 依赖 `learning-lab.css`。

如果 `notes_root` 只是 Vault 的一个子目录，CSS 仍然应该放在 Vault 根目录的 `.obsidian/snippets/`。

完整教程见 [Obsidian 视觉样式](OBSIDIAN-STYLING.md)。

---

## 12. 短链无法解析

项目只允许受支持的 Bilibili 官方域名，并限制重定向次数和超时。

如果 `b23.tv` 无法解析，最简单的处理是回到 Bilibili，重新使用“复制链接”，再发送标准链接。

不要把不明来源的重定向域名加入白名单来绕过安全限制。

---

## 13. `organize` 失败

整理功能默认关闭。先确认用户已经明确选择：

```text
latest = 最近一篇
all    = 全部待整理笔记
```

然后检查：

- `--note` 是否位于 notes root 内；
- 笔记是否已经正式发布；
- `--title` 与 `--intro` 是否非空；
- `--confirmed-scope` 是否是 `latest` 或 `all`；
- `--category` 是否存在于 `taxonomy.organization.categories`；
- 是否至少提供一个 `--tag`；
- 整理后的 tags 是否仍只剩 `待整理`（Organizer 会移除该标签）。

如果返回“整理功能默认不执行”，说明 Agent 在没有用户范围确认的情况下调用了 Organizer。不要绕过这道门禁。

不要手工移动文件后再让导航脚本猜当前状态。正确流程是由 `organize` 统一完成原视频标题保留、短标题更新、tags 更新、安全移动和导航重建。完整规则见 [笔记整理与归档教程](NOTE-ORGANIZATION.md)。

---

## 14. 不建议的“修复方式”

遇到异常时，优先不要做这些操作：

```text
手工删除整个 .runtime
手工删除 reservation
手工删除 lock
绕过 finalizer
直接复制 runtime 草稿到 notes
把 Cookie 内容贴给 Agent
为了无字幕自动下载视频做 ASR
```

这些操作可能让当前问题暂时消失，但会破坏并发保护、清理边界或数据可信度。

更好的顺序是：

```text
看 status
→ doctor
→ 检查对应配置 / adapter
→ 保留现场定位
→ 再决定是否重新发起任务
```
