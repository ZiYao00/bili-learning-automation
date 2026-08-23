from __future__ import annotations

import re
from pathlib import Path
from typing import Any

FACT_LEDGER_FILENAME = "fact-ledger.md"
SEMANTIC_DRAFT_FILENAME = "semantic-draft.md"
LAYOUT_PLAN_FILENAME = "layout-plan.md"

_WORKFLOW_PATHS = {
    "fact_ledger_path": ("fact_ledger", FACT_LEDGER_FILENAME),
    "semantic_draft_path": ("semantic_draft", SEMANTIC_DRAFT_FILENAME),
    "layout_plan_path": ("layout_plan", LAYOUT_PLAN_FILENAME),
}


def _write_new(path: Path, content: str) -> None:
    if path.exists():
        raise FileExistsError(f"运行时工作文件已存在，拒绝覆盖：{path}")
    path.write_text(content, encoding="utf-8", newline="\n")


def _frontmatter(stage: str) -> str:
    return (
        "---\n"
        f"workflow_stage: {stage}\n"
        "workflow_status: pending\n"
        'workflow_reason: ""\n'
        "---\n\n"
    )


def write_agent_work_templates(agent_work_dir: Path) -> dict[str, str]:
    """创建分离事实保全、内容成稿与视觉排版的 runtime 工作文件。"""

    agent_work_dir.mkdir(parents=True, exist_ok=True)
    fact_ledger = agent_work_dir / FACT_LEDGER_FILENAME
    semantic_draft = agent_work_dir / SEMANTIC_DRAFT_FILENAME
    layout_plan = agent_work_dir / LAYOUT_PLAN_FILENAME

    _write_new(
        fact_ledger,
        _frontmatter("fact_ledger")
        + """# Fact Ledger（原子事实账本）

> 仅用于当前 runtime。不得把本文件名、Fact ID、路径或工作状态写入正式笔记。

长字幕、百科型、参数密集或实测证据多的视频，必须先按 manifest 顺序阅读 transcript，并在规划章节前记录原子事实。

完成方式：

- 知识密集型内容完成后，把 `workflow_status` 改为 `complete`。
- 短且简单、无需独立 Fact Ledger 的视频，可改为 `not_applicable`，并在 `workflow_reason` 写明原因。

规则：

- 保留具体成员、数值、上限/下限、版本、兼容性、安装前提、例外、冲突、作者评价，以及 `配置 → 耗时 / 质量 / 失败表现` 的证据链。
- “模型选择”“提示词”“加速方案”只是主题标签，不是原子事实。
- 本阶段不决定最终 H2 数量，也不为了文章简洁删减事实。
- 来源术语损坏或无法确认时，保留不确定性，不得用模型常识静默修正。

| Fact ID | 来源 chunk / 时间 | 原子事实 | 关系 / 条件 / 证据 | 最终去向或省略理由 |
| --- | --- | --- | --- | --- |
| F001 |  |  |  | pending |
""",
    )
    _write_new(
        semantic_draft,
        _frontmatter("semantic_draft")
        + """# Semantic Draft（内容完成稿）

> 仅用于当前 runtime。先把知识写完整，再应用 Learning Lab 视觉组件。

根据 Fact Ledger 与当前 transcript 写一份完整的普通 Markdown 内容稿。可以使用自然标题、段落、列表、步骤和具有固定比较字段的表格；此时不要仅为了好看添加 Grid / Card / Badge / Metric / Chip。

完成内容稿后，把 `workflow_status` 改为 `complete`。

规则：

- 章节数量只决定事实如何分组，不改变事实保留预算。
- 一个 H2 可以通过 H3、表格、列表和必要 Callout 承载大量原子事实。
- `knowledge_outline` 只用于上层索引和复核，不是事实来源，也不是最终目录。
- 保留足够条件与结果，使读者能够复查某个方案为什么更快、更慢、更稳、更软，或能否兼容。
- 本内容稿完成前，不编辑正式笔记正文。

## 内容稿

""",
    )
    _write_new(
        layout_plan,
        _frontmatter("layout_plan")
        + """# Layout Plan（排版计划）

> 仅用于当前 runtime。排版只转换完整内容的表达形式，不是第二次摘要。

把 Semantic Draft 中已经存在的语义关系映射到最小且合适的视觉组件。本阶段不得重新选择、删除或发明事实。完成排版计划并核对事实无损后，把 `workflow_status` 改为 `complete`。

| 现有章节 / 内容关系 | 推荐表达 | 为什么适合 | 事实无损检查 |
| --- | --- | --- | --- |
|  |  |  | pending |

检查清单：

- 整页只保留一个最高优先级 Summary。
- 只有真实并列或比较关系才使用 Grid / Card；有固定字段或 4 个以上对象时优先 Table。
- 需要保留检索、但不值得逐项展开的名称使用 Chip。
- 冲突、互斥、兼容性、失败模式或明确不推荐路线使用 Risk。
- 来源损坏、术语不确定或验证边界使用 Meta。
- 排版完成后，重新确认 Semantic Draft 中每个高价值事实仍存在于最终正文。
""",
    )

    return {
        "fact_ledger_path": str(fact_ledger),
        "semantic_draft_path": str(semantic_draft),
        "layout_plan_path": str(layout_plan),
    }


def _field(text: str, name: str) -> str | None:
    match = re.search(rf"^{re.escape(name)}:\s*(.*?)\s*$", text, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip('"\'')


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _fact_ledger_has_content(text: str) -> bool:
    for line in text.splitlines():
        if not re.match(r"^\|\s*F\d+\s*\|", line):
            continue
        cells = _table_cells(line)
        if len(cells) >= 5 and cells[2] and cells[4].lower() != "pending":
            return True
    return False


def _semantic_draft_has_content(text: str) -> bool:
    if "## 内容稿" not in text:
        return False
    body = text.split("## 内容稿", 1)[1]
    return len(re.sub(r"\s+", "", body)) >= 40


def _layout_plan_has_content(text: str) -> bool:
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = _table_cells(line)
        if len(cells) < 4 or cells[0] in {"现有章节 / 内容关系", "---", ""}:
            continue
        if cells[1] and cells[3].lower() != "pending":
            return True
    return False


def validate_agent_workflow(job: dict[str, Any]) -> list[str]:
    """严格模式校验三个 runtime 阶段；轻量模式不强制中间工作文件。"""

    mode = job.get("workflow_mode")
    if mode == "light":
        return []
    if mode not in {None, "strict"}:
        return ["workflow_mode 无效"]

    present = [key in job for key in _WORKFLOW_PATHS]
    if not any(present):
        return ["strict 模式缺少运行时工作文件"] if mode == "strict" else []
    if not all(present):
        return ["运行时工作流路径不完整"]

    work_dir_value = job.get("agent_work_dir")
    if not isinstance(work_dir_value, str) or not work_dir_value:
        return ["缺少 agent_work_dir"]
    work_dir = Path(work_dir_value).resolve()
    errors: list[str] = []

    for key, (expected_stage, expected_name) in _WORKFLOW_PATHS.items():
        value = job.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"缺少运行时工作文件路径：{key}")
            continue
        path = Path(value)
        try:
            resolved = path.resolve()
        except OSError:
            errors.append(f"无法解析运行时工作文件：{key}")
            continue
        if resolved.parent != work_dir or resolved.name != expected_name:
            errors.append(f"运行时工作文件路径越界或文件名错误：{key}")
            continue
        if not path.is_file():
            errors.append(f"缺少运行时工作文件：{expected_name}")
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            errors.append(f"无法读取运行时工作文件：{expected_name}")
            continue
        stage = _field(text, "workflow_stage")
        status = _field(text, "workflow_status")
        reason = _field(text, "workflow_reason") or ""
        if stage != expected_stage:
            errors.append(f"运行时工作阶段标识错误：{expected_name}")
            continue

        if expected_stage == "fact_ledger" and status == "not_applicable":
            if not reason:
                errors.append("Fact Ledger 标记为 not_applicable 时必须填写 workflow_reason")
            continue
        if status != "complete":
            errors.append(f"运行时工作阶段尚未完成：{expected_name}")
            continue

        if expected_stage == "fact_ledger" and not _fact_ledger_has_content(text):
            errors.append("Fact Ledger 已标记 complete，但没有完成的原子事实条目")
        elif expected_stage == "semantic_draft" and not _semantic_draft_has_content(text):
            errors.append("Semantic Draft 已标记 complete，但内容稿为空或过短")
        elif expected_stage == "layout_plan" and not _layout_plan_has_content(text):
            errors.append("Layout Plan 已标记 complete，但没有完成的排版决定")

    return errors
