"""Tests for ComicSamplerOverride — runtime sampler tweak node."""
import json
from pathlib import Path

from tk_comfyui_batch_image.core.normalizer import normalize_script
from tk_comfyui_batch_image.nodes.sampler_override import (
    KEEP_STR,
    ComicSamplerOverride,
)

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


def _basic_script():
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    return data, normalize_script(data)


def _all_panels(script):
    return [p for page in script.pages for p in page.panels]


def test_passthrough_when_all_sentinels():
    _, script = _basic_script()
    before = [dict(p.sampler) for p in _all_panels(script)]
    (out,) = ComicSamplerOverride().apply(
        comic_script=script,
        sampler_name=KEEP_STR, scheduler=KEEP_STR,
        steps=0, cfg=0.0, denoise=-1.0,
    )
    after = [dict(p.sampler) for p in _all_panels(out)]
    assert before == after


def test_cfg_override_applies_to_every_panel():
    _, script = _basic_script()
    (out,) = ComicSamplerOverride().apply(
        comic_script=script,
        sampler_name=KEEP_STR, scheduler=KEEP_STR,
        steps=0, cfg=9.5, denoise=-1.0,
    )
    for p in _all_panels(out):
        assert p.sampler["cfg"] == 9.5
    # Other keys untouched
    orig = _all_panels(script)
    for src, dst in zip(orig, _all_panels(out), strict=False):
        assert src.sampler["steps"] == dst.sampler["steps"]
        assert src.sampler["sampler_name"] == dst.sampler["sampler_name"]


def test_does_not_mutate_input_script():
    _, script = _basic_script()
    before = [dict(p.sampler) for p in _all_panels(script)]
    ComicSamplerOverride().apply(
        comic_script=script,
        sampler_name="dpmpp_2m", scheduler="karras",
        steps=40, cfg=8.0, denoise=0.9,
    )
    after = [dict(p.sampler) for p in _all_panels(script)]
    assert before == after, "apply() mutated the input script"


def test_override_wins_over_per_panel_sampler_override():
    """Book-level per-panel sampler_override is normalized into panel.sampler.
    The override node must replace it (it's the 'most recent' user intent)."""
    data, _ = _basic_script()
    # basic.json's page 2 panel 1 already has sampler_override (steps=30, cfg=8.0)
    script = normalize_script(data)
    pre = [p.sampler for p in _all_panels(script)
           if p.page_index == 2 and p.panel_index == 1][0]
    assert pre["steps"] == 30   # sanity check on fixture

    (out,) = ComicSamplerOverride().apply(
        comic_script=script,
        sampler_name=KEEP_STR, scheduler=KEEP_STR,
        steps=15, cfg=0.0, denoise=-1.0,
    )
    post = [p.sampler for p in _all_panels(out)
            if p.page_index == 2 and p.panel_index == 1][0]
    assert post["steps"] == 15   # override wins
    assert post["cfg"] == 8.0    # cfg not overridden, keeps panel's existing


def test_mixed_overrides_preserve_unset_keys():
    _, script = _basic_script()
    orig_sampler = _all_panels(script)[0].sampler.copy()
    (out,) = ComicSamplerOverride().apply(
        comic_script=script,
        sampler_name="dpmpp_2m", scheduler=KEEP_STR,
        steps=0, cfg=5.5, denoise=-1.0,
    )
    new_sampler = _all_panels(out)[0].sampler
    assert new_sampler["sampler_name"] == "dpmpp_2m"
    assert new_sampler["cfg"] == 5.5
    assert new_sampler["scheduler"] == orig_sampler["scheduler"]
    assert new_sampler["steps"] == orig_sampler["steps"]
    assert new_sampler["denoise"] == orig_sampler["denoise"]
