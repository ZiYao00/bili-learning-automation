# Obsidian 视觉样式

本项目已经自带视频学习笔记所需的两份 CSS，不依赖用户另外下载 `ComfyUI-Learning-Lab`：

```text
bili-learning-automation/
└── obsidian/
    └── snippets/
        ├── learning-lab.css
        └── video-note.css
```

- `learning-lab.css`：Core Design System，负责阅读宽度、标题层级、Callout、Grid、Card、Badge、Chip、Table 和响应式布局。
- `video-note.css`：Video Note Extension，依赖 Core，只处理长视频标题、Bilibili 播放器、来源附录等视频笔记特有样式。

当前仓库中的副本与 `ComfyUI-Learning-Lab` Design System v0.3 / Video Note v0.1 对齐。对普通使用者来说，本仓库内这两份文件就是安装来源，不需要知道另一个项目的目录。

## 第一次使用：把 CSS 安装到 Obsidian

### 1. 找到你的 Vault 根目录

Obsidian 的 Vault 根目录就是包含 `.obsidian` 文件夹的目录。例如：

```text
D:\Notes\MyVault\
├── .obsidian\
├── 00-待整理\
└── 其它笔记\
```

Windows 默认可能隐藏 `.obsidian`。如果看不到，可以在资源管理器开启“显示隐藏的项目”。

> 如果 `BILI_LEARNING_NOTES_ROOT` 指向 Vault 内的某个子目录，例如 `D:\Notes\MyVault\bilibili`，CSS 仍然要安装到 `D:\Notes\MyVault\.obsidian\snippets\`，而不是 `bilibili\.obsidian\`。

> 如果你直接把本项目的 `notes/bilibili` 作为一个独立 Obsidian Vault 打开，那么它自己就是 Vault 根目录，CSS 应放到 `notes/bilibili/.obsidian/snippets/`。

### 2. 打开或创建 snippets 目录

目标目录是：

```text
你的 Vault\.obsidian\snippets\
```

如果 `.obsidian\snippets\` 不存在，可以手动创建 `snippets` 文件夹。

### 3. 从本仓库复制两个文件

从：

```text
bili-learning-automation\obsidian\snippets\
├── learning-lab.css
└── video-note.css
```

复制到：

```text
你的 Vault\.obsidian\snippets\
├── learning-lab.css
└── video-note.css
```

两个文件都需要保留。`video-note.css` 依赖 `learning-lab.css`，只复制扩展文件会导致部分版式失效。

### 4. 在 Obsidian 启用

打开：

```text
设置 → 外观 → CSS 代码片段
```

然后：

1. 点击刷新 / 重新载入代码片段；
2. 启用 `learning-lab`；
3. 启用 `video-note`。

完成后重新打开一篇新生成的视频学习笔记即可看到版式。

## 不需要手工修改笔记 Frontmatter

新生成的视频学习笔记会由程序自动写入：

```yaml
cssclasses:
  - learning-page
  - video-note
```

`learning-page` 启用 Core，`video-note` 启用视频扩展。Codex、Hermes 和用户都不需要为了样式手工添加这两个 class。

最终阅读顺序固定为：

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

以后 `git pull` 或升级本项目后，如果 `obsidian/snippets/` 中的 CSS 有更新，重新把这两个文件复制到 Vault 的 `.obsidian/snippets/` 并覆盖旧版本，然后在 Obsidian 的“CSS 代码片段”页面刷新一次。

建议两个文件一起更新，不要只替换其中一个版本。

## 样式没有生效时

优先检查：

- 当前打开的笔记是否属于你安装 CSS 的那个 Vault；
- 两个文件是否真的位于该 Vault 的 `.obsidian/snippets/`；
- Obsidian“设置 → 外观 → CSS 代码片段”里是否同时启用了 `learning-lab` 与 `video-note`；
- 笔记 Frontmatter 是否包含 `learning-page` 与 `video-note`；
- 更新 CSS 后是否点击了刷新，必要时关闭再重新启用代码片段。

即使 CSS 没有安装或没有启用，Markdown、Callout、表格、链接和正文仍应保持基本可读；CSS 只负责视觉表现，不承载知识内容。

## 维护约定

本仓库提交可直接使用的 CSS 副本，确保项目可以独立安装和使用。设计语言最初来自 `ComfyUI-Learning-Lab`，后续如果两个项目继续共享 Design System，维护者应显式同步版本，而不是让运行时依赖另一个本地仓库。

同步 CSS 时应同时检查：

- `learning-lab.css` Core 与 `video-note.css` Extension 的版本依赖是否匹配；
- 本项目生成的 `cssclasses` 是否仍与选择器一致；
- `docs/OBSIDIAN-STYLING.md` 和 README 的安装路径是否仍准确；
- 真实视频笔记在浅色 / 深色和窄分栏下是否仍可读。
