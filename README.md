# tk_comfyui_batch_image

ComfyUI custom node set for batch comic-page generation from a JSON script.

**Status:** M1 — Rectangle vertical-stack. See `docs/superpowers/specs/2026-04-23-comfyui-comic-batch-node-design.md` for the full design; `docs/superpowers/plans/` for milestones.

## Install

Clone this repo into `ComfyUI/custom_nodes/`, then:

    pip install -e .[dev]

Restart ComfyUI.

## Nodes

| Node | Purpose |
|---|---|
| `Comic Script Loader` | Load + validate JSON; emits `COMIC_SCRIPT`. Modes: `file` / `path` / `inline`. |
| `Comic Batch Generator` | Inner for-loop over panels. Connect `MODEL / CLIP / VAE`; no KSampler needed. Supports resume via panel-hash cache. |
| `Comic Page Composer` | Assemble panels into full pages. Outputs composed IMAGE batch + bbox metadata + pass-through panels. |

## Example workflow

Drop `examples/workflows/m1_basic_vertical_stack.json` into ComfyUI.
Place `basic.json` (see `tests/fixtures/scripts/`) at `ComfyUI/input/comics/basic.json`.

## Running tests

    pytest tk_comfyui_batch_image/tests/ -v
    ruff check tk_comfyui_batch_image

## Current limitations (M1)

- Shapes: rectangle only (no `split` / `polygon` yet → M3/M4)
- Layout modes: `vertical_stack` only (no `custom_grid` yet → M3)
- No debug overlay (→ M5)
- No standalone JSON-validation CLI (→ M2)
- No SKILL.md skill package for AI script generation (→ M2)
