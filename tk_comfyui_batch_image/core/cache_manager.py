"""Panel-hash-based cache: compute stable hash, read/write manifest, detect stale."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .types import SolvedPanel

MANIFEST_VERSION = 1
"""Bump when the panel_hash input schema or manifest layout changes in a way
that invalidates older caches. manifest_matches() treats version mismatch as
a miss so stale manifests are regenerated safely."""


@dataclass(frozen=True)
class PanelPaths:
    image: Path
    manifest: Path


def panel_hash(panel: SolvedPanel) -> str:
    """Stable SHA256 over the fields that determine the generated image.

    Deliberately excludes bbox_topleft (affects composition, not pixels).
    """
    payload = {
        "positive_prompt": panel.positive_prompt,
        "negative_prompt": panel.negative_prompt,
        "width_px":  panel.width_px,
        "height_px": panel.height_px,
        "seed": panel.seed,
        "sampler": dict(sorted(panel.sampler.items())),
        "shape_type": panel.shape_type,
        "polygon_local": panel.polygon_local,
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def panel_paths(out_dir: Path, panel: SolvedPanel) -> PanelPaths:
    panels_dir = Path(out_dir) / "panels"
    stem = f"p{panel.page_index:03d}_{panel.panel_index:02d}"
    return PanelPaths(
        image=panels_dir / f"{stem}.png",
        manifest=panels_dir / f"{stem}.json",
    )


def write_manifest(path: Path, hash_hex: str, extra: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"manifest_version": MANIFEST_VERSION, "hash": hash_hex}
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_matches(manifest_path: Path, panel: SolvedPanel) -> bool:
    if not manifest_path.exists():
        return False
    try:
        m = read_manifest(manifest_path)
    except (OSError, json.JSONDecodeError):
        return False
    # Older manifests without the version field are treated as stale —
    # hash semantics may have shifted between releases.
    if m.get("manifest_version") != MANIFEST_VERSION:
        return False
    return m.get("hash") == panel_hash(panel)
