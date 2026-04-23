"""End-to-end: loader → generator → composer with the basic.json fixture."""
from pathlib import Path

import numpy as np
import torch

from tk_comfyui_batch_image.core.sampler_runner import SamplerBackend
from tk_comfyui_batch_image.nodes.batch_generator import ComicBatchGenerator
from tk_comfyui_batch_image.nodes.page_composer import ComicPageComposer
from tk_comfyui_batch_image.nodes.script_loader import ComicScriptLoader

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


class GreyBackend(SamplerBackend):
    def encode(self, clip, text):
        return ("c", text)

    def empty_latent(self, w, h, batch_size=1):
        return {"w": w, "h": h}

    def sample(self, model, seed, steps, cfg, sampler_name, scheduler,
               cond_pos, cond_neg, latent, denoise):
        return latent

    def vae_decode(self, vae, samples):
        h, w = samples["h"], samples["w"]
        return np.full((h, w, 3), 0.5, dtype=np.float32)


def test_full_pipeline_basic_script(tmp_path: Path):
    loader = ComicScriptLoader()
    text = (FIXTURES / "basic.json").read_text(encoding="utf-8")
    script, summary = loader.load(mode="inline", json_text=text,
                                  json_file="", json_path="")

    gen = ComicBatchGenerator()
    panels, pass_script, log = gen.generate(
        comic_script=script, model="M", clip="C", vae="V",
        on_failure="halt", max_attempts=1,
        positive_suffix="", negative_suffix="",
        _backend=GreyBackend(), _out_dir=tmp_path,
    )

    composer = ComicPageComposer()
    pages, bboxes_json, pass_panels = composer.compose(
        generated_panels=panels, comic_script=pass_script, debug_overlay=False,
    )

    # 2 pages of same size
    assert pages.shape[0] == 2
    # all panels generated
    assert panels.shape[0] == 4
    # rerun without changes → everything cached
    gen2 = ComicBatchGenerator()
    panels2, _, log2 = gen2.generate(
        comic_script=script, model="M", clip="C", vae="V",
        on_failure="halt", max_attempts=1,
        positive_suffix="", negative_suffix="",
        _backend=GreyBackend(), _out_dir=tmp_path,
    )
    assert "cached" in log2
    # PNG round-trip introduces ≤1/255 quantisation; use atol accordingly
    assert torch.allclose(panels, panels2, atol=1.0 / 255)
