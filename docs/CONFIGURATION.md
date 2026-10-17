# 配置说明

普通用户优先让 Agent 通过 onboarding 检查并补齐缺失配置；这些本机值最终保存到 `config/local.json`。它用于保存当前电脑的本地路径与私密配置，并已被 Git 忽略；公开仓库只提交 `config/local.json.example`。高级用户也可以直接手工维护这个文件。

当前推荐把“真实存储”和“Obsidian 展示路径”分开：

```text
notes_root    = 真实 Markdown 存储目录；推荐 <repo-root>/notes/bilibili
vault_root    = Obsidian Vault 根目录（直接包含 .obsidian）
notes_subdir  = Vault 内显示本项目笔记的相对子目录
Vault 映射    = <vault_root>/<notes_subdir> -> Junction -> <notes_root>
```

这样本地 Agent / CodexPro 始终读写授权工作区内的 `notes_root`，Obsidian 仍能在自己的 Vault 里看到同一批文件，同时 doctor 仍可检查 `.obsidian/snippets/` 和 Junction 映射。

---

## 1. 推荐配置

项目模板：

```text
config/local.json.example
```

复制后修改为自己的路径：

```json
{
  "notes_root": "notes/bilibili",
  "vault_root": "D:\\Notes\\MyVault",
  "notes_subdir": "bilibili",
  "cookie_file": "key/bilibili_cookies.txt",
  "local_asr_base_url": "http://127.0.0.1:8191",
  "workflow_mode": "light"
}
```

真实笔记会写到：

```text
<repo-root>\notes\bilibili\00-待整理\
```

Obsidian 中的 `D:\Notes\MyVault\bilibili` 推荐做成指向上述目录的 Junction；doctor 会校验它与 `notes_root` 是否解析到同一位置。

CSS 则应该位于：

```text
D:\Notes\MyVault\.obsidian\snippets\
```

### `yt-dlp`：固定项目内单文件 EXE

所有采集、简介和 ASR 临时音频流程只调用 `<repo-root>/tools/yt-dlp.exe`。项目不安装源码，不使用 `winget`，不查询系统 PATH，不使用 `BILI_LEARNING_YTDLP` 或 `local.json.ytdlp` 自定义路径。现有本机配置中的旧 `ytdlp` 字段可继续被解析，但**已失效且不会影响实际执行**；无需强制清除旧文件。

如果 EXE 缺失，Agent 应从经过校验的官方来源或完整项目副本恢复，确认 `tools/yt-dlp.release.json` 的 SHA-256 与可执行版本，然后重新运行 onboarding。不得把文件放进 Skill 安装目录，也不得静默下载或替换现有 EXE。

### `local_asr_base_url`（可选外部能力）

`local-ASR-service` 是独立共享基础设施，不属于本项目必需依赖。默认地址为：

```text
http://127.0.0.1:8191
```

普通字幕流程不会检查、启动或调用它，也不会下载音频。只有默认 `prepare` 已确认 `subtitle_unavailable`，并且用户明确授权 ASR 后，Agent 才运行：

```powershell
python .\\scripts\\run_bili_learning.py asr-health
python .\\scripts\\run_bili_learning.py prepare-asr '<原始完整消息>'
```

`prepare-asr` 会先按 BVID 查重、检查更新目标并占用现有 reservation，再临时下载音轨，通过有 Content-Length 的分块上传调用外部 `local-ASR-service /v1/audio/transcriptions`；取得真实纯文本后复用标准 `prepare-transcript / asr_text` Job lifecycle。临时音轨和中间 transcript 不作为长期业务资产保存；重复笔记不会触发下载或转录。本项目不会安装、复制或启动另一套 FunASR / Whisper Pipeline。

ASR 是共享的可选服务：`asr-health` 的 `ready` 返回设备、模型和 `queue` 信息。未启动时按独立 [安装文档](DEPENDENCIES.md) 在授权范围内检查 / 启动已有服务，不能在此仓库重复安装。转录请求可能在服务端队列中等待，客户端网络断开或超时会返回 `asr_outcome_unknown`：它**不表示转录必定失败**，请先检查 `local-ASR-service /health.queue`，不自动再次提交相同 POST；服务端当前没有可按 Job ID 找回结果的接口。

如外部服务使用其他地址，可在本机配置：

```json
"local_asr_base_url": "http://127.0.0.1:8191"
```

也可用 `BILI_LEARNING_LOCAL_ASR_BASE_URL` 临时覆盖。该能力是可选项，因此服务未启动不会让 onboarding 失败。

### `vault_root`

Obsidian Vault 根目录，必须是直接包含 `.obsidian` 的目录，例如：

```text
D:\Notes\MyVault\
├── .obsidian\
├── bilibili\
└── 其它笔记\
```

不要把 `D:\Notes\MyVault\bilibili` 错写成 `vault_root`，除非它本身就是一个独立 Vault，并且内部确实有 `.obsidian`。

### `notes_subdir`

Vault 内用于保存本项目笔记的**相对子目录**。默认推荐：

```json
"notes_subdir": "bilibili"
```

资深 Obsidian 用户也可以使用自己的知识库结构，例如：

```json
"notes_subdir": "03-Resources\\Bilibili"
```

`notes_subdir` 不能是绝对路径，也不能包含 `..` 跳出 Vault。

### `cookie_file`

Netscape 格式 Bilibili Cookie 文件路径。当前正常采集流程要求该文件存在。

项目需要的是完整的 Mozilla / Netscape `cookies.txt`，不是单个 `SESSDATA`、JSON 或浏览器请求头。这里只写**文件路径**，不要把 Cookie 内容放进 JSON、日志、Issue 或聊天记录。

默认未显式配置时会检查：

```text
<repo-root>\key\bilibili_cookies.txt
```

也可以放在项目外的私密目录，例如：

```json
"cookie_file": "D:\\Private\\bilibili_cookies.txt"
```

第一次不知道怎样导出、怎样确认 Netscape 格式，或遇到 Windows Chrome `Failed to decrypt with DPAPI` 时，阅读 [Bilibili Cookie 获取与安全配置](BILIBILI-COOKIE.md)。

### `pinned-comment-whitelist.local.json`

`config/pinned-comment-whitelist.local.json` 是**仅限本机的私有配置**，已被 Git 忽略且不会进入 Skill ZIP。它用于让用户主动列出“即使简介/字幕未明确指向评论区，也允许额外检查一次 UP 主置顶一级评论”的 UP 主身份。仓库只跟踪空白的 `config/pinned-comment-whitelist.example.json`，不预置任何具体 UP 主。

如确有需要，先复制模板，再仅在本机填写你认可的公开 UID；优先使用稳定 UID，名称只作为兼容匹配：

```powershell
Copy-Item .\config\pinned-comment-whitelist.example.json .\config\pinned-comment-whitelist.local.json
```

未创建本地文件时，白名单路径完全关闭。普通视频仍只在当前来源明确提示评论区资源时执行一次匿名只读查询；本地白名单命中时才允许使用项目现有 Netscape Cookie 做且只做一次只读查询。两种路径都不翻页、不抓普通评论/楼中楼、不重试，失败或无置顶评论不阻塞笔记生成。

### `workflow_mode`

控制 Agent 的写作流程：

- `light`：当前默认模式。完整读字幕后直接写笔记，内容完成再做一次排版优化；不创建 Fact Ledger、Semantic Draft 或 Layout Plan。
- `strict`：保留此前的分阶段严格流程，用于需要可审计中间文件和阶段门禁的任务。

推荐先使用：

```json
"workflow_mode": "light"
```

也可以临时通过环境变量 `BILI_LEARNING_WORKFLOW_MODE=strict` 切换，而不修改本机 JSON。

---

## 2. 第一次初始化

Agent 首次生成笔记前应先运行统一 onboarding，而不是直接启动采集：

```powershell
python .\scripts\run_bili_learning.py onboarding
```

它只把**用户需要处理的首次配置**放进 `actions`：Vault、Cookie、yt-dlp 与 Python 环境；CSS 缺失放进 `warnings`，不阻塞 Markdown 笔记生成。完整项目诊断仍由 `doctor` 负责。

可写入本机配置的统一入口包括：

```powershell
# Obsidian Vault；notes_subdir 默认 bilibili
python .\scripts\run_bili_learning.py configure-obsidian --vault 'D:\Notes\MyVault'

# Netscape Cookie 文件路径；不要把 Cookie 内容传给 Agent
python .\scripts\run_bili_learning.py configure-cookie --file 'D:\Private\bilibili_cookies.txt'

```

### 第一次绑定 Vault

统一 Vault 配置入口：

```powershell
python .\scripts\run_bili_learning.py configure-obsidian --vault 'D:\Notes\MyVault' --notes-subdir 'bilibili'
```

该命令由 Agent 调用。全新配置时自动设置 `notes_root = notes/bilibili`，使用 Hybrid 模式；已有 `notes_root` 的位置不变；已有 direct-vault 配置也不会被静默迁移。旧 `ytdlp` 字段仅作为兼容数据保留，实际调用始终使用项目内 EXE。

Agent 推荐执行顺序：

1. 运行 `configure-obsidian` 写入本机配置；全新安装会自动使用项目内 `notes/bilibili`；
2. 核对 Vault 和项目 notes 的实际绝对路径，在获得目标目录写入授权后，使用 `scripts/ensure_junction.ps1` 先计划、再 `-Apply` 创建 Vault → 项目 notes 的 Junction；
3. 若 Vault 已有真实目录或笔记，立即停止，不覆盖或移动；
4. 重新运行 onboarding，确认 `obsidian_notes_mapping = OK`。

---

## 3. 推荐的数据拓扑：项目内真实存储 + Vault Junction

推荐正式配置同时保留三项：

```json
{
  "notes_root": "notes/bilibili",
  "vault_root": "D:\\Notes\\MyVault",
  "notes_subdir": "bilibili"
}
```

语义分别是：

- `notes_root`：真实 Markdown 文件所在位置；推荐在项目内并保持 Git ignored；
- `vault_root + notes_subdir`：Obsidian 中用户看到的逻辑位置；
- Windows 上推荐让 `<vault_root>/<notes_subdir>` 成为 Junction，目标指向 `<repo-root>/notes/bilibili`；
- doctor 会增加 `obsidian_notes_mapping` 检查；映射不正确时 onboarding 返回 `action_required`，避免 Agent 写到错误位置。

**Junction 方向必须是 Vault → 项目 notes。** 不要把项目内的 `notes/bilibili` 反向 Junction 到工作区外，否则 Agent 虽然能看到目录名，但真实路径仍可能超出其授权工作区。

Taxonomy 仍保留 `notes/bilibili` 作为未配置时的 repository fallback；如果没有显式 `notes_root` 或 Vault 配置，它仍会被标记为 fallback 并阻止普通新采集。

---

## 4. 兼容模式

下面两种旧模式仍然支持：

1. 只配置 `vault_root + notes_subdir`：程序直接把 Vault 子目录作为 `notes_root`；
2. 只配置 `notes_root`：程序正常生成笔记，但因为不知道 Vault 根目录，无法可靠检查 CSS。

当前推荐模式允许 `notes_root` 与 `vault_root + notes_subdir` **同时存在**：前者决定真实写入路径，后两者只描述并校验 Obsidian 映射。

---

## 5. 环境变量

高级用户仍可使用环境变量：

| 环境变量 | 用途 |
| --- | --- |
| `BILI_LEARNING_VAULT_ROOT` | Obsidian Vault 根目录 |
| `BILI_LEARNING_NOTES_SUBDIR` | Vault 内笔记相对子目录 |
| `BILI_LEARNING_NOTES_ROOT` | 真实笔记根目录；可与 Vault 元数据组合为 hybrid 模式 |
| `BILI_LEARNING_COOKIE_FILE` | Cookie 文件 |
| `BILI_LEARNING_TAXONOMY` | 自定义 taxonomy 文件 |
| `BILI_LEARNING_WORKFLOW_MODE` | `light` 或 `strict` 写作模式 |
| `SILICONFLOW_API_KEY` | 手动 ASR 旁路的 SiliconFlow Key；优先级高于 `config/local.json` |

推荐的 hybrid 环境变量方式：

```powershell
$env:BILI_LEARNING_NOTES_ROOT = 'notes/bilibili'
$env:BILI_LEARNING_VAULT_ROOT = 'D:\Notes\MyVault'
$env:BILI_LEARNING_NOTES_SUBDIR = 'bilibili'
```

环境变量也支持同一混合模型：`BILI_LEARNING_NOTES_ROOT` 可以与 `BILI_LEARNING_VAULT_ROOT` / `BILI_LEARNING_NOTES_SUBDIR` 同时使用；此时前者决定真实写入位置，后两者用于 Vault / Junction 校验。单独设置 `BILI_LEARNING_NOTES_SUBDIR` 仍然无效，必须同时提供 Vault 根目录。旧的 `BILI_LEARNING_YTDLP` 环境变量已不参与运行时解析。

---

## 6. 路径解析优先级

笔记位置按以下顺序解析：

```text
1. BILI_LEARNING_NOTES_ROOT + 可选 Vault 映射元数据
   否则 BILI_LEARNING_VAULT_ROOT + BILI_LEARNING_NOTES_SUBDIR 直接写 Vault
2. config/local.json 的 notes_root + 可选 vault_root / notes_subdir
   否则 vault_root + notes_subdir 直接写 Vault
3. taxonomy 的 notes/bilibili fallback
```

当 `notes_root` 与 Vault 元数据同时存在时，`notes_root` 是物理存储真源，Vault 只用于 Obsidian/CSS/Junction 校验。

`yt-dlp` 没有路径搜索优先级：始终固定为 `<repo-root>/tools/yt-dlp.exe`，环境变量与旧配置覆盖不生效。

---

## 7. Doctor 会检查什么

运行：

```powershell
python .\scripts\run_bili_learning.py doctor
```

结构化输出：

```powershell
python .\scripts\run_bili_learning.py doctor --json
```

重点检查：

- Python 版本；
- 项目根和 taxonomy；
- 当前笔记位置是否仍是未配置的 repository fallback；
- `vault_root` 是否真正包含 `.obsidian`；
- hybrid 模式下 `<vault_root>/<notes_subdir>` 是否与 `notes_root` 解析到同一位置（`obsidian_notes_mapping`）；
- `learning-lab.css` 是否存在；
- `video-note.css` 是否存在；
- notes/runtime 是否可写；
- yt-dlp 是否存在、可执行以及最终来源；
- Cookie 文件是否存在；
- 共享协议是否存在。

CSS 缺失和 repository fallback 使用 `WARN`；它们不会伪装成硬故障，但会明确告诉用户当前配置还不完整。真正无法运行的依赖仍使用 `FAIL`。

Doctor 不访问 Bilibili，也不读取 Cookie 内容。

---

## 8. CSS 为什么要知道 Vault 根

本项目的样式依赖由 `config/obsidian-style.json` 声明；CSS 唯一真源是 <https://github.com/ZiYao00/obsidian-learning-snippets>。本项目需要 `learning-lab.css` 与 `video-note.css`，但不在仓库内维护副本。

它们应该安装到：

```text
<vault_root>/.obsidian/snippets/
```

而不是：

```text
<notes_root>/.obsidian/snippets/
```

程序只负责诊断 Vault 中 CSS 是否存在，**不会静默覆盖**用户已经修改过的 CSS。具体安装、启用和升级方式见 [Obsidian 样式教程](OBSIDIAN-STYLING.md)。

---

## 9. 支持的 `local.json` 字段

当前支持：

```text
notes_root
vault_root
notes_subdir
cookie_file
taxonomy
workflow_mode
local_asr_base_url
siliconflow (历史可选字段)
ytdlp (旧配置兼容字段，忽略)
```

推荐新配置：

```json
{
  "notes_root": "notes/bilibili",
  "vault_root": "D:\\Notes\\MyVault",
  "notes_subdir": "bilibili",
  "cookie_file": "key/bilibili_cookies.txt",
  "workflow_mode": "light"
}
```

本机配置出现未知字段、空路径、孤立的 `notes_subdir` 或非法相对路径时会直接停止。`notes_root` 与 Vault 元数据可以同时存在，但 hybrid 模式的 Junction 映射必须由 onboarding 验证通过。

---

## 10. 笔记命名与归档

新笔记仍统一先进入：

```text
<notes_root>/00-待整理/
```

文件名默认使用原视频标题；同名时自动生成 `（2）`、`（3）`，不覆盖旧笔记。

只有用户明确执行“学习后整理”时，系统才根据 tags / taxonomy 移入建议分类并刷新导航。
