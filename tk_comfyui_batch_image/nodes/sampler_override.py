"""ComicSamplerOverride — runtime sampler-param tweak node.

Insert between ComicScriptLoader and ComicBatchGenerator when you want to
experiment with cfg / steps / sampler without editing the JSON. Any widget
left at its sentinel value is ignored; non-sentinel widgets overwrite every
panel's sampler entry, including panels that had per-panel sampler_override
in the JSON (the node is 'most recent user intent').

No widget inserted (just don't add the node) = JSON is single source of truth.
"""
from __future__ import annotations

import dataclasses

from ..core.types import COMIC_SCRIPT_TYPE, SolvedScript

KEEP_STR = "(keep)"

SAMPLER_NAMES = [
    KEEP_STR,
    "euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral",
    "lms", "dpm_fast", "dpm_adaptive",
    "dpmpp_2s_ancestral", "dpmpp_sde",
    "dpmpp_2m", "dpmpp_2m_sde", "dpmpp_3m_sde",
    "ddim", "uni_pc", "uni_pc_bh2",
]
SCHEDULERS = [
    KEEP_STR,
    "normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform",
]


class ComicSamplerOverride:
    CATEGORY = "comic/util"
    FUNCTION = "apply"
    RETURN_TYPES = (COMIC_SCRIPT_TYPE,)
    RETURN_NAMES = ("comic_script",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "comic_script": (COMIC_SCRIPT_TYPE,),
                "sampler_name": (SAMPLER_NAMES, {"default": KEEP_STR}),
                "scheduler":    (SCHEDULERS,    {"default": KEEP_STR}),
                # Sentinels: steps=0, cfg=0.0, denoise=-1.0 mean "don't override".
                "steps":        ("INT",   {"default": 0,    "min": 0,    "max": 200}),
                "cfg":          ("FLOAT", {"default": 0.0,  "min": 0.0,  "max": 30.0, "step": 0.1}),
                "denoise":      ("FLOAT", {"default": -1.0, "min": -1.0, "max": 1.0,  "step": 0.01}),
            },
        }

    def apply(
        self, comic_script: SolvedScript,
        sampler_name: str, scheduler: str,
        steps: int, cfg: float, denoise: float,
    ):
        overrides: dict = {}
        if sampler_name != KEEP_STR:
            overrides["sampler_name"] = sampler_name
        if scheduler != KEEP_STR:
            overrides["scheduler"] = scheduler
        if steps > 0:
            overrides["steps"] = steps
        if cfg > 0.0:
            overrides["cfg"] = cfg
        if 0.0 <= denoise <= 1.0:
            overrides["denoise"] = denoise

        if not overrides:
            return (comic_script,)

        new_pages = []
        for page in comic_script.pages:
            new_panels = [
                dataclasses.replace(p, sampler={**p.sampler, **overrides})
                for p in page.panels
            ]
            new_pages.append(dataclasses.replace(page, panels=new_panels))
        return (dataclasses.replace(comic_script, pages=new_pages),)
