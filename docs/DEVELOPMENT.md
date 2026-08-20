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
- 一视频一笔记，BVID 负责文件级唯一性。
- 公开 CI 不访问真实 Bilibili 账号。
- Cookie 只能作为 yt-dlp 的本地文件参数使用，不能读取内容。
- cleanup 只能作用于 `.runtime/bilibili-learning` 下的 job。

## 兼容入口

- `prepare_ytdlp_bilibili_note.py`
- `finalize_ytdlp_bilibili_note.py`
- `build_bilibili_navigation.py`
- `doctor_bilibili_learning.py`

不要在没有迁移 Hermes 调用方的情况下删除或改名这些入口。

## CI

`.github/workflows/ci.yml` 在 Windows / Linux、Python 3.10 / 3.12 上执行 compile、Ruff 和 pytest，不配置 Cookie Secret。
