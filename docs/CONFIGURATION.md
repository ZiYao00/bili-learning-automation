# 配置说明

## taxonomy

默认文件：`config/bilibili-note-taxonomy.json`。

`version` 当前只支持 `1`。程序启动时会校验 `notes_root`、`navigation_dir`、fallback、models、routes、route id、title 和 pattern 字段；配置无效时应立即失败，不继续写笔记。

每个 route 的 `path` 是**学习后整理的建议位置**，不是新笔记的自动发布位置。新笔记一律先发布到 fallback 的 `path`（默认 `00-待整理`）；route 的 `tags` 用于收集阶段标注，并让 `organize` 默认推断建议目录。`title` 仅是分类配置的说明，不改写收集阶段的原视频标题。

`notes_root` 是默认笔记根目录，也是 collector、判重、finalizer 和 navigation 共用的配置来源。相对路径以项目根目录为基准。

## 环境变量

- `BILI_LEARNING_TAXONOMY`：覆盖 taxonomy 文件。
- `BILI_LEARNING_NOTES_ROOT`：覆盖笔记根目录。
- `BILI_LEARNING_YTDLP`：覆盖 yt-dlp 可执行文件。
- `BILI_LEARNING_COOKIE_FILE`：覆盖 Netscape Cookie 文件。

环境变量只用于机器差异，不要把 Cookie 内容写进配置。

## 本机持久配置

可复制 `config/local.json.example` 为 `config/local.json`，再填写本机路径。`config/local.json` 已被 Git 忽略，适合保存 yt-dlp、笔记目录和 Cookie 文件的**路径**；不得写入 Cookie 内容。

```json
{
  "ytdlp": "C:\\Tools\\yt-dlp.exe",
  "notes_root": "D:\\YourObsidianVault\\bilibili",
  "cookie_file": "C:\\PrivateConfig\\bilibili_cookies.txt"
}
```

支持字段只有 `ytdlp`、`notes_root`、`cookie_file` 和 `taxonomy`。文件不是有效 JSON、字段未知或值为空时，启动会以稳定配置错误停止，不会静默回退。

每项路径的优先级为：对应环境变量 → `config/local.json` → 项目默认值；yt-dlp 的第三层为系统 PATH。这样升级公开代码时，本机依赖可保留在 Git 忽略的配置中。

## 新机器配置

默认 `notes_root` 为项目内 `notes/bilibili`。可直接创建这个目录，或通过 `BILI_LEARNING_NOTES_ROOT` 指向已有 Obsidian Vault，例如：

```powershell
$env:BILI_LEARNING_NOTES_ROOT = 'D:\YourObsidianVault\bilibili'
```

不要把个人盘符、目录链接目标或 Cookie 路径写回仓库。yt-dlp 必须通过 `BILI_LEARNING_YTDLP` 或 PATH 配置。

## yt-dlp 查找顺序

1. `BILI_LEARNING_YTDLP`
2. `config/local.json` 的 `ytdlp`
3. PATH 中的 `yt-dlp`

新环境必须使用其中一种方式。doctor 会显示最终来源、已检查来源、可执行性和版本。

## 诊断

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py --json
```

doctor 不访问 Bilibili、不读取 Cookie 内容，也不保留测试文件；它会在 notes/runtime 的可写位置创建并立即删除空探针，以确认该位置实际可写。

`--json` 输出稳定的 `schema_version`、总状态和每项 check 的 `status`、`code`、`label`、`detail`。yt-dlp 成功项包含 `source`、`version` 和 `checked_sources`；失败项使用稳定 code，例如 `ytdlp_not_configured`、`ytdlp_path_invalid`、`ytdlp_not_executable`。

## 笔记命名

默认目标文件名为：

```text
{原视频标题}.md
```

H1 默认使用原视频标题，BVID 固定写在 H1 与视频简介之间的 `<small>` 行。若同目录已有相同标题，文件名自动变为 `{原视频标题}（2）.md`，不会覆盖既有笔记。旧笔记不自动批量改名。

用户明确要求学习后整理时，使用 `bili-learning organize --note ... --title ... --intro ...` 将短标题、简介摘要和归档目录合并为一次安全操作。
