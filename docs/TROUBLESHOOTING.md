# 疑难解答 / 故障排查

> 文档类型：**疑难解答**。按“状态 / 症状 → 原因 → 处理方式”查找，不需要从头通读。

遇到问题时，不建议一上来就删 `.runtime`、删锁文件或重装全部环境。

先运行：

```powershell
.\scripts\run_bili_learning.ps1 doctor
```

如果需要给智能体分析：

```powershell
.\scripts\run_bili_learning.ps1 doctor --json
```

doctor 不访问 Bilibili，也不读取 Cookie 内容。

快速定位：

| 你看到的问题 | 先看 |
| --- | --- |
| 返回 `onboarding_required` / `in_progress` / `note_invalid` 等状态 | [第 1 节：状态表](#1-先看状态不要先猜原因) |
| WorkBuddy 出现 `windows-sandbox-recycle-bin-unavailable` / safe-delete | [第 2 节：旧 Job 恢复与 safe-delete](#2-in_progressrecovered-与旧-job-恢复) |
| 找不到 yt-dlp | [第 3 节：未找到 yt-dlp](#3-未找到-yt-dlp) |
| Cookie 不存在或登录态失效 | [第 4 节：Cookie 文件不存在或登录态失效](#4-cookie-文件不存在或登录态失效) |
| 没有字幕 | [第 5 节：subtitle_unavailable](#5-subtitle_unavailable) |
| Hermes 更新后仍像旧版本 | [第 8 节](#8-hermes-更新了-skill但好像还在使用旧版本) |
| Hermes 只分析、不继续执行 | [第 9 节](#9-hermes-会分析但不继续执行) |
| 长视频处理慢 | [第 10 节](#10-长视频读取很慢) |
| Obsidian 有内容但没样式 | [第 11 节](#11-obsidian-笔记有内容但没有样式) |
| `organize` 失败 | [第 13 节](#13-organize-失败) |

---

### Python 缺失或版本不符合要求

运行 `scripts/run_bili_learning.ps1 -ProbeOnly`。如果返回 `python_required`，说明 Python 尚不可用，不能直接运行 `python scripts/run_bili_learning.py`。Agent 应先检查现有 Python 3.10+；如确实不存在，则在取得用户授权后准备官方 Python 3.12，并重新检测。已有 `.venv` 如果无效会被跳过；若系统环境无法发现可信 Python，Agent 可仅在当前 PowerShell 会话设置 `$env:BILI_LEARNING_PYTHON` 为正确的解释器绝对路径。这个变量只影响 Python 解析器，不会改变项目内固定的 yt-dlp EXE。不得无授权安装软件或修改用户系统 PATH。

---

## 1. 先看状态，不要先猜原因

| 状态 | 含义 | 推荐处理 |
| --- | --- | --- |
| `onboarding_required` | 首次环境仍缺少 Vault / Cookie / yt-dlp 等必需配置，或 hybrid 笔记映射无效 | 按 `actions` 处理缺失项；映射无效时先修复 Vault 到 `notes_root` 的 Junction，再重新运行 onboarding |
| `materials_ready` | 采集完成，等待智能体写笔记 | 正常继续；若同时有 `recovered: true`，表示核心已恢复此前完整 Job，不会重复采集 |
| `existing_note_found` | 当前 BVID 已有已发布笔记 | 采集尚未开始；先让用户选择更新、重新执行或取消 |
| `update_target_required` | 同一 BVID 有多篇笔记且未指定更新目标 | 让用户明确选择具体笔记，不自动猜最新或最旧 |
| `update_conflict` | 更新期间目标笔记被再次修改 | 原笔记未被覆盖；重新读取最新版本后再发起更新 |
| `in_progress` | 同 BV 仍有真实活动任务 | 不重复采集，不手工删 job / reservation / lock |
| `subtitle_unavailable` | 没有取得可用中文字幕 | 本次停止；若人工确认视频完全无字幕，可按第 5 节使用手动 ASR 旁路 |
| `source_insufficient` | 字幕 / 简介不足以写可靠笔记 | 换资料更完整的视频 |
| `note_ready` | Finalizer 校验通过并已发布 | 业务完成；runtime retire/维护状态不改变发布结果 |
| `note_invalid` | 草稿未通过最终校验 | 看错误原因，不绕过 finalizer |
| `failed` | 配置、采集或运行失败 | 先 doctor，再按下面对应项检查 |

### hybrid 笔记映射异常

如果 onboarding 的 actions 出现 `obsidian_notes_mapping_invalid`，检查 Vault 子目录是不是正确的 Junction，并确认它最终解析到配置的 `notes_root`。推荐方向固定为 **Vault → 项目 notes**；不要把项目 `notes/bilibili` 反向链接到工作区外。修复后重新运行 onboarding，只有 `obsidian_notes_mapping = OK` 才继续采集。

---

## 2. `in_progress`、`recovered` 与旧 Job 恢复

`in_progress` 是并发保护，只表示同一个 BV **仍有真实活动任务**。

如果 Hermes、WorkBuddy 或其他入口正在处理同一个 BV，第二个入口再次采集可能造成：

- 同一视频重复下载字幕；
- 两个 Agent 同时改 analysis / draft；
- 两个 finalizer 竞争同一输出；
- runtime 状态互相覆盖。

所以活动任务期间不会重复采集。

这**不代表视频以后不能再次处理**。正常任务完成后，Job 会退出活动区并 retire；reservation 会切换为 `released`。之后再次发送同一 BVID 时，核心先返回 `existing_note_found`：只有用户明确选择 `rerun` 才生成独立新笔记，选择 `update` 则保留指定旧笔记路径并进入受控更新。

### 进程异常结束，但材料已经完整

旧版本主要依赖适配层判断“能否续做”；当前版本已经把恢复逻辑收回共享核心。

如果 reservation 的持有进程已经结束，而绑定 Job 仍具备 `job.json`、草稿、`analysis.json`、transcript manifest、字幕等完整材料，`prepare` 会：

1. 验证已有 Job 是否完整；
2. 缺少 `agent_handoff.md` 时自动重建；
3. **不重新调用 yt-dlp**；
4. 返回 `materials_ready`，并附带 `recovered: true`。

因此 Agent 只需要按正常 `materials_ready` 继续写作，不需要自己判断 PID、stale timeout 或底层锁状态。

### WorkBuddy 的 safe-delete / `windows-sandbox-recycle-bin-unavailable`

当前 runtime 主链已经不再依赖删除权限：

- `note-names.lock`、navigation lock 和 reservation claim 使用 OS 文件锁；锁文件可以长期存在，不靠 `unlink()` 释放；
- reservation 使用 `active / released` 状态覆盖，不靠删除文件释放；
- Job 完成后从活动区移动到 `.runtime/bilibili-learning/retired/`，物理删除属于后续维护；
- Finalizer 的 `note_ready` 与 runtime retire/维护状态解耦；
- 发布 staging 保留在 Job 内，不再要求发布后删除临时文件。

因此 WorkBuddy 的 safe-delete 即使阻止 `Path.unlink()` / `shutil.rmtree()`，也不应再让正常 `prepare → finalize` 主链失败。

如果当前版本仍出现 `windows-sandbox-recycle-bin-unavailable` 并中断任务，优先确认 WorkBuddy 是否重新读取了最新 Skill / 仓库代码；**不要修改 WorkBuddy 内置 `sitecustomize.py`，也不要手工删除 reservation / lock / job 来绕过。**

---

## 3. 项目内 yt-dlp 缺失或无法运行

常见代码：`ytdlp_not_configured`、`ytdlp_path_invalid`、`ytdlp_not_executable`。

此项目的唯一执行文件是：

```text
<repo-root>\tools\yt-dlp.exe
```

**不要运行 `winget install yt-dlp`，不要查找系统 PATH，也不要在 `local.json` 配置其它 yt-dlp 路径。** Agent 应检查该文件是否存在、可执行及版本。缺失或校验不符时，只从官方 Release 或可信完整项目副本恢复项目内 EXE，同步 `tools/yt-dlp.release.json` 与第三方许可证，再重新运行 doctor。

```powershell
& '<repo-root>\tools\yt-dlp.exe' --version
python .\scripts\run_bili_learning.py doctor --json
```

旧配置的 `ytdlp` 键和 `BILI_LEARNING_YTDLP` 不参与路径解析。Windows EXE 不支持 Linux 运行；Linux CI 仅测试通用 Python 逻辑与受控模拟，不声明跨平台采集可用。

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

### 用户明确只要“纯资源分享 / 只整理简介”

这不是 `subtitle_unavailable` 的自动回退。只有用户当前消息明确要求“不用字幕 / 跳过字幕 / 只整理简介”时，才使用：

```powershell
bili-learning prepare-description "https://www.bilibili.com/video/BV..."
```

该入口只采集 metadata 与 UP 主简介，不请求字幕、不下载媒体、不调用 ASR。它创建 `source_mode = description_only` 的标准 Job，并继续走 handoff / finalizer；不得根据视频标题或历史偏好自动选择，也不得直接修改已发布笔记。简介不足时应返回来源不足，而不是推断视频口播或画面内容。

### 已确认无字幕：按授权调用本地 ASR

默认 `prepare` 返回 `subtitle_unavailable` 后，只有用户明确授权本次 ASR，Agent 才先运行 `scripts/run_bili_learning.ps1 asr-health`，确认 `ready` 后运行 `scripts/run_bili_learning.ps1 prepare-asr '<原始完整消息>'`。此入口先按 BVID 查重并取得 reservation，之后才临时下载音轨、分块提交本机 `local-ASR-service`，回流标准 Job 并继续 finalizer；不伪造 SRT 或时间戳。

当服务未启动时，参照 [独立服务文档](DEPENDENCIES.md) 在获得操作授权后检查 `service.bat status`、必要时启动已安装的服务，不应重新安装模型或停止其它使用者的任务。

`asr_outcome_unknown` 表示客户端断线或超时，**服务端可能仍在执行**。先检查 `/health.queue`、服务日志；当前没有任务 ID 可找回断开的转录结果，不能自动再次 POST。`asr_unavailable` 则优先排查健康状态、FFmpeg/VAD/标点；音频下载失败应检查 B站权限和 Cookie，而不是改 ASR 模型。

历史脚本 `scripts/bili_asr_fallback.py` 保留为可选 SiliconFlow 手动兼容路径，不属于默认 Skill 工作流；新用户无需配置 SiliconFlow API Key。

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
<project-root>\skill\bili-learning-automation
```

然后在 Hermes 会话发送：

```text
/reload-skills
```

再要求 Hermes：

```text
重新读取当前安装的 SKILL.md，不要根据之前会话记忆回答。
```

完整教程见 [本地 Agent Skill 安装](LOCAL-AGENT-INSTALL.md)。

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

### `obsidian_notes_mapping_invalid`

这表示当前使用 hybrid 配置，但 `<vault_root>/<notes_subdir>` 没有解析到 `notes_root`。先停止采集，不要改写 `notes_root` 去迁就错误的 Vault 路径。

Windows 上检查：

```powershell
Get-Item '<vault-root>\bilibili' | Format-List FullName,LinkType,Target
```

正确状态应为 `LinkType = Junction`，`Target` 指向 `<repo-root>\notes\bilibili`。Agent 应先通过 `scripts/ensure_junction.ps1` 执行只读计划；目标目录如已有笔记，必须停止并报告冲突，**不得自动复制、删除、移动或替换**。数据迁移应作为另一个经用户授权的独立任务，完成备份和校验后才能处理。修复后重新运行 `onboarding`，确认 `obsidian_notes_mapping = OK`。

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

这些操作可能让当前问题暂时消失，但会破坏并发保护、Job 恢复 / retire 生命周期或数据可信度。

更好的顺序是：

```text
看 status
→ doctor
→ 检查对应配置 / adapter
→ 保留现场定位
→ 再决定是否重新发起任务
```
