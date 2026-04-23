# tests/test_page_composer.py
import json
from pathlib import Path
import numpy as np
import torch
from PIL import Image

from tk_comfyui_batch_image.core.normalizer import normalize_script
from tk_comfyui_batch_image.nodes.page_composer import ComicPageComposer

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


def _make_panel_stack(script) -> torch.Tensor:
    """Produce a solid-colour IMAGE batch matching each panel's bbox_size."""
    imgs = []
    for page in script.pages:
        for panel in page.panels:
            w, h = panel.bbox_size
            arr = np.full((h, w, 3), 0.5, dtype=np.float32)
            imgs.append(arr)
    # Pad to same H/W by placing each into a max-sized canvas
    max_h = max(a.shape[0] for a in imgs)
    max_w = max(a.shape[1] for a in imgs)
    padded = [np.pad(a, ((0, max_h - a.shape[0]), (0, max_w - a.shape[1]), (0, 0)),
                     constant_values=1.0) for a in imgs]
    return torch.from_numpy(np.stack(padded, axis=0)).float()


def test_compose_basic_script_yields_n_pages():
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    stack = _make_panel_stack(script)
    pages, bboxes_json, pass_panels = ComicPageComposer().compose(
        generated_panels=stack, comic_script=script, debug_overlay=False,
    )
    assert isinstance(pages, torch.Tensor)
    assert pages.shape[0] == 2   # 2 pages
    assert pages.shape[-1] == 3
    assert pages.shape[1] == script.pages[0].page_height
    assert pages.shape[2] == script.pages[0].page_width


def test_bboxes_json_includes_all_panels():
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    stack = _make_panel_stack(script)
    _, bboxes_json, _ = ComicPageComposer().compose(
        generated_panels=stack, comic_script=script, debug_overlay=False,
    )
    parsed = json.loads(bboxes_json)
    assert len(parsed["pages"]) == 2
    assert len(parsed["pages"][0]["panels"]) == 3
    p0 = parsed["pages"][0]["panels"][0]
    assert "bbox_topleft" in p0 and "bbox_size" in p0


def test_individual_panels_passthrough_preserves_order():
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    stack = _make_panel_stack(script)
    _, _, pass_panels = ComicPageComposer().compose(
        generated_panels=stack, comic_script=script, debug_overlay=False,
    )
    assert torch.equal(pass_panels, stack)
