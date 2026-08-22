# Obsidian 视觉样式

本项目自带视频学习笔记需要的两份 CSS，不依赖其他仓库：

```text
bili-learning-automation/
└── obsidian/
    └── snippets/
        ├── learning-lab.css
        └── video-note.css
```

- `learning-lab.css`：Core Design System，负责阅读宽度、标题层级、Callout、Grid、Card、Badge、Chip、Table 和响应式布局。
- `video-note.css`：Video Note Extension，依赖 Core，只处理长视频标题、Bilibili 播放器、来源附录等视频笔记特有样式。

## 先分清两个目录

新版推荐配置：

```json
{
  "vault_root": "D:\\Notes\\MyVault",
  "notes_subdir": "bilibili"
}
```

它们对应：

```text
Vault 根目录
D:\Notes\MyVault
├── .obsidian\
│   └── snippets\        ← CSS 放这里
└── bilibili\             ← 本项目笔记放这里
    └── 00-待整理\
```

因此记住一条规则即可：

> CSS 始终安装到 `<vault_root>\.obsidian\snippets\`，不是 `<notes_root>\.obsidian\snippets\`。

旧版 `notes_root` / `BILI_LEARNING_NOTES_ROOT` 继续兼容，但它只告诉程序“笔记在哪”，不能可靠告诉程序“Vault 根在哪”。这种情况下 doctor 会提示 `obsidian_vault_unknown`，CSS 路径需要用户自己确认。

## 第一次安装 CSS

### 1. 确认 Vault 根目录

Vault 根目录就是直接包含 `.obsidian` 的文件夹。例如：

```text
D:\Notes\MyVault\
├── .obsidian\
├── bilibili\
└── 其它笔记\
```

Windows 默认可能隐藏 `.obsidian`。看不到时可在资源管理器开启“显示隐藏的项目”。

### 2. 打开或创建 snippets 目录

目标目录：

```text
D:\Notes\MyVault\.obsidian\snippets\
```

如果 `.obsidian\snippets\` 不存在，可以手动创建 `snippets` 文件夹。

### 3. 复制两份 CSS

从仓库：

```text
obsidian\snippets\
├── learning-lab.css
└── video-note.css
```

复制到：

```text
你的 Vault\.obsidian\snippets\
├── learning-lab.css
└── video-note.css
```

两个文件都需要保留。`video-note.css` 依赖 `learning-lab.css`。

### 4. 在 Obsidian 启用

打开：

```text
设置 → 外观 → CSS 代码片段
```

然后：

1. 点击刷新 / 重新载入代码片段；
2. 启用 `learning-lab`；
3. 启用 `video-note`。

## Doctor 可以帮你检查什么

运行：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

在已经配置 `vault_root` 时，doctor 会检查：

```text
Obsidian Vault
learning-lab.css
video-note.css
```

相关代码：

```text
obsidian_vault_detected
obsidian_snippet_learning_lab
obsidian_snippet_video_note
```

CSS 不存在时是 `WARN`，不会影响 Markdown 的基本可读性。

程序**不会静默复制或覆盖 CSS**。原因是用户可能已经自行修改 CSS，或者多个项目正在共享同一份设计系统。需要升级时由用户明确决定是否覆盖。

## 不需要手工修改 Frontmatter

新生成的视频学习笔记由程序自动写入：

```yaml
cssclasses:
  - learning-page
  - video-note
```

`learning-page` 启用 Core，`video-note` 启用视频扩展。Codex、Hermes、WorkBuddy 和用户都不需要为了样式手工添加这两个 class。

正式阅读顺序是：

```text
标题 / BVID
→ 先看结论
→ Bilibili 播放器
→ 动态知识正文
→ 视频资料
   ├── 视频简介
   ├── UP 主资源
   └── UP 主原始简介（折叠）
```

Agent 会根据知识关系选择 Table / Grid / Card / Chip / Risk / Resource 等语义组件；具体规则见 `docs/standards/CODEX-VIDEO-NOTE-GUIDE.md`。

## 更新项目后如何同步 CSS

以后 `git pull` 或升级本项目后，如果 `obsidian/snippets/` 中的 CSS 有更新：

1. 先确认自己是否修改过 Vault 中的 CSS；
2. 需要升级时同时更新 `learning-lab.css` 和 `video-note.css`；
3. 回到 Obsidian“CSS 代码片段”页面刷新。

不要只替换其中一个版本，也不要让自动化在未确认的情况下覆盖用户版本。

## 样式没有生效时

优先检查：

- 当前打开的笔记是否属于配置的 `vault_root`；
- 两个文件是否真的位于 `<vault_root>/.obsidian/snippets/`；
- Obsidian“设置 → 外观 → CSS 代码片段”里是否同时启用了 `learning-lab` 与 `video-note`；
- 笔记 Frontmatter 是否包含 `learning-page` 与 `video-note`；
- 更新 CSS 后是否点击了刷新，必要时关闭再重新启用代码片段。

即使 CSS 没有安装或没有启用，Markdown、Callout、表格、链接和正文仍应保持基本可读；CSS 只负责视觉表现，不承载知识内容。

## 维护约定

本仓库提交可直接使用的 CSS 副本，确保项目能够独立安装和使用。维护设计系统时应同时检查：

- `learning-lab.css` Core 与 `video-note.css` Extension 的版本依赖是否匹配；
- 本项目生成的 `cssclasses` 是否仍与选择器一致；
- `docs/OBSIDIAN-STYLING.md`、`docs/QUICKSTART.md` 与 README 的安装路径是否仍准确；
- 真实视频笔记在浅色 / 深色和窄分栏下是否仍可读。
