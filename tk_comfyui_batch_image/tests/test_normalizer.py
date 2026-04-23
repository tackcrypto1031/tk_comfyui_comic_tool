# tests/test_normalizer.py
import json
from pathlib import Path

from tk_comfyui_batch_image.core.normalizer import normalize_script
from tk_comfyui_batch_image.core.types import SolvedPanel, SolvedScript

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_normalize_minimal_returns_solved_script():
    s = normalize_script(_load("minimal.json"))
    assert isinstance(s, SolvedScript)
    assert s.job_id == "min"
    assert len(s.pages) == 1
    assert len(s.pages[0].panels) == 1

    p = s.pages[0].panels[0]
    assert isinstance(p, SolvedPanel)
    assert p.page_index == 1
    assert p.panel_index == 1
    assert p.global_index == 0
    assert p.width_px == 472
    assert p.bbox_size == (472, 300)
    assert p.shape_type == "rect"
    assert p.polygon_local is None


def test_prompt_is_concatenated():
    s = normalize_script(_load("minimal.json"))
    p = s.pages[0].panels[0]
    assert p.positive_prompt == "anime style, a girl, short hair, looking at sky"
    assert p.negative_prompt == "blurry"


def test_sampler_override_merges_over_defaults():
    s = normalize_script(_load("basic.json"))
    p21 = s.pages[1].panels[0]
    assert p21.sampler["steps"] == 30    # overridden
    assert p21.sampler["cfg"] == 8.0     # overridden
    assert p21.sampler["sampler_name"] == "euler"  # inherited


def test_seed_offset_uses_global_index():
    s = normalize_script(_load("basic.json"))
    seeds = [panel.seed for page in s.pages for panel in page.panels]
    assert seeds == [7, 8, 9, 10]  # base_seed=7, 3 panels in p1 + 1 in p2


def test_page_template_custom_uses_explicit_size():
    s = normalize_script(_load("minimal.json"))
    assert s.pages[0].page_width == 512
    assert s.pages[0].page_height == 768


def test_page_template_A4_overrides_explicit_size():
    data = _load("minimal.json")
    data["page_template"] = "A4"
    data["page_width_px"] = 100    # should be ignored
    data["page_height_px"] = 100
    # Need a panel that fits A4
    data["pages"][0]["panels"][0]["width_px"] = 2000
    s = normalize_script(data)
    assert s.pages[0].page_width == 2480
    assert s.pages[0].page_height == 3508


def test_border_inherits_then_overrides():
    data = _load("minimal.json")
    data["pages"][0]["panels"][0]["border"] = {"width_px": 5, "color": "#FF0000", "style": "solid"}
    s = normalize_script(data)
    assert s.pages[0].panels[0].border == {"width_px": 5, "color": "#FF0000", "style": "solid"}


def test_panels_solved_includes_bbox_from_layout():
    s = normalize_script(_load("basic.json"))
    p1 = s.pages[0].panels[0]
    # inner area 20~492 × 20~748; panel w=472, align=center → x = 20
    assert p1.bbox_topleft == (20, 20)
    assert p1.bbox_size == (472, 200)
    # second panel
    p2 = s.pages[0].panels[1]
    assert p2.bbox_topleft == (20, 230)  # 20 + 200 + 10 gutter
