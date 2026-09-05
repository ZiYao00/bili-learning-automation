# 开发说明

## 环境

项目核心 package 位于 `src/bili_learning`。ChatGPT 与 Codex 通过共享启动器调用核心 CLI；Hermes / WorkBuddy 的宿主脚本保留为兼容入口。

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

`.venv` 是项目本机的开发/测试环境，已被 Git 忽略；不要向 Hermes 的运行环境、全局 Python 或仓库提交任何依赖目录。普通 Hermes 使用者不需要安装 `pytest` 或 `ruff`。

## 本地验证

```powershell
python -m compileall -q src scripts hermes-skills/bili-learning-automation/scripts workbuddy-skills/bili-learning-automation/scripts
python -m ruff check .
python -m pytest -q
python .\scripts\build_agent_skill_packages.py
python .\scripts\build_agent_skill_packages.py --check
```

测试不得依赖真实 Cookie、真实 Bilibili 登录态或私人 Obsidian 笔记。

## 设计原则

- 确定性数据由 Python 生成，不让 LLM 重写元数据。
- Skill 只人工维护 `skill/bili-learning-automation/SKILL.md`；所有宿主 `SKILL.md` 都由 `scripts/build_agent_skill_packages.py` 生成。改 Skill 时先改真源，再运行构建脚本；禁止在生成出口直接打补丁。
- `subtitle_srt`、`asr_text`、`description_only` 只在 SourceMaterial 层分流；三个外部入口必须共用 `_prepare_materials`、Job、handoff、finalizer、恢复与 retire，不为新来源复制 lifecycle。
- taxonomy 是分类规则与 repository fallback 的配置源；正式 Obsidian 笔记位置优先使用本机 `vault_root + notes_subdir`，旧 `notes_root` 仅用于兼容。
- 相同 BVID 默认先返回 `existing_note_found`，由用户选择 update / rerun / cancel；只有明确 rerun 才创建同标题序号笔记，update 保留原路径并使用 SHA-256 冲突保护。
- 公开 CI 不访问真实 Bilibili 账号。
- Cookie 是本地凭据：正常采集只把文件路径交给 yt-dlp；命中置顶评论白名单时，核心可以在本机读取 Netscape Cookie 构造一次只读请求，但不得把值暴露给 Agent、日志、Job、笔记或 Git。
- cleanup 只能作用于 `.runtime/bilibili-learning` 下的 job。

## 兼容入口

- `prepare_ytdlp_bilibili_note.py`
- `prepare_transcript_bilibili_note.py`
- `prepare_description_bilibili_note.py`
- `finalize_ytdlp_bilibili_note.py`
- `build_bilibili_navigation.py`
- `doctor_bilibili_learning.py`
- `configure_bilibili_learning.py`

ChatGPT 与 Codex 使用共享 `scripts/run_bili_learning.py`。不要在没有迁移调用方的情况下删除或改名共享启动器或上述 Hermes 兼容入口。

## Obsidian 样式维护

共享 CSS 的唯一真源为 <https://github.com/ZiYao00/obsidian-learning-snippets>；本项目的依赖声明在 `config/obsidian-style.json`。本项目不保留 `learning-lab.css` / `video-note.css` 副本，也不建立指向共享仓库的项目级 junction。升级共享 CSS 时，在共享仓库中把 Core 与 Extension 视为一组复核，再同步到 Vault，避免版本错配。

同步后至少确认：

- `video-note.css` 声明的 Core 版本与 `learning-lab.css` 一致；
- `src/bili_learning/frontmatter.py` 生成的 `learning-page` / `video-note` class 与 CSS 选择器一致；
- README 与 `docs/OBSIDIAN-STYLING.md` 仍指向共享仓库和 `config/obsidian-style.json`；
- 无 CSS 时 Markdown 仍可正常阅读。

## 内容质量 Benchmark

修改写作标准或更换推荐模型时，不再用笔记字数、KB 大小、章节数量或压缩比判断质量。固定使用同一批高信息密度视频做横向回归，并至少记录：Skill / 仓库版本、Agent 宿主、实际底层模型、思考档位、BVID 与输出文件。

Benchmark 重点比较：

- 重大知识模块是否完整；
- 对象之间的来源、兼容、互斥、选择和因果关系是否保留；
- 参数、专有名词、版本、数字与单位是否忠于来源；
- 实测是否保留条件、耗时、结果、失败表现和作者判断；
- 来源自身存在冲突或字幕不确定时，是否明确保留不确定性而不是猜测；
- 排版是否服务于理解，而不是通过再次摘要来缩短正文。

不同模型测试时，生成模型不得读取同一 BVID 的其它模型成品笔记，避免历史结果污染。动态代理必须记录实际底层模型；无法确认底层模型时，测试结果只能归因于该代理链路，不能作为单一模型结论。

项目不指定默认或必选 LLM。不同模型共用同一套 `light` 标准和最终笔记结构，不为单独模型维护第二套 Markdown 模板。模型实测结果只用于说明“最终笔记质量与模型能力显著相关”，以及帮助使用者结合成本、速度和质量自行选择。

## 提交前验收

准备 commit / push 前，先复核当前 diff，确认没有把 Cookie、`.runtime`、私人笔记、测试抓取材料、本机绝对路径或其它机器特征提交进去；同时确认 Git author / committer 邮箱是维护者愿意公开的地址。然后运行：

```powershell
python -m compileall -q src scripts hermes-skills/bili-learning-automation/scripts workbuddy-skills/bili-learning-automation/scripts
python -m ruff check .
python -m pytest -q
python .\scripts\build_agent_skill_packages.py
python .\scripts\build_agent_skill_packages.py --check
git -c core.whitespace=cr-at-eol diff --check
```

本轮涉及内容质量与版式升级时，还应确认：

- `config/obsidian-style.json` 正确声明 `learning-lab.css` 与 `video-note.css`，且本仓库没有跟踪 CSS 副本；
- 新生成笔记含 `learning-page + video-note`；
- Finalizer 仍拒绝未完成 `coverage_review` 或 `source_insufficient` 的任务；
- 示例与文档不再要求固定“怎么做 / 容易踩坑 / 我来实践”四段式；
- README、CHANGELOG、架构说明和 Obsidian 安装教程与实现一致。

## CI

`.github/workflows/ci.yml` 在 Windows / Linux、Python 3.10 / 3.12 上执行 compile、Ruff、统一 Skill 生成出口 `--check` 和 pytest，不配置 Cookie Secret。
