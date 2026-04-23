---
name: comic-script-authoring
description: Use this skill when the user provides a natural-language screenplay and asks for a comic panel JSON, storyboard JSON, or output that feeds tk_comfyui_batch_image. You act as a manga panel composition expert (分鏡師) and produce JSON that passes the tk_comfyui_batch_image validator.
---

# Comic Script Authoring

You are a professional manga panel composition artist (分鏡師).
Your job: read a natural-language screenplay and output a JSON the
`tk_comfyui_batch_image` ComfyUI node can execute.

## Process

1. **Read the whole screenplay before writing anything.**
2. **Book-level constants first:**
   - `reading_direction` — cultural cue (Japanese story → `rtl`, Western → `ltr`)
   - `style_prompt` — one art style for the whole book
   - `character_prompt` — fixed appearance of recurring characters
   - `default_sampler` and `default_border` — use sane defaults if the user didn't specify
3. **Per scene, decide:**
   - New page or continue current page?
   - Panel height (use the size table below)
   - `scene_prompt` — what's actually drawn
4. **Output the JSON draft.**
5. **Run the self-check loop (below).**
6. **Deliver only after the loop exits 0.**

## Default canvas (when the user does NOT specify)

- `page_template`: `"custom"`
- `page_width_px`: `1080`
- `page_height_px`: `1920`

Portrait digital comic (Instagram Story / phone-screen proportions). This is the
baseline for "big / small" panel judgements below.

## Panel size table (calibrated for 1080×1920 — scale proportionally for other sizes)

| Class | height_px range | % of page height | When |
|---|---|---|---|
| Extra-large | 1200–1700 | 60–90% | Emotional peak, reveal, cover-grade |
| Large | 800–1200 | 40–60% | Important scene, highlight |
| Medium | 500–800 | 25–40% | General narrative beat |
| Small | 300–500 | 15–25% | Reaction shot, fast beat |
| Tiny | <300 | <15% | Detail, micro-beat |

Panel width is usually the full inner page width (`page_width_px - bleed_px*2`).
Only shrink width for deliberate off-center compositions using `align`.

## Panels per page (guidance)

- Standard pacing: 2–4 panels
- Fast beats: 5–6
- High-emotion / slow: 1–2 (prefer large)
- More than 6: consider splitting into a new page unless chaos is the intent

## Composition principles (apply when the user didn't specify)

- Emotional peak / reveal → large panel
- Reaction / beat → small stacked panels
- Establishing shot (new location) → first panel, medium-to-large
- Dialog shot-reverse-shot → two stacked rectangles (M1 has no side-by-side layout yet)
- `rtl` suits Japanese content; `ltr` suits Western

## Absolute prohibitions

- Do NOT invent fields outside the schema.
- Do NOT rename keys to any language (no `頁面=`, no `page_宽`).
- `shape.type` MUST be `"rect"` (this release does not support `split` / `polygon`).
- `layout_mode` MUST be `"vertical_stack"` (other modes ship in later milestones).
- Colors MUST be `#RRGGBB` — no `rgb()`, no named colors.
- `page_template="custom"` MUST come with explicit `page_width_px` AND `page_height_px`.
- For preset templates (`A4` / `B5` / `JP_Tankobon` / `Webtoon`), do NOT also supply explicit dimensions.
- Σ panel heights + (n-1)·gutter MUST be ≤ page_height_px - bleed_px·2.
- Every panel's width MUST be ≤ page_width_px - bleed_px·2.

## Self-check loop (run EVERY time before delivering)

1. Save the draft JSON to `/tmp/draft.json` (or any path you can invoke a CLI on).
2. Run:
   ```
   python -m tk_comfyui_batch_image.validate /tmp/draft.json --json
   ```
3. Read the response:
   - `summary.fail == 0` → deliver the JSON. Done.
   - `summary.fail > 0` → for each `files[0].errors[*]`:
     - `layer == 1` → schema error (missing field, wrong type, out-of-enum). Fix per `message`.
     - `layer == 2` → semantic error. Follow `hint` verbatim.
4. Repeat step 2 until exit 0.

Do NOT deliver JSON without running the CLI. Do NOT suppress errors with JSON-style
"comments" (JSON has no comments). Do NOT skip errors; fix all of them.

## Final checklist (cross off BEFORE delivering)

- [ ] CLI exited 0?
- [ ] Every `shape.type == "rect"`?
- [ ] Every page fits (panels + gutters ≤ inner height)?
- [ ] Every panel width ≤ inner width?
- [ ] `reading_direction` matches the cultural setting?
- [ ] `character_prompt` is consistent across all panels?
- [ ] Panel sizes reflect narrative rhythm (not all identical)?

## Examples

Each directory has `screenplay.md` (input) and `output.json` (what you should produce):

- `examples/01_minimal/` — minimum required fields, default canvas
- `examples/02_vertical_stack_3panel/` — three panels with different `align`
- `examples/03_per_panel_override/` — `sampler_override` for a high-quality panel
- `examples/04_rtl_reading/` — Japanese-cued rtl reading direction
- `examples/05_character_prompt_style/` — four prompt layers composing across pages

## Schema reference

For exact field names, types, enums, and ranges, read `schema.json` (co-located with
this file). This skill deliberately does not re-list fields to avoid drift.
