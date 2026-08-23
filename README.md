# B站视频转笔记

[简体中文](README.md) | [English](README.en.md)

把 Bilibili 视频自动整理成**字幕优先的 Obsidian 学习笔记**。

你只需要发送一个 B站链接或 BV 号，系统会自动获取字幕、UP 主原始简介和元数据，再由智能体提取知识、整理正文、校验并写入 Obsidian。

默认流程**不下载视频或音频**。

## 许可证

本项目采用 [PolyForm Noncommercial 1.0.0](LICENSE)：允许个人学习、研究、测试和兴趣项目等非商业使用，禁止商业用途。详情以许可证原文为准。

> 第一次使用，建议直接从 [新手快速上手](docs/QUICKSTART.md) 开始。

---

## 它能帮你做什么

日常使用可以理解成这一条流程：

```text
发送 B站链接 / BV号
→ 获取字幕、简介、元数据
→ 自动处理长字幕
→ 智能体提取知识
→ 生成“先看结论 + 知识正文”
→ finalizer 校验
→ 写入 Obsidian
```

适合：

- B站教程、课程、技术分享；
- ComfyUI / AI / 编程类长视频；
- 想把“看视频”变成“可搜索、可复习的知识笔记”；
- 手机端把链接发给 Hermes，电脑端自动完成整理。

当前主要支持 **Hermes、WorkBuddy、Codex** 三个入口，核心逻辑共用，不为每个智能体复制一套实现。

---

## 核心特点

- 支持 BV 号、标准 Bilibili 链接、包含 BV 的复制文本和受支持的 `b23.tv` 短链；
- 使用 `yt-dlp --skip-download`，默认不下载音视频；
- 保留 UP 主原始简介和重要资源链接，并识别“三连 / 充电 / 评论关键词 / 私信 / 进群”等明确的附加资料获取条件；资料本体未出现在来源中时不会由智能体自行补写；
- 字幕不足时宁可停止，也不靠模型常识补写事实；
- 长字幕自动生成 transcript manifest 和分块，避免一次把超长 SRT 塞进上下文；
- 极小尾块自动合并，减少无意义的额外 Agent 读取；
- 新笔记先进入 `00-待整理`，学完以后再归档；
- 文件名默认保留原视频标题，同名自动加 `（2）`、`（3）`，不覆盖旧笔记；
- Frontmatter、标题下方元信息、播放器、资料获取提示、tags、cssclasses、路径等确定性内容由程序生成；
- Finalizer 通过后才正式发布，并自动清理 runtime 临时任务；
- Cookie 内容不会进入日志、笔记或 Git。

---

## 第一次使用

如果你是第一次安装，不建议从源码结构开始看。

按下面顺序即可：

1. 下载项目；
2. 准备 Python，配置 Cookie 和 Obsidian 笔记目录；
3. 运行 doctor，让它自动检测 yt-dlp 和其它依赖；
4. 把 CSS 安装到 Obsidian；
5. 安装 Hermes / WorkBuddy 适配层，或者直接使用 Codex；
6. 发送一个 B站链接测试。

完整教程：

**[新手快速上手 →](docs/QUICKSTART.md)**

---

## 日常怎么用

安装完成以后，普通用户通常不需要再碰命令行。

直接在已经接入的智能体里发送：

```text
https://www.bilibili.com/video/BVxxxxxxxxxx/
```

或者：

```text
BVxxxxxxxxxx
```

正常情况下，智能体会自己完成采集、长字幕处理、知识整理、覆盖复核和 finalizer。

如果使用 Hermes，当前设计用于 owner 私聊场景；WorkBuddy 和 Codex 复用同一套核心协议。

---

## 长视频怎么处理

长视频不需要用户手工拆字幕。

任务创建时程序会自动生成：

```text
.runtime/bilibili-learning/<job>/agent-work/
├── transcript-manifest.json
└── transcript/
    ├── transcript-01.txt
    ├── transcript-02.txt
    └── ...
```

短字幕通常是一个 `direct` chunk；长字幕是 `chunked`。切块保持原字幕文字顺序和 cue 边界，不做语义删减、摘要或关键词过滤。

Hermes / WorkBuddy / Codex 只负责读取已经准备好的 transcript，再完成知识判断和写作。

---

## 生成的笔记在哪里

新笔记先进入：

```text
<notes_root>/00-待整理/
```

例如：

```text
00-待整理/
└── H3智能一体化节点重磅升级.md
```

笔记主要阅读顺序：

```text
标题 / 作者 · 日期 · 时长 · BV号
→ 先看结论
→ 播放器与来源区（资料获取 / UP 主资源 / 视频简介 / 原文折叠）
→ 知识正文
```

播放器与来源区不再显示额外标题：播放器直接位于“先看结论”之后，UP 主资源以逐条链接列表展示，视频简介保持紧凑，UP 主原文（完整说明与链接）继续折叠留档。知识密集型视频会先建立原子事实清单，再形成正文，并在完成前重新回看原 transcript，减少参数、成员关系和例外条件被二次压缩。

项目自带 Obsidian 样式：

```text
obsidian/snippets/
├── learning-lab.css
└── video-note.css
```

安装教程见 [Obsidian 视觉样式](docs/OBSIDIAN-STYLING.md)。

---

## 学完以后再整理

“转成笔记”和“知识归档”是两个阶段。

刚生成的笔记先留在 `00-待整理`。当你确认已经学习完，可以让智能体执行“学习后整理”，统一完成：

- 短标题；
- 一句简介摘要；
- taxonomy 建议分类；
- 文件安全移动；
- 导航刷新。

这样可以避免把“还没看过的资料”直接伪装成已经整理好的知识库。

---

## 三种智能体入口

| 入口 | 适合谁 | 说明 |
| --- | --- | --- |
| Hermes | 想在微信里直接发链接的人 | `hermes-skills/bili-learning-automation/` |
| WorkBuddy | 在 WorkBuddy 会话里使用 | `workbuddy-skills/bili-learning-automation/` |
| Codex | 开发、测试、维护项目 | 读取 `AGENTS.md` 和 `docs/AGENT-INTEGRATION.md` |

这些只是**薄适配层**。核心 collector、transcript、taxonomy、finalizer 和内容标准保持共用。

安装说明：

- [Hermes Skill 安装](docs/HERMES-SKILL-INSTALL.md)
- [WorkBuddy Skill 安装](docs/WORKBUDDY-SKILL-INSTALL.md)

---

## 常见状态

| 状态 | 代表什么 |
| --- | --- |
| `configuration_required` | 尚未显式绑定 Obsidian Vault；本次不会启动采集 |
| `materials_ready` | 字幕、简介等材料已经准备完成 |
| `in_progress` | 同一个 BV 号已经有活动任务，防止并发冲突 |
| `subtitle_unavailable` | 没有取得可用中文字幕 |
| `source_insufficient` | 现有字幕 / 简介不足以写可靠笔记 |
| `note_ready` | Finalizer 校验通过并发布成功 |
| `note_invalid` | 草稿没有通过最终校验 |
| `failed` | 配置、采集或运行失败 |

`in_progress` 不等于“这个视频以后不能再转”。当前 job 结束后，同一个 BV 号仍可再次生成新笔记。

更完整解释见 [新手快速上手](docs/QUICKSTART.md#11-常见状态是什么意思)。

---

## 配置

普通用户推荐使用：

```text
config/local.json
```

示例：

```json
{
  "vault_root": "D:\\Notes\\MyVault",
  "notes_subdir": "bilibili",
  "cookie_file": "D:\\Private\\bilibili_cookies.txt"
}
```

`vault_root` 是直接包含 `.obsidian` 的 Vault 根目录，`notes_subdir` 是本项目在 Vault 内使用的相对子目录。未显式配置笔记位置时，仓库内 `notes/bilibili` 只作为临时 fallback；新采集会返回 `configuration_required`，不会静默把私人笔记写进代码仓库。

`yt-dlp` 默认不需要写进配置：程序会自动检查环境变量、本机 `local.json` 覆盖和系统 PATH。首次检查如果未检测到 yt-dlp，只会给出安装指引，不会自动安装，也不会在 Skill / 仓库中内置 `yt-dlp.exe`。Windows 推荐按官方说明运行 `winget install yt-dlp`；如果你把 yt-dlp 放在自定义位置，再单独配置 `ytdlp` 即可。

也支持环境变量：

- `BILI_LEARNING_TAXONOMY`
- `BILI_LEARNING_VAULT_ROOT`
- `BILI_LEARNING_NOTES_SUBDIR`
- `BILI_LEARNING_NOTES_ROOT`（旧版兼容）
- `BILI_LEARNING_YTDLP`
- `BILI_LEARNING_COOKIE_FILE`

详见 [配置说明](docs/CONFIGURATION.md)。

---

## 出问题先运行 doctor

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

结构化输出：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py --json
```

doctor 会检查 yt-dlp、Cookie 文件、taxonomy、Vault/CSS、notes/runtime 写权限和关键文档，不读取 Cookie 内容，也不访问 Bilibili。若未检测到 yt-dlp，只提供官方安装指引，不会自动安装。

常见错误见 [故障排查](docs/TROUBLESHOOTING.md)。

---

## 文档导航

| 文档 | 适合什么时候看 |
| --- | --- |
| [新手快速上手](docs/QUICKSTART.md) | 第一次安装、第一次生成笔记 |
| [配置说明](docs/CONFIGURATION.md) | 换电脑、换 Vault、改 yt-dlp / Cookie 路径 |
| [Hermes Skill 安装](docs/HERMES-SKILL-INSTALL.md) | 安装、更新、验证 Hermes Skill |
| [WorkBuddy Skill 安装](docs/WORKBUDDY-SKILL-INSTALL.md) | 安装、更新、验证 WorkBuddy 适配层 |
| [Obsidian 视觉样式](docs/OBSIDIAN-STYLING.md) | 安装 CSS、样式不生效 |
| [故障排查](docs/TROUBLESHOOTING.md) | 看到错误状态或任务卡住 |
| [智能体接入协议](docs/AGENT-INTEGRATION.md) | 接入新 Agent / 维护适配层 |
| [架构说明](docs/ARCHITECTURE.md) | 想了解内部流程 |
| [开发说明](docs/DEVELOPMENT.md) | 修改代码、跑测试、维护 CI |
| [v1.0 发布清单](docs/RELEASE-CHECKLIST.md) | Feature Freeze、clean-room 验收与正式 Release 前检查 |

---

## 数据与隐私

长期数据主要是正式 Markdown 笔记和导航。

临时任务位于：

```text
.runtime/bilibili-learning/
```

敏感凭据默认位于：

```text
key/
```

以下内容默认不进入 Git：

- Cookie；
- 私人笔记；
- runtime 临时任务；
- 本机 `config/local.json`；
- 虚拟环境和测试缓存。

不要手工删除正在工作的 job、reservation 或锁文件，也不要绕过 finalizer 直接发布 runtime 草稿。

---

## 开发与测试

开发环境：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
```

公共测试不需要真实 Cookie，也不应访问真实 Bilibili 账号。

---

## Legacy

`hermes-skills/bili-learning-automation/scripts/prepare_bilibili_learning.py` 属于旧 Chrome/CDP / `bili-note` / `web-access` 路线，不是当前默认入口。

新接入统一使用 yt-dlp 字幕优先流程。详见 [Legacy 说明](docs/LEGACY.md)。

---

## 许可证

本项目采用 [PolyForm Noncommercial 1.0.0](LICENSE)。允许个人学习、研究、测试和兴趣项目等非商业使用；商业使用不在该许可证授权范围内。第三方依赖继续遵循各自许可证。
