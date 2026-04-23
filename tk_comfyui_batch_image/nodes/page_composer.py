"""ComicPageComposer — assemble panels into full page images."""
from __future__ import annotations

import json

import numpy as np
import torch

from ..core.compositor import compose_page
from ..core.types import COMIC_SCRIPT_TYPE, SolvedScript


def _pil_to_tensor(img) -> np.ndarray:
    return np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0


def _bboxes_metadata(script: SolvedScript) -> dict:
    return {
        "job_id": script.job_id,
        "reading_direction": script.reading_direction,
        "pages": [
            {
                "page_index": page.page_index,
                "page_width": page.page_width,
                "page_height": page.page_height,
                "panels": [
                    {
                        "panel_index": panel.panel_index,
                        "bbox_topleft": list(panel.bbox_topleft),
                        "bbox_size":    list(panel.bbox_size),
                        "shape_type":   panel.shape_type,
                    } for panel in page.panels
                ],
            } for page in script.pages
        ],
    }


class ComicPageComposer:
    CATEGORY = "comic/io"
    FUNCTION = "compose"
    RETURN_TYPES = ("IMAGE", "STRING", "IMAGE")
    RETURN_NAMES = ("composed_pages", "panel_bboxes_json", "individual_panels")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "generated_panels": ("IMAGE",),
                "comic_script":     (COMIC_SCRIPT_TYPE,),
                "debug_overlay":    ("BOOLEAN", {"default": False}),
            }
        }

    def compose(self, generated_panels: torch.Tensor, comic_script: SolvedScript,
                debug_overlay: bool):
        panels_np = generated_panels.cpu().numpy()   # (N, Hmax, Wmax, 3)

        out_pages: list[np.ndarray] = []
        idx = 0
        for page in comic_script.pages:
            panel_imgs: list[tuple] = []
            for panel in page.panels:
                raw = panels_np[idx]
                w, h = panel.bbox_size
                cropped = raw[:h, :w, :]   # matching what BatchGenerator placed (top-left of padding)
                panel_imgs.append((panel, cropped))
                idx += 1
            pil = compose_page(page, panel_imgs)
            out_pages.append(_pil_to_tensor(pil))

        # Pad composed pages to same shape if sizes differ (M1: all same)
        max_h = max(p.shape[0] for p in out_pages)
        max_w = max(p.shape[1] for p in out_pages)
        padded = [np.pad(p, ((0, max_h - p.shape[0]), (0, max_w - p.shape[1]), (0, 0)),
                         constant_values=1.0) for p in out_pages]
        pages_tensor = torch.from_numpy(np.stack(padded, axis=0)).float()

        bboxes = json.dumps(_bboxes_metadata(comic_script), indent=2, ensure_ascii=False)
        return pages_tensor, bboxes, generated_panels
