# Example 01 — Minimal

## Target
Teach the absolute-minimum JSON: one page, one panel, default canvas (1080×1920).

## Screenplay

主角站在窗前看雨。

## Expected AI reasoning

- No reading direction specified → default `ltr`
- No page size specified → use default 1080×1920 + `page_template="custom"`
- One scene → one page, one panel
- No emotional cue → medium-size panel (height ~600px, full width ~1040px)
- Character appearance not described → keep `character_prompt` minimal / empty
