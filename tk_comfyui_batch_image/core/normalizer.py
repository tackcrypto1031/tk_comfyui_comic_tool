"""Normalize a validated JSON dict into a SolvedScript with fully-resolved panels."""
from __future__ import annotations

from .constants import PAGE_TEMPLATES
from .layout_solver import solve_vertical_stack
from .prompt_builder import build_prompt_pair
from .types import SolvedPage, SolvedPanel, SolvedScript


def _resolve_page_size(data: dict) -> tuple[int, int]:
    tpl = data["page_template"]
    if tpl == "custom":
        return int(data["page_width_px"]), int(data["page_height_px"])
    if tpl in PAGE_TEMPLATES:
        return PAGE_TEMPLATES[tpl]
    raise ValueError(f"unknown page_template: {tpl}")


def normalize_script(data: dict) -> SolvedScript:
    """Validated JSON dict → SolvedScript with resolved bboxes, prompts, sampler, seeds."""
    page_w, page_h = _resolve_page_size(data)
    bleed   = int(data["bleed_px"])
    gutter  = int(data["gutter_px"])
    bg      = data["page_background"]
    base_seed = int(data["base_seed"])
    default_sampler = dict(data["default_sampler"])
    default_border  = dict(data["default_border"])

    style_p = data["style_prompt"]
    char_p  = data["character_prompt"]

    pages: list[SolvedPage] = []
    global_idx = 0
    for page in data["pages"]:
        page_prompt = page["page_prompt"]
        page_gutter = int(page.get("gutter_px", gutter))
        page_panels_raw = page["panels"]

        # solve layout for rect panels
        bbox_specs = solve_vertical_stack(
            page_width=page_w, page_height=page_h,
            bleed_px=bleed, gutter_px=page_gutter,
            panels=[{"width_px": p["width_px"], "height_px": p["height_px"],
                     "align": p["align"]} for p in page_panels_raw],
        )

        solved_panels: list[SolvedPanel] = []
        for raw, bb in zip(page_panels_raw, bbox_specs, strict=False):
            pos, neg = build_prompt_pair(
                style=style_p, character=char_p,
                page=page_prompt, scene=raw["scene_prompt"],
            )
            override = raw.get("sampler_override") or {}
            merged_sampler = {**default_sampler, **{k: v for k, v in override.items() if k != "seed"}}
            seed = int(override["seed"]) if "seed" in override else base_seed + global_idx
            border = dict(raw.get("border") or default_border)

            solved_panels.append(SolvedPanel(
                page_index=int(page["page_index"]),
                panel_index=int(raw["panel_index"]),
                global_index=global_idx,
                positive_prompt=pos,
                negative_prompt=neg,
                width_px=int(raw["width_px"]),
                height_px=int(raw["height_px"]),
                bbox_topleft=bb["bbox_topleft"],
                bbox_size=bb["bbox_size"],
                align=raw["align"],
                shape_type=raw["shape"]["type"],
                polygon_local=None,
                polygon_abs=None,
                seed=seed,
                sampler=merged_sampler,
                border=border,
            ))
            global_idx += 1

        pages.append(SolvedPage(
            page_index=int(page["page_index"]),
            page_width=page_w, page_height=page_h,
            bleed_px=bleed, background=bg,
            panels=solved_panels,
        ))

    return SolvedScript(
        version=data["version"],
        job_id=data["job_id"],
        reading_direction=data["reading_direction"],
        base_seed=base_seed,
        pages=pages,
    )
