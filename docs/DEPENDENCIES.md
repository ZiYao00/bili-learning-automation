# 依赖说明

## 1. 基础运行依赖（Windows 10/11 x64）

| 项目 | 是否必需 | 约定 |
| --- | --- | --- |
| Python 3.10+ | 是 | 运行 `src/bili_learning` 和统一 CLI；核心无第三方 pip 运行时依赖 |
| `tools/yt-dlp.exe` | 是 | 官方 Windows x64 **单文件 EXE**，固定路径、随项目分发 |
| Bilibili Cookie | 是 | 本机 Netscape `cookies.txt` **文件路径**，不存 Cookie 内容 |
| Obsidian Vault | 是 | 优先 Hybrid：真实笔记在项目内，Vault 用 Junction 指向它 |
| Codex / Hermes / WorkBuddy / 已连接本机的 ChatGPT | 至少一种 | Agent 读取来源和完成内容；ChatGPT Web 需本地工作区桥接 |

项目**不安装 yt-dlp 源码、不在 PATH/环境变量或配置文件中寻找其他 EXE、不执行 winget、不下载或静默更新工具**。所有正常采集和可选 ASR 临时音频下载都使用：

```text
<repo-root>\tools\yt-dlp.exe
```

如缺少或无法执行，doctor/onboarding 报错，Agent 依据官方校验资料恢复项目文件，不自动回退外部 yt-dlp。旧 `config/local.json` 的 `ytdlp` 字段及 `BILI_LEARNING_YTDLP` 环境变量目前被忽略（保留旧配置键解析，避免旧用户直接启动失败）。

## 2. 内置 yt-dlp 的来源和许可证

版本、平台、官方来源及 SHA-256 见 `tools/yt-dlp.release.json`；仓库内 `tools/YT-DLP-LICENSE.txt` 和 `tools/THIRD_PARTY_LICENSES.txt` 是该版本的许可证信息。更新时 Agent 必须从官方稳定版下载单文件 EXE，校验官方 SHA-256，试运行 `--version`，同步更新版本清单及许可证，最后测试。不得把文件换成 Python 包或把其它可执行文件放入搜索链路。

Windows EXE 不能在 Linux 上运行。Linux CI 只检查通用 Python 行为、文件哈希和模拟 yt-dlp 命令，不是 Linux 实际采集能力承诺。

## 3. 可选外部服务：local-ASR-service

`local-ASR-service` 是**独立项目**，不属于本项目初次安装依赖。不复制源码、模型或虚拟环境；不在此项目安装、启动或更新服务。

默认字幕采集不会访问它。只有 `subtitle_unavailable` 后用户明确授权 ASR，Agent 才会：

```text
GET http://127.0.0.1:8001/health
POST http://127.0.0.1:8001/v1/audio/transcriptions
```

未部署则停止 ASR 分支并提示独立安装文档，**不影响字幕优先的普通流程**。本机可用 `local_asr_base_url` 或 `BILI_LEARNING_LOCAL_ASR_BASE_URL` 改地址；外部网络地址应当由用户明确确认数据发送风险。

### 按需安装（仅在用户另外明确授权时）

此步骤**不是 bili-learning-automation 的首次安装步骤**。在用户决定启用 ASR 且独立仓库可访问后，Agent 应单独取得 local-ASR-service 工作区操作权限，并以其 [README](https://github.com/ZiYao00/local-ASR-service) 和 `docs/INSTALL.md` 为准。当前官方项目说明的推荐 Windows CPU 安装顺序是：

1. 检查 **Python 3.11**、FFmpeg、可用磁盘空间和模型下载网络；这些依赖属于 ASR 工程，不装进 bili-learning-automation。
2. 在 **local-ASR-service 仓库根目录**由 Agent 运行 `scripts/install-cpu.ps1` 创建其独立 `.venv-cpu`；无需手动逐项 pip 安装。
3. 经用户同意模型下载后运行 `scripts/start-server.ps1`，再运行 `scripts/health-check.ps1 -WaitSeconds 120`；确认 `status=ok` 且 FFmpeg、VAD、标点恢复全部 ready。
4. 返回 bili-learning-automation 项目，由 Agent 运行 `python scripts/run_bili_learning.py asr-health`；只有服务 ready 且用户再次明确同意本次 ASR 才调用 `prepare-asr`。

若仓库尚未公开或用户无权获取，请向用户说明需要从独立项目取得访问权限，不能臆造下载地址、假装安装完成，也不能把另一套 ASR 源码或模型复制进本项目。

## 4. Agent 安装依赖

Codex、Hermes、WorkBuddy 通过用户级 Junction 使用同一 canonical Skill；`scripts/install_agent_skill.ps1` 和 `scripts/ensure_junction.ps1` **默认只做计划**，写用户目录需要权限及 `-Apply`。ChatGPT Web 使用单独构建的 Skill ZIP。普通用户不需要运行 PowerShell 或编辑 JSON，见 [快速上手](QUICKSTART.md)。

## 5. 开发依赖（普通用户无需安装）

```powershell
python -m pip install -e ".[dev]"
```

包含 pytest 和 Ruff；测试不得使用真实 Cookie、Bilibili 账号或私人笔记。完整说明见 [开发说明](DEVELOPMENT.md)。
