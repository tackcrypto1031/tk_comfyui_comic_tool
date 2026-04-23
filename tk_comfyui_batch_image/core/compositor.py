"""Compose a SolvedPage + per-panel images into a single PIL.Image."""
from __future__ import annotations
from typing import Iterable
import numpy as np
from PIL import Image, ImageDraw
from .types import SolvedPage, SolvedPanel


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _arr_to_pil(arr: np.ndarray) -> Image.Image:
    if arr.dtype != np.uint8:
        arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def compose_page(
    page: SolvedPage,
    panel_images: Iterable[tuple[SolvedPanel, np.ndarray]],
) -> Image.Image:
    """Paste each panel image onto the page canvas and draw its border (if any).

    `panel_images` yields (SolvedPanel, HxWx3 float32 in [0,1] or uint8) pairs.
    """
    canvas = Image.new("RGB", (page.page_width, page.page_height), _hex_to_rgb(page.background))

    for panel, img_arr in panel_images:
        pil = _arr_to_pil(img_arr)
        # In M1 every panel is rect; paste directly.
        canvas.paste(pil, panel.bbox_topleft)

        if panel.border["width_px"] > 0:
            draw = ImageDraw.Draw(canvas)
            x0, y0 = panel.bbox_topleft
            w, h = panel.bbox_size
            color = _hex_to_rgb(panel.border["color"])
            width = panel.border["width_px"]
            draw.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], outline=color, width=width)

    return canvas
