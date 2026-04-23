# Example 03 — per-panel sampler_override

## Target
Teach `sampler_override` for panels that need higher quality.

## Screenplay

一頁兩格。第一格是輕鬆的過場。
第二格是整個故事的封面級高潮畫面，要非常精緻，多花些 steps。

## Expected AI reasoning

- Panel 2 is explicitly a "cover-level" shot → bump steps + cfg via sampler_override
- Panel 1 stays on default_sampler
- Heights chosen so the climactic panel is larger (e.g. 1100 vs 600)
- Both use rect (M1 limit)
