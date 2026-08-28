from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SOURCE_MODE_SUBTITLE = "subtitle_srt"
SOURCE_MODE_ASR = "asr_text"
SOURCE_MODE_DESCRIPTION = "description_only"
SOURCE_MODES = frozenset({SOURCE_MODE_SUBTITLE, SOURCE_MODE_ASR, SOURCE_MODE_DESCRIPTION})


@dataclass(frozen=True)
class SourceMaterial:
    """Explicit source selected for one standard note Job."""

    mode: str
    path: Path | None = None

    def __post_init__(self) -> None:
        if self.mode not in SOURCE_MODES:
            raise ValueError(f"不支持的 source_mode：{self.mode}")
        if self.mode in {SOURCE_MODE_SUBTITLE, SOURCE_MODE_ASR} and self.path is None:
            raise ValueError(f"{self.mode} 必须提供 source path")
        if self.mode == SOURCE_MODE_DESCRIPTION and self.path is not None:
            raise ValueError("description_only 不应提供 source path")
