"""Compose a SolvedPage + per-panel images into a single PIL.Image."""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from PIL import Image, ImageDraw

from .image_ops import arr_to_pil, hex_to_rgb
from .types import SolvedPage, SolvedPanel


def compose_page(
    page: SolvedPage,
    panel_images: Iterable[tuple[SolvedPanel, np.ndarray]],
) -> Image.Image:
    """Paste each panel image onto the page canvas and draw its border (if any).

    `panel_images` yields (SolvedPanel, HxWx3 float32 in [0,1] or uint8) pairs.
    """
    canvas = Image.new("RGB", (page.page_width, page.page_height), hex_to_rgb(page.background))

    for panel, img_arr in panel_images:
        pil = arr_to_pil(img_arr)
        # In M1 every panel is rect; paste directly.
        canvas.paste(pil, panel.bbox_topleft)

        if panel.border["width_px"] > 0:
            draw = ImageDraw.Draw(canvas)
            x0, y0 = panel.bbox_topleft
            w, h = panel.bbox_size
            color = hex_to_rgb(panel.border["color"])
            width = panel.border["width_px"]
            draw.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], outline=color, width=width)

    return canvas
