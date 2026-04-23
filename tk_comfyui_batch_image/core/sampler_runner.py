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

    Returns an (H, W, 3) float32 image in [0, 1].
    """
    cond_pos = backend.encode(clip, panel.positive_prompt)
    cond_neg = backend.encode(clip, panel.negative_prompt)
    w, h = panel.bbox_size
    latent = backend.empty_latent(w, h, batch_size=1)
    s = panel.sampler
    samples = backend.sample(
        model, panel.seed, s["steps"], s["cfg"],
        s["sampler_name"], s["scheduler"],
        cond_pos, cond_neg, latent, s["denoise"],
    )
    img = backend.vae_decode(vae, samples)
    return img
