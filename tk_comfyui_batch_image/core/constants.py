"""Shared constants: page templates, enums."""

PAGE_TEMPLATES: dict[str, tuple[int, int]] = {
    "A4":            (2480, 3508),
    "B5":            (2079, 2953),
    "JP_Tankobon":   (2362, 3425),
    "Webtoon":       (1600, 12800),
}

READING_DIRECTIONS = ("ltr", "rtl")
SHAPE_TYPES = ("rect",)  # M1 only; M3 adds "split", M4 adds "polygon"
LAYOUT_MODES = ("vertical_stack",)  # M1 only
PANEL_ALIGNS = ("left", "center", "right")
ON_FAILURE_MODES = ("halt", "retry_then_skip")

DEFAULT_RETRIES = 2
