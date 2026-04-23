# Example 05 — 4-layer prompt stacking

## Target
Show how style_prompt + character_prompt + page_prompt + scene_prompt compose.
Two pages with the same main character across multiple environments.

## Screenplay

主角是一名黑髮藍眼的少年騎士。
第一頁：他站在城堡中庭練劍（兩格：全景 + 動作特寫）。
第二頁：他走到高塔頂端俯瞰王國（一格，壯闊）。

## Expected AI reasoning

- Character appears across all panels → put fixed description in character_prompt
- style_prompt carries the overall art style
- page_prompt carries per-page environmental mood
- scene_prompt carries the specific action/shot
- Page 2 uses a single tall panel (800 or larger) for the sweeping vista
- All rect (M1)
