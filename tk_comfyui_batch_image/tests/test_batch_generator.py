import json
from pathlib import Path

import numpy as np
import pytest
import torch

from tk_comfyui_batch_image.core.normalizer import normalize_script
from tk_comfyui_batch_image.core.sampler_runner import SamplerBackend
from tk_comfyui_batch_image.nodes.batch_generator import ComicBatchGenerator

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


class RecordingBackend(SamplerBackend):
    """Deterministic grey-image backend that records every call."""

    def __init__(self):
        self.n_sample_calls = 0

    def encode(self, clip, text): return ("c", text)
    def empty_latent(self, w, h, batch_size=1):
        return {"w": w, "h": h}
    def sample(self, model, seed, steps, cfg, sampler_name, scheduler,
               cond_pos, cond_neg, latent, denoise):
        self.n_sample_calls += 1
        return latent
    def vae_decode(self, vae, samples):
        h, w = samples["h"], samples["w"]
        return np.full((h, w, 3), 0.5, dtype=np.float32)


def _gen(node, script, backend, out_dir, on_failure="halt"):
    return node.generate(
        comic_script=script, model="M", clip="C", vae="V",
        positive_suffix="", negative_suffix="",
        sampler_name="euler", scheduler="normal", steps=10, cfg=7.0, denoise=1.0,
        on_failure=on_failure, retries=1,
        _backend=backend, _out_dir=out_dir,
    )


def test_generator_returns_image_tensor_for_all_panels(tmp_path: Path):
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    backend = RecordingBackend()
    images, pass_script, log = _gen(ComicBatchGenerator(), script, backend, tmp_path)
    assert isinstance(images, torch.Tensor)
    assert images.dim() == 4 and images.shape[-1] == 3   # (N, H, W, 3)
    assert images.shape[0] == 4   # 3 panels in page 1 + 1 in page 2
    assert backend.n_sample_calls == 4


def test_generator_cache_skips_when_hash_matches(tmp_path: Path):
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    backend1 = RecordingBackend()
    _gen(ComicBatchGenerator(), script, backend1, tmp_path)
    assert backend1.n_sample_calls == 4

    backend2 = RecordingBackend()
    _gen(ComicBatchGenerator(), script, backend2, tmp_path)
    assert backend2.n_sample_calls == 0   # all cached


def test_generator_invalidates_cache_when_prompt_changes(tmp_path: Path):
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    _gen(ComicBatchGenerator(), script, RecordingBackend(), tmp_path)

    # modify a prompt in one panel
    data["pages"][0]["panels"][1]["scene_prompt"]["positive"] = "CHANGED"
    script2 = normalize_script(data)
    backend = RecordingBackend()
    _gen(ComicBatchGenerator(), script2, backend, tmp_path)
    assert backend.n_sample_calls == 1   # only the changed panel


class FlakyBackend(RecordingBackend):
    def __init__(self, fail_on_panel: int, fail_times: int):
        super().__init__()
        self.fail_on = fail_on_panel
        self.fail_times = fail_times
        self.panel_seen = -1

    def sample(self, *args, **kwargs):
        self.panel_seen += 1
        if self.panel_seen == self.fail_on and self.fail_times > 0:
            self.fail_times -= 1
            self.panel_seen -= 1      # retry counts same panel
            raise RuntimeError("boom")
        return super().sample(*args, **kwargs)


def test_retry_then_skip_mode_tolerates_transient_failure(tmp_path: Path):
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    backend = FlakyBackend(fail_on_panel=1, fail_times=1)
    images, _, log = _gen(ComicBatchGenerator(), script, backend, tmp_path,
                          on_failure="retry_then_skip")
    assert images.shape[0] == 4
    assert "retry" in log.lower()


def test_halt_mode_raises_on_failure(tmp_path: Path):
    data = json.loads((FIXTURES / "basic.json").read_text(encoding="utf-8"))
    script = normalize_script(data)
    backend = FlakyBackend(fail_on_panel=0, fail_times=5)
    with pytest.raises(RuntimeError):
        _gen(ComicBatchGenerator(), script, backend, tmp_path, on_failure="halt")
