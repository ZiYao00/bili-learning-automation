# 配置说明

普通用户优先让 Agent 通过 onboarding 检查并补齐缺失配置；这些本机值最终保存到 `config/local.json`。它用于保存当前电脑的本地路径与私密配置，并已被 Git 忽略；公开仓库只提交 `config/local.json.example`。高级用户也可以直接手工维护这个文件。

新版本把 Obsidian 配置拆成两个概念：

```text
vault_root     = Obsidian Vault 根目录（直接包含 .obsidian）
notes_subdir   = 本项目在 Vault 内使用的相对子目录
notes_root     = vault_root / notes_subdir（程序计算结果）
```

这样程序既知道笔记应该写到哪里，也知道 CSS 应该检查哪个 `.obsidian/snippets/`。

---

## 1. 推荐配置

项目模板：

```text
config/local.json.example
```

复制后修改为自己的路径：

```json
{
  "vault_root": "D:\\Notes\\MyVault",
  "notes_subdir": "bilibili",
  "cookie_file": "D:\\Private\\bilibili_cookies.txt",
  "workflow_mode": "light"
}
```

最终笔记会写到：

```text
D:\Notes\MyVault\bilibili\00-待整理\
```

CSS 则应该位于：

```text
D:\Notes\MyVault\.obsidian\snippets\
```

### `ytdlp`（可选覆盖）

普通用户**不需要**预先填写 `ytdlp`。程序会先检查 `BILI_LEARNING_YTDLP`、再检查 `config/local.json` 的自定义覆盖，最后自动查找系统 PATH 中的 `yt-dlp`。

项目不会内置 `yt-dlp.exe`，也不会自动下载安装。首次 doctor 如果没有检测到 yt-dlp，会给出 Windows 推荐命令：

```powershell
winget install yt-dlp
```

安装后重新运行 doctor 即可。只有 yt-dlp 位于自定义目录且没有加入 PATH 时，才建议配置例如：

```json
"ytdlp": "D:\\Tools\\yt-dlp.exe"
```

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

### `pinned-comment-whitelist.json`

`config/pinned-comment-whitelist.json` 是**可提交的公开项目配置**，用于列出“即使简介/字幕未明确指向评论区，也允许额外检查一次 UP 主置顶一级评论”的公开 UP 主身份。优先使用稳定的 UP UID，名称只作为兼容匹配；不要在这里放 Cookie、账号凭据或私人标识。

普通视频仍只在当前来源明确提示评论区资源时执行一次匿名只读查询；白名单命中时允许使用项目现有 Netscape Cookie 做且只做一次只读查询。两种路径都不翻页、不抓普通评论/楼中楼、不重试，失败或无置顶评论不阻塞笔记生成。

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
python .\hermes-skills\bili-learning-automation\scripts\onboarding_bilibili_learning.py
```

它只把**用户需要处理的首次配置**放进 `actions`：Vault、Cookie、yt-dlp 与 Python 环境；CSS 缺失放进 `warnings`，不阻塞 Markdown 笔记生成。完整项目诊断仍由 `doctor` 负责。

可写入本机配置的统一入口包括：

```powershell
# Obsidian Vault；notes_subdir 默认 bilibili
python .\hermes-skills\bili-learning-automation\scripts\configure_bilibili_learning.py --vault 'D:\Notes\MyVault'

# Netscape Cookie 文件路径；不要把 Cookie 内容传给 Agent
python .\hermes-skills\bili-learning-automation\scripts\configure_cookie_bilibili_learning.py --file 'D:\Private\bilibili_cookies.txt'

# 仅当 yt-dlp 位于自定义目录且未加入 PATH 时使用
python .\hermes-skills\bili-learning-automation\scripts\configure_ytdlp_bilibili_learning.py --path 'D:\Tools\yt-dlp.exe'
```

### 第一次绑定 Vault

除了手工编辑 JSON，也可以使用统一 Vault 配置命令：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\configure_bilibili_learning.py --vault 'D:\Notes\MyVault' --notes-subdir 'bilibili'
```

这个命令会：

- 检查 Vault 目录是否存在；
- 检查该目录下是否有 `.obsidian`；
- 保留 `local.json` 中已有的 yt-dlp、Cookie 等配置；
- 如果存在旧版 `notes_root`，迁移为新的 `vault_root + notes_subdir`；
- 不复制或覆盖 CSS；
- 不访问 Bilibili。

配置成功后会返回：

```json
{
  "status": "configured",
  "vault_root": "D:\\Notes\\MyVault",
  "notes_root": "D:\\Notes\\MyVault\\bilibili"
}
```

Hermes / WorkBuddy / Codex 会在正式采集前通过 onboarding 发现 Vault 缺失，并在 `onboarding_required.actions` 中要求用户提供这个路径，再调用同一配置入口。

---

## 3. 为什么不再默认把笔记写进仓库

Taxonomy 仍保留：

```text
notes/bilibili
```

作为安全 fallback，便于开发、测试和诊断。但它现在被定义为**临时状态**，不是正式用户的长期笔记目录。

如果没有显式配置 Vault 或旧版 `notes_root`：

- doctor 会报告 `notes_repository_fallback`；
- 普通新采集会被 onboarding 门禁拦住并返回 `onboarding_required`；
- yt-dlp 不会启动；
- 不会静默把私人笔记写进代码仓库。

已有 runtime job 的 finalizer / 清理流程不受这个门禁影响，避免升级后把旧任务卡死。

---

## 4. 旧版 `notes_root` 仍然兼容

旧配置：

```json
{
  "notes_root": "D:\\Notes\\MyVault\\bilibili"
}
```

仍可继续使用，程序不会强制破坏现有用户配置。

但旧配置只告诉程序“笔记目录”，没有明确告诉程序 Vault 根在哪里，因此 doctor 无法可靠判断 `.obsidian/snippets/`。

建议有机会时迁移为：

```json
{
  "vault_root": "D:\\Notes\\MyVault",
  "notes_subdir": "bilibili"
}
```

不要同时配置 `notes_root` 和 `vault_root / notes_subdir`。两套配置同时出现时程序会明确报错，避免路径歧义。

---

## 5. 环境变量

高级用户仍可使用环境变量：

| 环境变量 | 用途 |
| --- | --- |
| `BILI_LEARNING_YTDLP` | yt-dlp 可执行文件 |
| `BILI_LEARNING_VAULT_ROOT` | Obsidian Vault 根目录 |
| `BILI_LEARNING_NOTES_SUBDIR` | Vault 内笔记相对子目录 |
| `BILI_LEARNING_NOTES_ROOT` | 旧版兼容：直接指定笔记根目录 |
| `BILI_LEARNING_COOKIE_FILE` | Cookie 文件 |
| `BILI_LEARNING_TAXONOMY` | 自定义 taxonomy 文件 |
| `BILI_LEARNING_WORKFLOW_MODE` | `light` 或 `strict` 写作模式 |
| `SILICONFLOW_API_KEY` | 手动 ASR 旁路的 SiliconFlow Key；优先级高于 `config/local.json` |

推荐的新方式：

```powershell
$env:BILI_LEARNING_VAULT_ROOT = 'D:\Notes\MyVault'
$env:BILI_LEARNING_NOTES_SUBDIR = 'bilibili'
```

旧版 `BILI_LEARNING_NOTES_ROOT` 继续兼容，但不能与 `BILI_LEARNING_VAULT_ROOT / BILI_LEARNING_NOTES_SUBDIR` 同时使用。

---

## 6. 路径解析优先级

笔记位置按以下顺序解析：

```text
1. 旧环境变量 BILI_LEARNING_NOTES_ROOT
   或新环境变量 BILI_LEARNING_VAULT_ROOT + BILI_LEARNING_NOTES_SUBDIR
2. config/local.json 的旧 notes_root
   或新 vault_root + notes_subdir
3. taxonomy 的 notes/bilibili fallback
```

环境变量和 `local.json` 内部如果混用新旧两套路径模型，会直接报配置冲突，不做静默猜测。

`yt-dlp` 的顺序是：

```text
BILI_LEARNING_YTDLP
→ local.json 的 ytdlp
→ 系统 PATH
```

---

## 7. Doctor 会检查什么

运行：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

结构化输出：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py --json
```

重点检查：

- Python 版本；
- 项目根和 taxonomy；
- 当前笔记位置是否仍是仓库 fallback；
- `vault_root` 是否真正包含 `.obsidian`；
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
ytdlp
vault_root
notes_subdir
notes_root      # 旧版兼容
cookie_file
taxonomy
workflow_mode
```

推荐新配置：

```json
{
  "vault_root": "D:\\Notes\\MyVault",
  "notes_subdir": "bilibili",
  "cookie_file": "D:\\Private\\bilibili_cookies.txt",
  "workflow_mode": "light"
}
```

本机配置出现未知字段、空路径、新旧笔记路径冲突或非法 `notes_subdir` 时会直接停止，不会尝试“猜一个能跑的值”。

---

## 10. 笔记命名与归档

新笔记仍统一先进入：

```text
<notes_root>/00-待整理/
```

文件名默认使用原视频标题；同名时自动生成 `（2）`、`（3）`，不覆盖旧笔记。

只有用户明确执行“学习后整理”时，系统才根据 tags / taxonomy 移入建议分类并刷新导航。
