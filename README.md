# tk_comfyui_batch_image

**ComfyUI custom node set for batch comic-page generation from an AI-authored JSON script.**

Write a natural-language screenplay → an AI (acting as a manga panel composition expert) turns it into a JSON → this node runs every panel through your ComfyUI model/CLIP/VAE and composes the pages.

---

## Install

Clone this repo into `ComfyUI/custom_nodes/`:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/tackcrypto1031/tk_comfyui_comic_tool.git
cd tk_comfyui_comic_tool
pip install Pillow jsonschema numpy
```

Restart ComfyUI. Four nodes appear under the `comic/` category.

## Nodes

| Node | Category | Purpose |
|---|---|---|
| **Comic Script Loader** | `comic/io` | Load + validate JSON (Layer 1 schema + Layer 2 semantic); emits `COMIC_SCRIPT`. Modes: `file` / `path` / `inline`. |
| **Comic Sampler Override** | `comic/util` | Optional. Plug between loader and generator to temporarily override cfg / steps / sampler from node widgets without editing the JSON. Leave all widgets at sentinel (`(keep)` / `0` / `0.0` / `-1.0`) for passthrough. |
| **Comic Batch Generator** | `comic/core` | Inner for-loop. Connect `MODEL` / `CLIP` / `VAE`; no external `KSampler` needed. Panel-hash cache → modifying one panel's prompt only re-runs that panel on next queue. Retry + skip policy configurable. |
| **Comic Page Composer** | `comic/io` | Assemble panels into full pages. Outputs composed `IMAGE` batch + bbox metadata (JSON) + pass-through panels. |

## AI skill pack

The [`docs/skills/comic-script-authoring/`](docs/skills/comic-script-authoring/) folder is a ready-to-use delivery for three audiences:

| Audience | Entry point |
|---|---|
| Claude Code + superpowers users | copy `SKILL.md` into your skills dir; invoke via `/skill comic-script-authoring` |
| Generic LLM (ChatGPT / Gemini / Claude API / …) | paste `PROMPT_TEMPLATE.md` into the system prompt |
| Humans reading about the tool | read `README.md` in that folder |

The `schema.json` is generated from `tk_comfyui_batch_image/core/schema.py` (single source of truth) and is referenced by all three audiences instead of duplicating field tables.

The `examples/` subdirectory has 5 `screenplay.md` + `output.json` pairs covering minimal, multi-panel with align, per-panel sampler_override, rtl reading direction, and 4-layer prompt composition.

## Standalone validator CLI

The AI (or you) can self-check a JSON without running ComfyUI:

```bash
python -m tk_comfyui_batch_image.validate my_script.json
python -m tk_comfyui_batch_image.validate my_script.json --json      # machine-readable
python -m tk_comfyui_batch_image.validate examples/*.json --max-errors 5
```

Exit codes: `0` all pass · `1` validation failed · `2` CLI usage error · `3` I/O error.

## Example workflow

1. Write a screenplay (Markdown or plain text).
2. Give it to your AI along with `docs/skills/comic-script-authoring/SKILL.md` (or `PROMPT_TEMPLATE.md`).
3. AI outputs a JSON and (if it can run shells) self-validates via the CLI.
4. Drop the JSON into a ComfyUI workflow:
   `ComicScriptLoader` → (optional `ComicSamplerOverride`) → `ComicBatchGenerator` → `ComicPageComposer`.
5. Queue.

A starter ComfyUI workflow lives at [`tk_comfyui_batch_image/examples/workflows/m1_basic_vertical_stack.json`](tk_comfyui_batch_image/examples/workflows/m1_basic_vertical_stack.json). Drop it into the ComfyUI canvas.

Put the JSON script at `ComfyUI/input/comics/your_script.json` and set `ComicScriptLoader` to `file` mode.

## Running tests

```bash
pytest tk_comfyui_batch_image/tests/ -q           # 117 tests
ruff check tk_comfyui_batch_image
```

## Current capabilities

- Rectangle panels (`shape.type="rect"`)
- Vertical-stack layout (`layout_mode="vertical_stack"`)
- 4-layer prompt composition (style + character + page + scene) + per-panel `sampler_override`
- Reading direction `ltr` / `rtl`
- Panel-hash cache + resume
- `retry_then_skip` / `halt` failure policies (placeholder PNG + manifest persisted on skip)
- Layer 1 + Layer 2 JSON validation (schema + semantic rules: index continuity, layout fit, dimensional consistency)
- AI skill pack with default canvas (1080 × 1920) and panel-size guidance table

## Not yet supported

- Diagonal split panels (`shape.type="split"` + sister-panel coline) — planned for M3
- Arbitrary polygon panels (`shape.type="polygon"`) — M4
- Webtoon long-page + per-page size + debug overlay + streaming decode — M5

## License

MIT.
