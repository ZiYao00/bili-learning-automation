from __future__ import annotations

from pathlib import Path


def test_multi_item_notes_keep_source_order_numbering_and_links() -> None:
    light = Path("docs/standards/LIGHT-WORKFLOW.md").read_text(encoding="utf-8")
    strict = Path("docs/standards/CODEX-VIDEO-NOTE-GUIDE.md").read_text(encoding="utf-8")

    for guide in (light, strict):
        assert "连续编号 `01 → N`" in guide
        assert "概览表与详细标题复用同一编号" in guide
        assert "Markdown 超链接" in guide
        assert "不能替代或重排连续编号正文" in guide
