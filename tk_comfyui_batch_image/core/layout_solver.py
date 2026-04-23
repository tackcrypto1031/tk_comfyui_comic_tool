"""Resolve panel absolute bboxes for supported layout modes.

M1 supports `vertical_stack` with rect panels only.
"""
from __future__ import annotations


class LayoutError(ValueError):
    """Raised when layout cannot be resolved."""


def solve_vertical_stack(
    *,
    page_width: int,
    page_height: int,
    bleed_px: int,
    gutter_px: int,
    panels: list[dict],
) -> list[dict]:
    """Return one dict per panel: {bbox_topleft: (x,y), bbox_size: (w,h)}.

    Panels are stacked top-to-bottom with `gutter_px` between them.
    Horizontal alignment respects `align` in {"left","center","right"} relative
    to the inner content area (page minus bleed on each side).
    """
    inner_left   = bleed_px
    inner_right  = page_width - bleed_px
    inner_top    = bleed_px
    inner_bottom = page_height - bleed_px
    inner_w = inner_right - inner_left
    inner_h = inner_bottom - inner_top
    if inner_w <= 0 or inner_h <= 0:
        raise LayoutError(f"bleed_px {bleed_px} too large for page {page_width}x{page_height}")

    total_h = sum(p["height_px"] for p in panels) + gutter_px * max(0, len(panels) - 1)
    if total_h > inner_h:
        raise LayoutError(
            f"vertical_stack: total panel height {sum(p['height_px'] for p in panels)}px + "
            f"gutters {gutter_px * max(0, len(panels)-1)}px = {total_h}px "
            f"exceeds inner content area {inner_h}px (page {page_height} - bleed*2). "
            f"hint: reduce a panel height or increase page_height_px."
        )

    results: list[dict] = []
    y = inner_top
    for i, p in enumerate(panels):
        w, h, align = p["width_px"], p["height_px"], p["align"]
        if w > inner_w:
            raise LayoutError(
                f"panel {i} width {w}px exceeds inner content width {inner_w}px"
            )
        if align == "left":
            x = inner_left
        elif align == "right":
            x = inner_right - w
        else:  # center
            x = inner_left + (inner_w - w) // 2
        results.append({"bbox_topleft": (x, y), "bbox_size": (w, h)})
        y += h + gutter_px
    return results
