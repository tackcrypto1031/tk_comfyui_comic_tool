"""Backend-agnostic sampler runner.

The real ComfyUI backend is wired up in `nodes/batch_generator.py`; tests inject
a fake backend for deterministic unit tests.
"""
from __future__ import annotations

from typing import Protocol

import numpy as np

from .types import SolvedPanel


class SamplerBackend(Protocol):
    def encode(self, clip, text: str): ...
    def empty_latent(self, width: int, height: int, batch_size: int = 1): ...
    def sample(self, model, seed: int, steps: int, cfg: float,
               sampler_name: str, scheduler: str,
               cond_pos, cond_neg, latent, denoise: float): ...
    def vae_decode(self, vae, samples) -> np.ndarray: ...


def run_panel_sampler(
    backend: SamplerBackend,
    *,
    model,
    clip,
    vae,
    panel: SolvedPanel,
) -> np.ndarray:
    """Run the full CLIP→KSampler→VAE decode pipeline for one panel.

    Returns an (H, W, 3) float32 image in [0, 1] at exactly `panel.bbox_size`.

    SD/SDXL latents operate at 1/8 resolution, so the VAE always decodes at
    dimensions that are multiples of 8. We round the sampling size UP to the
    nearest multiple of 8 and crop the decoded image back to the exact panel
    size — otherwise panels whose width/height aren't divisible by 8 come out
    1–7 px short and get silently replaced with the red-X placeholder by the
    batch generator's failure path.
    """
    cond_pos = backend.encode(clip, panel.positive_prompt)
    cond_neg = backend.encode(clip, panel.negative_prompt)
    w, h = panel.bbox_size
    gen_w = ((w + 7) // 8) * 8
    gen_h = ((h + 7) // 8) * 8
    latent = backend.empty_latent(gen_w, gen_h, batch_size=1)
    s = panel.sampler
    samples = backend.sample(
        model, panel.seed, s["steps"], s["cfg"],
        s["sampler_name"], s["scheduler"],
        cond_pos, cond_neg, latent, s["denoise"],
    )
    img = backend.vae_decode(vae, samples)
    if img.ndim != 3 or img.shape[2] != 3:
        raise RuntimeError(
            f"vae_decode returned shape {img.shape}, expected (H, W, 3)"
        )
    if img.shape[0] < h or img.shape[1] < w:
        raise RuntimeError(
            f"vae_decode returned shape {img.shape}, "
            f"expected at least ({h}, {w}, 3)"
        )
    return img[:h, :w, :]
