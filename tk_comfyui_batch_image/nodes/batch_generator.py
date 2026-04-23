"""ComicBatchGenerator — inner for-loop that generates every panel."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from ..core.cache_manager import manifest_matches, panel_hash, panel_paths, write_manifest
from ..core.sampler_runner import SamplerBackend, run_panel_sampler
from ..core.types import COMIC_SCRIPT_TYPE, SolvedPanel, SolvedScript


def _arr_to_pil(arr: np.ndarray) -> Image.Image:
    arr_u8 = np.clip(arr * 255.0, 0, 255).astype(np.uint8) if arr.dtype != np.uint8 else arr
    return Image.fromarray(arr_u8, mode="RGB")


def _pil_to_arr(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    return arr


def _red_x(w: int, h: int) -> np.ndarray:
    arr = np.full((h, w, 3), 1.0, dtype=np.float32)
    # crude X in red
    for i in range(min(w, h)):
        arr[i, i] = [1.0, 0.0, 0.0]
        arr[i, w - 1 - i if w - 1 - i >= 0 else 0] = [1.0, 0.0, 0.0]
    return arr


class _ComfyUIBackend(SamplerBackend):
    """Thin adapter around ComfyUI's built-in nodes. Imported lazily."""

    def __init__(self):
        import nodes as comfy_nodes  # type: ignore
        self._enc = comfy_nodes.CLIPTextEncode()
        self._ks  = comfy_nodes.KSampler()
        self._el  = comfy_nodes.EmptyLatentImage()
        self._vd  = comfy_nodes.VAEDecode()

    def encode(self, clip, text):
        return self._enc.encode(clip, text)[0]

    def empty_latent(self, width, height, batch_size=1):
        return self._el.generate(width, height, batch_size)[0]

    def sample(self, model, seed, steps, cfg, sampler_name, scheduler,
               cond_pos, cond_neg, latent, denoise):
        return self._ks.sample(model, seed, steps, cfg, sampler_name, scheduler,
                               cond_pos, cond_neg, latent, denoise)[0]

    def vae_decode(self, vae, samples):
        img_tensor = self._vd.decode(vae, samples)[0]  # (N, H, W, 3) float 0~1
        return img_tensor[0].cpu().numpy()


class ComicBatchGenerator:
    """Generate every panel in a script using an internal for-loop."""

    CATEGORY = "comic/core"
    FUNCTION = "generate"
    RETURN_TYPES = ("IMAGE", COMIC_SCRIPT_TYPE, "STRING")
    RETURN_NAMES = ("generated_panels", "comic_script", "generation_log")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "comic_script": (COMIC_SCRIPT_TYPE,),
                "model":        ("MODEL",),
                "clip":         ("CLIP",),
                "vae":          ("VAE",),
                "sampler_name": ("STRING", {"default": "euler"}),
                "scheduler":    ("STRING", {"default": "normal"}),
                "steps":        ("INT",    {"default": 25, "min": 1, "max": 200}),
                "cfg":          ("FLOAT",  {"default": 7.0, "min": 0.0, "max": 30.0, "step": 0.1}),
                "denoise":      ("FLOAT",  {"default": 1.0, "min": 0.0, "max": 1.0,  "step": 0.01}),
                "on_failure":   (["retry_then_skip", "halt"], {"default": "retry_then_skip"}),
                "retries":      ("INT",    {"default": 2, "min": 0, "max": 10}),
            },
            "optional": {
                "positive_suffix": ("STRING", {"default": "", "multiline": True}),
                "negative_suffix": ("STRING", {"default": "", "multiline": True}),
            },
        }

    def _resolve_out_dir(self, job_id: str, override: Path | None = None) -> Path:
        if override is not None:
            d = Path(override) / "comics" / job_id
        else:
            import folder_paths  # type: ignore
            d = Path(folder_paths.get_output_directory()) / "comics" / job_id
        (d / "panels").mkdir(parents=True, exist_ok=True)
        return d

    def _merge_widget_defaults(self, panel: SolvedPanel, widget: dict) -> SolvedPanel:
        """Apply widget-level sampler defaults when the script didn't specify.

        The normalizer already filled defaults from `default_sampler` in the
        JSON; the node-level widgets act as a LOWEST-priority fallback only if
        the JSON default_sampler is missing a key — which the schema forbids,
        so in practice this is a no-op. Implemented for safety.
        """
        merged = {**widget, **panel.sampler}
        panel.sampler = merged
        return panel

    def generate(
        self, comic_script: SolvedScript, model, clip, vae,
        sampler_name, scheduler, steps, cfg, denoise,
        on_failure, retries,
        positive_suffix: str = "", negative_suffix: str = "",
        _backend: SamplerBackend | None = None,
        _out_dir: Path | None = None,
    ):
        backend = _backend if _backend is not None else _ComfyUIBackend()
        out_dir = self._resolve_out_dir(comic_script.job_id, _out_dir)
        widget_defaults = {
            "sampler_name": sampler_name, "scheduler": scheduler,
            "steps": steps, "cfg": cfg, "denoise": denoise,
        }

        log_lines: list[str] = []
        images: list[np.ndarray] = []
        total_panels = sum(len(p.panels) for p in comic_script.pages)
        done = 0

        for page in comic_script.pages:
            for panel in page.panels:
                panel = self._merge_widget_defaults(panel, widget_defaults)
                if positive_suffix.strip():
                    panel.positive_prompt = (
                        f"{panel.positive_prompt}, {positive_suffix.strip()}"
                        if panel.positive_prompt else positive_suffix.strip()
                    )
                if negative_suffix.strip():
                    panel.negative_prompt = (
                        f"{panel.negative_prompt}, {negative_suffix.strip()}"
                        if panel.negative_prompt else negative_suffix.strip()
                    )

                paths = panel_paths(out_dir, panel)
                done += 1
                tag = f"[page {panel.page_index:02d}/{len(comic_script.pages):02d}] panel {panel.panel_index:02d} ({done}/{total_panels})"

                if manifest_matches(paths.manifest, panel):
                    img = _pil_to_arr(Image.open(paths.image))
                    log_lines.append(f"{tag} ... cached")
                    images.append(img)
                    continue

                img: np.ndarray | None = None
                last_err: BaseException | None = None
                for attempt in range(1 + retries):
                    t0 = time.time()
                    try:
                        img = run_panel_sampler(backend, model=model, clip=clip, vae=vae, panel=panel)
                        log_lines.append(f"{tag} ... generated ({time.time() - t0:.1f}s)"
                                         + (f" retry#{attempt}" if attempt else ""))
                        break
                    except Exception as e:   # noqa: BLE001
                        last_err = e
                        log_lines.append(f"{tag} ... FAILED attempt {attempt + 1}: {e}")
                        continue

                if img is None:
                    if on_failure == "halt":
                        raise RuntimeError(f"panel generation failed: {tag}") from last_err
                    # retry_then_skip
                    img = _red_x(*panel.bbox_size)
                    log_lines.append(f"{tag} ... skipped with placeholder")
                    images.append(img)
                    continue

                _arr_to_pil(img).save(paths.image, format="PNG")
                write_manifest(paths.manifest, panel_hash(panel))
                images.append(img)

        # Pad all images to the same (max_h, max_w) so np.stack works when
        # panels have different heights (e.g. basic.json has 200px and 400px panels).
        max_h = max(img.shape[0] for img in images)
        max_w = max(img.shape[1] for img in images)
        padded = []
        for img in images:
            h, w = img.shape[:2]
            if h == max_h and w == max_w:
                padded.append(img.astype(np.float32))
            else:
                pad = np.ones((max_h, max_w, 3), dtype=np.float32)  # white padding
                pad[:h, :w, :] = img.astype(np.float32)
                padded.append(pad)
        stacked = torch.from_numpy(np.stack(padded, axis=0)).float()
        return stacked, comic_script, "\n".join(log_lines)
