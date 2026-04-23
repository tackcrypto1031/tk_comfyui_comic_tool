# Comic Script Authoring Skill Pack

This directory ships everything an AI or human needs to turn a natural-language
screenplay into a JSON that drives the `tk_comfyui_batch_image` ComfyUI node.

The target audience of this README is **humans using the tool** (not AIs
producing JSON — those read `SKILL.md` or `PROMPT_TEMPLATE.md`).

## End-to-end flow

```
[You write a natural-language screenplay]
        ↓
[Your AI (Claude Code / ChatGPT / Gemini / …) reads the screenplay
 + SKILL.md or PROMPT_TEMPLATE.md]
        ↓
[AI outputs JSON]
        ↓
[AI (or you) runs `python -m tk_comfyui_batch_image.validate out.json`]
        ↓
[Drop the JSON into a ComfyUI workflow → ComicScriptLoader → ComicBatchGenerator]
        ↓
[Images]
```

## Three integration paths

### 1. Claude Code + superpowers

Copy `SKILL.md` to `~/.claude/skills/comic-script-authoring/SKILL.md` or your
project's skill directory. Then invoke it: *"Here's my screenplay — please
produce a comic JSON using the comic-script-authoring skill."*

Claude will run the self-check CLI loop automatically.

### 2. Generic LLM (ChatGPT, Gemini, Claude API, etc.)

Paste the body of `PROMPT_TEMPLATE.md` into the system prompt. Feed the
screenplay as a user message. When the model produces JSON, run the CLI
yourself and paste the response back — the model will iterate.

### 3. Programmatic pipeline

Read `schema.json` with your validator of choice in the pipeline. For CI,
`python -m tk_comfyui_batch_image.validate *.json --json` returns a
structured result you can gate on.

## Common errors

| Error | Likely cause | Fix |
|---|---|---|
| `[L2] pages[0]` total height exceeds inner | AI put too many / too tall panels on one page | Shorten a panel, or split into a new page |
| `[L1] shape.type expected "rect"` | AI tried to use `split` / `polygon` | Tell the AI the current release only supports rect |
| `[L2] root: page_template="custom" requires page_width_px` | AI omitted dimensions | Add them, or switch to a preset template |
| All panels identical size | AI did not apply composition principles | Re-prompt emphasising narrative rhythm |

## Files

- `schema.json` — generated from `tk_comfyui_batch_image/core/schema.py`. Single
  source of truth; do not hand-edit.
- `SKILL.md` — Claude Code + superpowers format.
- `PROMPT_TEMPLATE.md` — system-prompt version for generic LLMs.
- `examples/` — five `screenplay.md` / `output.json` pairs covering minimal,
  multi-panel, per-panel override, rtl reading, and 4-layer prompt composition.

## Validation CLI

```
python -m tk_comfyui_batch_image.validate <file> [more files …] [--json] [--max-errors N]
```

Exit codes: 0 = all pass, 1 = some file invalid, 2 = CLI usage error,
3 = I/O or JSON parse error.

## Feedback and extension

When a later milestone adds `shape.type="split"` (M3) or `"polygon"` (M4), the
schema will expand and new example directories will appear. The prohibitions
in `SKILL.md` / `PROMPT_TEMPLATE.md` will be relaxed accordingly. This README,
the examples list, and the error table above will be updated.
