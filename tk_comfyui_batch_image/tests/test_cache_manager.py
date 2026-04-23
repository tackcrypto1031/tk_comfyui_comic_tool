# tests/test_cache_manager.py
from pathlib import Path

from tk_comfyui_batch_image.core.cache_manager import (
    manifest_matches,
    panel_hash,
    panel_paths,
    read_manifest,
    write_manifest,
)
from tk_comfyui_batch_image.core.types import SolvedPanel


def _panel(**overrides) -> SolvedPanel:
    base = dict(
        page_index=1, panel_index=1, global_index=0,
        positive_prompt="a", negative_prompt="b",
        width_px=100, height_px=80,
        bbox_topleft=(10, 10), bbox_size=(100, 80),
        align="center", shape_type="rect",
        polygon_local=None, polygon_abs=None,
        seed=42,
        sampler={"sampler_name": "euler", "scheduler": "normal",
                 "steps": 25, "cfg": 7.0, "denoise": 1.0},
        border={"width_px": 3, "color": "#000000", "style": "solid"},
    )
    base.update(overrides)
    return SolvedPanel(**base)


def test_hash_is_deterministic():
    a = panel_hash(_panel())
    b = panel_hash(_panel())
    assert a == b
    assert len(a) == 64   # sha256 hex


def test_hash_changes_when_prompt_changes():
    a = panel_hash(_panel(positive_prompt="a"))
    b = panel_hash(_panel(positive_prompt="b"))
    assert a != b


def test_hash_changes_when_seed_changes():
    assert panel_hash(_panel(seed=1)) != panel_hash(_panel(seed=2))


def test_hash_changes_when_sampler_changes():
    s2 = {"sampler_name": "euler", "scheduler": "normal",
          "steps": 99, "cfg": 7.0, "denoise": 1.0}
    assert panel_hash(_panel()) != panel_hash(_panel(sampler=s2))


def test_hash_independent_of_bbox_topleft():
    # bbox position changes when gutter changes, but image content doesn't depend on it
    assert panel_hash(_panel(bbox_topleft=(0, 0))) == panel_hash(_panel(bbox_topleft=(50, 50)))


def test_panel_paths(tmp_path: Path):
    paths = panel_paths(tmp_path, _panel(page_index=3, panel_index=12))
    assert paths.image.name == "p003_12.png"
    assert paths.manifest.name == "p003_12.json"
    assert paths.image.parent == tmp_path / "panels"


def test_write_then_read_manifest_roundtrip(tmp_path: Path):
    p = _panel()
    paths = panel_paths(tmp_path, p)
    paths.image.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(paths.manifest, panel_hash(p), extra={"elapsed_s": 3.2})
    m = read_manifest(paths.manifest)
    assert m["hash"] == panel_hash(p)
    assert m["elapsed_s"] == 3.2


def test_manifest_matches_true(tmp_path: Path):
    p = _panel()
    paths = panel_paths(tmp_path, p)
    paths.image.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(paths.manifest, panel_hash(p))
    assert manifest_matches(paths.manifest, p) is True


def test_manifest_matches_false_when_prompt_changed(tmp_path: Path):
    p = _panel()
    paths = panel_paths(tmp_path, p)
    paths.image.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(paths.manifest, panel_hash(p))
    p2 = _panel(positive_prompt="different")
    assert manifest_matches(paths.manifest, p2) is False


def test_manifest_matches_false_when_no_file(tmp_path: Path):
    p = _panel()
    paths = panel_paths(tmp_path, p)
    assert manifest_matches(paths.manifest, p) is False


def test_manifest_matches_false_when_version_mismatch(tmp_path: Path):
    """Manifests from older releases (or manifests with no version) are stale
    — the panel_hash input schema may have shifted and we must re-render."""
    import json as _json

    p = _panel()
    paths = panel_paths(tmp_path, p)
    paths.image.parent.mkdir(parents=True, exist_ok=True)
    # Simulate a legacy manifest: correct hash but no manifest_version.
    paths.manifest.write_text(_json.dumps({"hash": panel_hash(p)}), encoding="utf-8")
    assert manifest_matches(paths.manifest, p) is False


def test_write_manifest_includes_version(tmp_path: Path):
    p = _panel()
    paths = panel_paths(tmp_path, p)
    paths.image.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(paths.manifest, panel_hash(p))
    m = read_manifest(paths.manifest)
    assert m["manifest_version"] == 1
