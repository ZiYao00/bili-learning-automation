# 轻量写作流程实验验收

日期：2026-08-23

## 实验目的

此前的严格流程通过 Fact Ledger、Semantic Draft、Layout Plan 与阶段门禁提高可审计性，但真实回归显示，中档模型可能把更多注意力用于完成流程和通过校验，而不是深入理解字幕、组织知识和优化版式。

本轮保留严格流程，同时新增并默认启用一个限制更少的轻量流程，用相同视频继续做 A/B 测试。

## 执行前备份

已使用项目自带备份脚本生成完整源码快照：

```text
<repo-root>/.codex-backups/90-full-snapshots/bili-learning-automation-before-light-workflow-experiment-<timestamp>.zip
```

备份共包含 239 个文件。按项目既有安全规则，备份不包含 `.git`、`.runtime`、虚拟环境、缓存、`key` 目录或 Cookie 凭据。

## 两种工作模式

### `light`：当前默认

```text
完整读取 transcript
→ 判断来源充分性
→ 直接完成笔记内容
→ 内容完成后独立优化版式
→ 回看 transcript 修正明显遗漏与无来源事实
→ finalizer
```

特点：

- 不创建 Fact Ledger、Semantic Draft 或 Layout Plan；
- 不要求填写阶段状态；
- 不预设章节数量、文章长度或组件组合；
- 写作阶段只读取简短的 `LIGHT-WORKFLOW.md`；
- 进入排版阶段后，才可按需查看 Obsidian 样式说明或示例中的相关局部片段；
- 保留来源、确定性结构、禁止覆盖、内部信息隔离和 finalizer 等硬边界。

### `strict`：保留的可选模式

继续执行：

```text
Fact Ledger
→ knowledge_outline
→ Semantic Draft
→ Layout Plan
→ Source Recheck
```

并保留三份 runtime 工作文件、`workflow_status` 和 finalizer 阶段门禁。

## 配置方式

默认无需增加配置，即使用 `light`。

显式配置：

```json
{
  "workflow_mode": "light"
}
```

切回严格模式：

```json
{
  "workflow_mode": "strict"
}
```

也可临时使用：

```text
BILI_LEARNING_WORKFLOW_MODE=light
BILI_LEARNING_WORKFLOW_MODE=strict
```

环境变量优先于 `config/local.json`。

## 核心实现

- `Settings` 新增 `workflow_mode`，只接受 `light` / `strict`；
- collector 在所有 job 中记录并返回工作模式；
- `light` 不创建三份阶段文件，使用精简 handoff；
- `strict` 保留此前全部阶段文件与门禁；
- finalizer / validator 仅在 `strict` 下要求三份阶段文件；
- Codex、Hermes、WorkBuddy 都先读取 `workflow_mode` 再选择说明；
- doctor 输出当前工作模式；
- README、Quick Start、配置、架构和标准文档已同步。

## 共同硬边界

两种模式都继续要求：

- 正文事实只来自当前字幕和 UP 主简介；
- 来源不足时停止，不以模型常识补具体事实；
- 不修改程序生成的 Frontmatter、H1、元信息、播放器、来源区、资源、tags、cssclasses、路径和 marker；
- 不覆盖已有笔记；
- 不把 Cookie、runtime 路径、日志或内部状态写入正式笔记；
- 只有 finalizer 返回 `note_ready` 且临时数据清理成功才报告完成。

## 未修改范围

本轮没有修改：

- 字幕采集与 yt-dlp 参数；
- transcript cue 解析和切块阈值；
- `analysis.json schema_version: 1`；
- taxonomy；
- `learning-lab.css` 与 `video-note.css`；
- 现有笔记；
- 用户的本机 Vault、Cookie 内容和私有路径配置；
- Git 提交与推送。

## 验证结果

```text
.venv/Scripts/python.exe -m pytest -q
75 passed

.venv/Scripts/python.exe -m ruff check src tests
All checks passed!
```

回归覆盖：

- 默认模式为 `light`；
- 本机配置和环境变量可切换模式；
- 非法模式会被拒绝；
- light job 不创建三份阶段文件；
- strict job 仍创建并校验三份阶段文件；
- light handoff 保持简短并直接写作；
- strict handoff 与阶段门禁继续有效；
- light 模式可以正常完成 finalizer、导航、重复转换和清理；
- 配置工具会保留已有 `workflow_mode`。

## 建议的真实回归

继续使用此前完全相同的三条视频，并保持模型为 Terra（中），以隔离“流程变化”本身的影响。

重点比较：

1. 一体化节点中的功能细节、API 限制、模型选择、安装条件和平台边界是否恢复；
2. 百科视频中的具体案例、失败表现、作者判断与二级关系是否比严格版完整；
3. 章节是否自然，而不是重新固定为五段；
4. 内容完成后的排版是否更接近人工编辑，而不是最低限度表格；
5. 是否出现新的幻觉、固定结构或确定性区域损坏。
