"""Shared image conversion helpers used across core and nodes."""
from __future__ import annotations

import numpy as np
from PIL import Image


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def arr_to_pil(arr: np.ndarray) -> Image.Image:
    """Convert an HxWx3 numpy array (float32 in [0,1] or uint8) to a PIL RGB image."""
    if arr.dtype != np.uint8:
        arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def pil_to_arr(img: Image.Image) -> np.ndarray:
    """Convert a PIL image to HxWx3 float32 numpy array in [0, 1]."""
    return np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
