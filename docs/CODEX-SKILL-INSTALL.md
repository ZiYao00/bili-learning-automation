# Codex Skill 安装教程

这份文档用于安装统一 `bili-learning-automation` Skill 的 Codex 安装出口。Codex 与 ChatGPT、Hermes、WorkBuddy 共用一份人工维护的 Skill 真源和同一项目核心；Codex 只保留本地工作区这一最小宿主边界。

## 1. 统一 Skill 真源与 Codex 安装出口

唯一需要人工编辑的 Skill 真源位于：

```text
<repo-root>\skill\bili-learning-automation
```

运行 `scripts\build_agent_skill_packages.py` 后，会生成仓库级 Codex 安装出口：

```text
<repo-root>\.agents\skills\bili-learning-automation-codex
```

其安装名称仍是 `bili-learning-automation-codex`，因此现有调用方式不变。当 Codex 从该项目目录或其子目录启动时会自动发现这个生成出口；不要直接修改其中的 `SKILL.md`。

## 2. 推荐方式：直接使用仓库级 Skill

进入项目目录后启动 Codex。新会话中可以显式调用：

```text
$bili-learning-automation-codex
```

第一次先说：

```text
使用 $bili-learning-automation-codex 检查 Skill 安装状态和运行环境，暂时不要转换视频。
```

Codex 应先读取根目录 `AGENTS.md`，再运行统一 onboarding。只有 onboarding 返回 `ready`，才表示当前可以直接使用。

这种方式不需要复制 Skill；更新仓库后，Codex 会读取当前仓库中的最新版。若列表没有刷新，重新启动 Codex 会话。

## 3. 全局使用：Junction

如果希望在其他工作目录中也能调用，可以把用户级 Skill 目录链接到仓库适配层。

Codex 用户级 Skill 目录：

```text
%USERPROFILE%\.agents\skills\
```

PowerShell 示例：

```powershell
$source = '<repo-root>\.agents\skills\bili-learning-automation-codex'
$target = Join-Path $HOME '.agents\skills\bili-learning-automation-codex'

Test-Path $source
Get-Item $target -ErrorAction SilentlyContinue | Format-List FullName,LinkType,Target
```

确认源目录存在且目标不存在后，再创建 Junction：

```powershell
New-Item -ItemType Junction -Path $target -Target $source
```

如果目标已经存在，先检查它是目录、旧副本还是已有 Junction；不要直接覆盖或批量删除。

Junction 只让 Codex 找到适配层。执行笔记任务时仍需打开或明确提供实际项目根目录，Skill 不会扫描整块磁盘猜位置。

## 4. 独立 ZIP 安装

在项目根目录运行：

```powershell
python .\scripts\build_agent_skill_packages.py
```

Codex 安装包是：

```text
<repo-root>\dist\bili-learning-automation-codex.zip
```

该 ZIP 内只有：

```text
bili-learning-automation-codex/
├── SKILL.md
└── agents/
    └── openai.yaml
```

可以把压缩包解压到：

```text
%USERPROFILE%\.agents\skills\
```

解压前先确认同名目标目录不存在，避免覆盖已有 Skill。ZIP 安装是静态副本；仓库更新后需要重新生成并更新该副本。长期在本机维护时，优先使用仓库级 Skill 或 Junction。

不要把 Codex ZIP 上传到 ChatGPT 的“插件 → 技能”页面。

## 5. 稳定命令入口

Codex 适配层统一调用：

```powershell
python scripts/run_bili_learning.py <command> [args]
```

该启动器会从自身位置定位项目核心，因此不要求先执行 `pip install -e .`，也不再借用 Hermes 脚本。

## 6. 安装与运行验收

需要分别确认：

- **Skill 已发现**：Codex 的 Skill 列表中存在 `bili-learning-automation-codex`；
- **项目已定位**：当前工作区包含 `pyproject.toml`、`AGENTS.md` 和 taxonomy；
- **运行环境已就绪**：onboarding 返回 `ready`。

如果项目未定位，Codex 应让用户打开或提供项目根目录，不得自动搜索所有磁盘。如果 onboarding 返回 `action_required`，只处理实际缺失项；Cookie 只接收 Netscape 文件路径，不读取或展示内容。

## 7. 与其他入口的关系

Hermes、WorkBuddy、ChatGPT 和 Codex 共用同一个 Skill 真源、Python 核心、配置、Job lifecycle、来源契约和 finalizer，只保留不同安装出口与最小宿主权限边界。四个 ZIP 由同一构建脚本分别生成，不需要人工同步四份 `SKILL.md`。
