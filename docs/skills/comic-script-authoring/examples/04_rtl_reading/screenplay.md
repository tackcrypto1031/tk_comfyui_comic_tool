# Example 04 — reading_direction = rtl

## Target
Japanese-style manga default: rtl reading direction.

## Screenplay

這是一段短篇日式漫畫。主角走進神社（第一格），
蹲下抽一支籤（第二格），看到籤上的字（第三格，情緒重點，放大）。

## Expected AI reasoning

- Culture cue "神社 / 籤" → Japanese → set `reading_direction: "rtl"`
- 3 panels
- Panel 3 is emotional peak → largest height
- Still all rect (M1)
