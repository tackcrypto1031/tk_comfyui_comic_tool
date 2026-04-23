import numpy as np

from tk_comfyui_batch_image.core.sampler_runner import SamplerBackend, run_panel_sampler
from tk_comfyui_batch_image.core.types import SolvedPanel


class FakeBackend(SamplerBackend):
    """Deterministic backend: returns a solid grey image of requested size."""

    def __init__(self):
        self.calls = []

    def encode(self, clip, text):
        self.calls.append(("encode", text))
        return ("COND", text)

    def empty_latent(self, width, height, batch_size=1):
        self.calls.append(("latent", width, height))
        return {"w": width, "h": height, "bs": batch_size}

    def sample(self, model, seed, steps, cfg, sampler_name, scheduler,
               cond_pos, cond_neg, latent, denoise):
        self.calls.append(("sample", seed, steps, cfg))
        return latent

    def vae_decode(self, vae, samples):
        self.calls.append(("decode",))
        # return (H, W, 3) float32 0~1 grey image
        h, w = samples["h"], samples["w"]
        img = np.full((h, w, 3), 0.5, dtype=np.float32)
        return img


def _panel(**overrides) -> SolvedPanel:
    base = dict(
        page_index=1, panel_index=1, global_index=0,
        positive_prompt="pos", negative_prompt="neg",
        width_px=64, height_px=48,
        bbox_topleft=(0, 0), bbox_size=(64, 48),
        align="center", shape_type="rect",
        polygon_local=None, polygon_abs=None,
        seed=99,
        sampler={"sampler_name": "euler", "scheduler": "normal",
                 "steps": 10, "cfg": 7.0, "denoise": 1.0},
        border={"width_px": 0, "color": "#000000", "style": "solid"},
    )
    base.update(overrides)
    return SolvedPanel(**base)


def test_run_panel_sampler_calls_backend_in_order():
    b = FakeBackend()
    img = run_panel_sampler(b, model="M", clip="C", vae="V", panel=_panel())
    kinds = [c[0] for c in b.calls]
    assert kinds == ["encode", "encode", "latent", "sample", "decode"]
    assert img.shape == (48, 64, 3)
    assert img.dtype == np.float32


def test_run_panel_sampler_passes_seed_and_steps():
    b = FakeBackend()
    run_panel_sampler(b, model="M", clip="C", vae="V",
                      panel=_panel(seed=12345,
                                   sampler={"sampler_name": "dpmpp_2m", "scheduler": "karras",
                                            "steps": 30, "cfg": 8.5, "denoise": 1.0}))
    sample_call = next(c for c in b.calls if c[0] == "sample")
    assert sample_call == ("sample", 12345, 30, 8.5)


def test_run_panel_sampler_requests_correct_latent_size():
    b = FakeBackend()
    run_panel_sampler(b, model="M", clip="C", vae="V",
                      panel=_panel(width_px=128, height_px=96, bbox_size=(128, 96)))
    latent_call = next(c for c in b.calls if c[0] == "latent")
    assert latent_call == ("latent", 128, 96)
