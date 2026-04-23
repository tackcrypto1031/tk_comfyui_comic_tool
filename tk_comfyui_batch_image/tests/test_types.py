from tk_comfyui_batch_image.core.types import (
    COMIC_SCRIPT_TYPE, SolvedPanel, SolvedPage, SolvedScript
)


def test_comic_script_type_name():
    assert COMIC_SCRIPT_TYPE == "COMIC_SCRIPT"


def test_solved_panel_has_required_fields():
    p = SolvedPanel(
        page_index=1, panel_index=1, global_index=0,
        positive_prompt="a", negative_prompt="b",
        width_px=100, height_px=80,
        bbox_topleft=(10, 10), bbox_size=(100, 80),
        align="center",
        shape_type="rect",
        polygon_local=None, polygon_abs=None,
        seed=42,
        sampler={"sampler_name": "euler", "scheduler": "normal",
                 "steps": 25, "cfg": 7.0, "denoise": 1.0},
        border={"width_px": 3, "color": "#000000", "style": "solid"},
    )
    assert p.page_index == 1
    assert p.bbox_size == (100, 80)


def test_solved_page_aggregates_panels():
    sp = SolvedPage(page_index=1, page_width=500, page_height=700,
                    bleed_px=10, background="#FFFFFF", panels=[])
    assert sp.page_index == 1
    assert sp.panels == []


def test_solved_script_carries_book_level():
    script = SolvedScript(
        version="1.0", job_id="test", reading_direction="ltr",
        base_seed=12345, pages=[],
    )
    assert script.job_id == "test"
