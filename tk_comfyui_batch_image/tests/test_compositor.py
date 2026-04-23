# tests/test_compositor.py
import numpy as np

from tk_comfyui_batch_image.core.compositor import compose_page
from tk_comfyui_batch_image.core.types import SolvedPage, SolvedPanel


def _solid_img(w: int, h: int, rgb: tuple[int, int, int]) -> np.ndarray:
    arr = np.full((h, w, 3), 0, dtype=np.float32)
    arr[..., 0] = rgb[0] / 255.0
    arr[..., 1] = rgb[1] / 255.0
    arr[..., 2] = rgb[2] / 255.0
    return arr


def _panel(page_i, panel_i, topleft, size, border_w=0) -> SolvedPanel:
    return SolvedPanel(
        page_index=page_i, panel_index=panel_i, global_index=0,
        positive_prompt="", negative_prompt="",
        width_px=size[0], height_px=size[1],
        bbox_topleft=topleft, bbox_size=size,
        align="center", shape_type="rect",
        polygon_local=None, polygon_abs=None,
        seed=0,
        sampler={"sampler_name":"euler","scheduler":"normal","steps":1,"cfg":1.0,"denoise":1.0},
        border={"width_px": border_w, "color": "#000000", "style": "solid"},
    )


def test_compose_single_rect_panel_on_white_page():
    page = SolvedPage(page_index=1, page_width=200, page_height=300,
                      bleed_px=10, background="#FFFFFF", panels=[])
    p = _panel(1, 1, topleft=(10, 10), size=(180, 100))
    img = _solid_img(180, 100, (255, 0, 0))
    out = compose_page(page, [(p, img)])
    assert out.size == (200, 300)
    out_arr = np.array(out)
    # pixel inside panel is red
    assert tuple(out_arr[50, 100]) == (255, 0, 0)
    # pixel in bleed area is white
    assert tuple(out_arr[5, 5]) == (255, 255, 255)


def test_compose_draws_border():
    page = SolvedPage(page_index=1, page_width=200, page_height=200,
                      bleed_px=10, background="#FFFFFF", panels=[])
    p = _panel(1, 1, topleft=(20, 20), size=(100, 100), border_w=4)
    img = _solid_img(100, 100, (0, 255, 0))
    out = compose_page(page, [(p, img)])
    out_arr = np.array(out)
    # Top-left corner of border
    assert tuple(out_arr[20, 20]) == (0, 0, 0)
    # Inside panel (past border)
    assert tuple(out_arr[70, 70]) == (0, 255, 0)


def test_compose_multiple_panels_gutter_background():
    page = SolvedPage(page_index=1, page_width=200, page_height=400,
                      bleed_px=10, background="#808080", panels=[])
    p1 = _panel(1, 1, topleft=(10, 10), size=(180, 100))
    p2 = _panel(1, 2, topleft=(10, 130), size=(180, 100))  # 20-gap gutter
    img_r = _solid_img(180, 100, (255, 0, 0))
    img_g = _solid_img(180, 100, (0, 255, 0))
    out = compose_page(page, [(p1, img_r), (p2, img_g)])
    out_arr = np.array(out)
    # Panel 1: red
    assert tuple(out_arr[50, 50]) == (255, 0, 0)
    # Gutter between panels: grey background
    assert tuple(out_arr[115, 50]) == (128, 128, 128)
    # Panel 2: green
    assert tuple(out_arr[180, 50]) == (0, 255, 0)
