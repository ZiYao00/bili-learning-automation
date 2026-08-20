# 配置说明

## taxonomy

默认文件：`config/bilibili-note-taxonomy.json`。

`version` 当前只支持 `1`。程序启动时会校验 `notes_root`、`navigation_dir`、fallback、models、routes、route id 和 pattern 字段；配置无效时应立即失败，不继续写笔记。

`notes_root` 是默认笔记根目录，也是 collector、判重、finalizer 和 navigation 共用的配置来源。相对路径以项目根目录为基准。

## 环境变量

- `BILI_LEARNING_TAXONOMY`：覆盖 taxonomy 文件。
- `BILI_LEARNING_NOTES_ROOT`：覆盖笔记根目录。
- `BILI_LEARNING_YTDLP`：覆盖 yt-dlp 可执行文件。
- `BILI_LEARNING_COOKIE_FILE`：覆盖 Netscape Cookie 文件。

环境变量只用于机器差异，不要把 Cookie 内容写进配置。

## 新机器配置

默认 `notes_root` 为项目内 `notes/bilibili`。可直接创建这个目录，或通过 `BILI_LEARNING_NOTES_ROOT` 指向已有 Obsidian Vault，例如：

```powershell
$env:BILI_LEARNING_NOTES_ROOT = 'D:\YourObsidianVault\bilibili'
```

不要把个人盘符、目录链接目标或 Cookie 路径写回仓库。yt-dlp 必须通过 `BILI_LEARNING_YTDLP` 或 PATH 配置。

## yt-dlp 查找顺序

1. `BILI_LEARNING_YTDLP`
2. PATH 中的 `yt-dlp`

新环境必须使用其中一种方式。

## 笔记命名

目标文件名固定为：

```text
{canonical_title}__{bvid}.md
```

H1 只使用 `canonical_title`。旧笔记不自动批量改名。
