# 开发说明

## 环境

项目核心 package 位于 `src/bili_learning`，Hermes 下的三个正式脚本保留为兼容入口。

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

`.venv` 是项目本机的开发/测试环境，已被 Git 忽略；不要向 Hermes 的运行环境、全局 Python 或仓库提交任何依赖目录。普通 Hermes 使用者不需要安装 `pytest` 或 `ruff`。

## 本地验证

```powershell
python -m compileall -q src hermes-skills/bilibili-learning/scripts
python -m ruff check .
python -m pytest -q
```

测试不得依赖真实 Cookie、真实 Bilibili 登录态或私人 Obsidian 笔记。

## 设计原则

- 确定性数据由 Python 生成，不让 LLM 重写元数据。
- taxonomy 是分类和 notes root 的配置源。
- 每次成功转换生成一篇笔记；同名文件使用序号防覆盖，BVID 不作为文件级唯一性约束。
- 公开 CI 不访问真实 Bilibili 账号。
- Cookie 只能作为 yt-dlp 的本地文件参数使用，不能读取内容。
- cleanup 只能作用于 `.runtime/bilibili-learning` 下的 job。

## 兼容入口

- `prepare_ytdlp_bilibili_note.py`
- `finalize_ytdlp_bilibili_note.py`
- `build_bilibili_navigation.py`
- `doctor_bilibili_learning.py`

不要在没有迁移 Hermes 调用方的情况下删除或改名这些入口。

## Obsidian 样式维护

仓库内提交可直接安装的样式副本：

```text
obsidian/snippets/
├── learning-lab.css
└── video-note.css
```

当前版本与 `ComfyUI-Learning-Lab` Design System v0.3 / Video Note v0.1 对齐，但本项目运行和安装不能依赖另一个本地仓库。后续如果从 Learning Lab 同步新版 CSS，应把两个文件视为一组进行复核，避免 Core 与 Extension 版本错配。

同步后至少确认：

- `video-note.css` 声明的 Core 版本与 `learning-lab.css` 一致；
- `src/bili_learning/frontmatter.py` 生成的 `learning-page` / `video-note` class 与 CSS 选择器一致；
- README 与 `docs/OBSIDIAN-STYLING.md` 仍指向本仓库的 `obsidian/snippets/`；
- 无 CSS 时 Markdown 仍可正常阅读。

## 提交前验收

准备 commit / push 前，先复核当前 diff，确认没有把 Cookie、`.runtime`、私人笔记、测试抓取材料或本机路径提交进去，然后运行：

```powershell
python -m compileall -q src hermes-skills/bilibili-learning/scripts
python -m ruff check .
python -m pytest -q
git diff --check
```

本轮涉及内容质量与版式升级时，还应确认：

- `obsidian/snippets/learning-lab.css` 与 `obsidian/snippets/video-note.css` 已被 Git 跟踪；
- 新生成笔记含 `learning-page + video-note`；
- Finalizer 仍拒绝未完成 `coverage_review` 或 `source_insufficient` 的任务；
- 示例与文档不再要求固定“怎么做 / 容易踩坑 / 我来实践”四段式；
- README、CHANGELOG、架构说明和 Obsidian 安装教程与实现一致。

## CI

`.github/workflows/ci.yml` 在 Windows / Linux、Python 3.10 / 3.12 上执行 compile、Ruff 和 pytest，不配置 Cookie Secret。
