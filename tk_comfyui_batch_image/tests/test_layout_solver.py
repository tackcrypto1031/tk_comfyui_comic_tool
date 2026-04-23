import pytest

from tk_comfyui_batch_image.core.layout_solver import LayoutError, solve_vertical_stack


def test_single_panel_centered():
    result = solve_vertical_stack(
        page_width=500, page_height=800, bleed_px=20, gutter_px=10,
        panels=[{"width_px": 400, "height_px": 300, "align": "center"}],
    )
    assert len(result) == 1
    assert result[0] == {"bbox_topleft": (50, 20), "bbox_size": (400, 300)}


def test_three_panels_stacked_with_gutter():
    result = solve_vertical_stack(
        page_width=500, page_height=800, bleed_px=20, gutter_px=10,
        panels=[
            {"width_px": 460, "height_px": 200, "align": "center"},
            {"width_px": 460, "height_px": 200, "align": "left"},
            {"width_px": 460, "height_px": 200, "align": "right"},
        ],
    )
    assert result[0]["bbox_topleft"] == (20, 20)
    assert result[1]["bbox_topleft"] == (20, 230)   # 20 + 200 + 10
    assert result[2]["bbox_topleft"] == (20, 440)
    assert all(r["bbox_size"] == (460, 200) for r in result)


def test_align_left_positions_at_bleed():
    result = solve_vertical_stack(
        page_width=500, page_height=800, bleed_px=20, gutter_px=0,
        panels=[{"width_px": 200, "height_px": 100, "align": "left"}],
    )
    assert result[0]["bbox_topleft"] == (20, 20)


def test_align_right_positions_against_right_bleed():
    result = solve_vertical_stack(
        page_width=500, page_height=800, bleed_px=20, gutter_px=0,
        panels=[{"width_px": 200, "height_px": 100, "align": "right"}],
    )
    # right edge = 500 - 20 = 480; x = 480 - 200 = 280
    assert result[0]["bbox_topleft"] == (280, 20)


def test_overflow_raises():
    with pytest.raises(LayoutError) as exc:
        solve_vertical_stack(
            page_width=500, page_height=400, bleed_px=20, gutter_px=10,
            panels=[
                {"width_px": 460, "height_px": 300, "align": "center"},
                {"width_px": 460, "height_px": 300, "align": "center"},
            ],
        )
    assert "exceeds inner content area" in str(exc.value)


def test_panel_wider_than_inner_area_raises():
    with pytest.raises(LayoutError) as exc:
        solve_vertical_stack(
            page_width=500, page_height=800, bleed_px=20, gutter_px=0,
            panels=[{"width_px": 600, "height_px": 100, "align": "center"}],
        )
    assert "panel 0 width" in str(exc.value)
