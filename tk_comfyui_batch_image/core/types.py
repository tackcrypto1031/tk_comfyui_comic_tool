"""Runtime dataclasses for the solved (normalized) comic script."""
from __future__ import annotations

from dataclasses import dataclass, field

COMIC_SCRIPT_TYPE = "COMIC_SCRIPT"


@dataclass
class SolvedPanel:
    page_index: int
    panel_index: int
    global_index: int                # 0-based across whole book (for seed offset)
    positive_prompt: str
    negative_prompt: str
    width_px: int
    height_px: int
    bbox_topleft: tuple[int, int]    # absolute (x, y) on page canvas
    bbox_size: tuple[int, int]       # (w, h) — for rect = width_px × height_px
    align: str                        # "left" | "center" | "right"
    shape_type: str                   # "rect" in M1
    polygon_local: list[tuple[float, float]] | None   # None for rect
    polygon_abs: list[tuple[int, int]] | None         # None for rect
    seed: int
    sampler: dict                     # merged sampler settings
    border: dict                      # {"width_px": int, "color": "#RRGGBB", "style": str}


@dataclass
class SolvedPage:
    page_index: int
    page_width: int
    page_height: int
    bleed_px: int
    background: str                   # "#RRGGBB"
    panels: list[SolvedPanel] = field(default_factory=list)


@dataclass
class SolvedScript:
    version: str
    job_id: str
    reading_direction: str
    base_seed: int
    pages: list[SolvedPage] = field(default_factory=list)
