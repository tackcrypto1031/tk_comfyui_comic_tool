# Example 02 — vertical_stack with align

## Target
Teach three stacked panels using `layout_mode=vertical_stack` with varied `align`.

## Screenplay

第一格：清晨街景（建立場景，重要）。
第二格：主角推開門走出公寓，動作連續。
第三格：路人經過，主角驚訝看向他（情緒轉折）。

## Expected AI reasoning

- 3 scenes → 3 panels, all rectangles on one page
- Panel 1 (establishing) → large, center-aligned
- Panel 2 (action beat) → medium, left-aligned
- Panel 3 (emotion) → large, right-aligned to vary rhythm
- All panels share width ≤ 1040 (page_width 1080 - bleed 20*2)
- Total heights + 2 gutters must fit inside inner 1880 (= 1920 - 20*2)
