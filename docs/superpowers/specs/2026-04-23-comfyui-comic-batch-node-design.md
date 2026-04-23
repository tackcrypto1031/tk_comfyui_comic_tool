# ComfyUI 漫畫批次生成節點 — 設計文件

**日期**：2026-04-23
**專案代號**：`tk_comfyui_batch_image`
**狀態**：Design approved，待寫實作計畫

---

## 1. 目標與動機

打造一個 ComfyUI 自訂節點套件，讓使用者用一份 **JSON 劇本** 描述整本漫畫（頁數、每頁 panel 的 prompt / 尺寸 / 位置 / 形狀），節點內部自動：

1. 逐格跑採樣器生成每一張 panel 的 AI 圖像
2. 依 layout 規則（垂直堆疊、斜切、任意多邊形）把 panel 合成為完整頁面
3. 輸出全部合成頁 + 原始 panel + layout metadata

使用者只需接入 model / clip / vae（+ LoRA 等），**不必**自己串迴圈、KSampler、VAEDecode、CLIPTextEncode。

同時輸出一份 **Skill 交付包**，讓另一個 LLM 按嚴格規格產出合法 JSON 劇本。

---

## 2. 非目標（Out of Scope）

- 不負責劇情／對話文字生成（由上游 LLM 產出 JSON）
- 不負責對話框 / 文字氣泡 / 擬聲詞排版（`panel_bboxes_json` 輸出供下游工具使用）
- 不做 AI 一致角色控制（交給使用者自己接 IPAdapter / LoRA / reference-only）
- 不內建封面、目錄、頁碼等印刷版型
- 不做 PDF 封裝（使用者用 ComfyUI 下游節點或外部工具）

---

## 3. 架構總覽

### 3.1 節點組成

| 節點 | 角色 |
|---|---|
| `ComicScriptLoader` | 載入 JSON → 驗證 → 正規化 → 輸出自訂型別 `COMIC_SCRIPT` |
| `ComicBatchGenerator` | 內建 for-loop；逐格走完 prompt 拼接 → KSampler → VAEDecode；支援斷點續跑 |
| `ComicPageComposer` | 依 layout 合成每頁；處理 polygon mask、border、gutter、背景、debug overlay |

### 3.2 典型 Workflow 連線

```
CheckpointLoader → ┐
                   ├→ ComicBatchGenerator → ComicPageComposer → SaveImage
LoraLoader(可選) ─┤
VAELoader ────────┘
                        ↑
ComicScriptLoader ──────┘
```

使用者不必接 KSampler、VAEDecode、CLIPTextEncode、任何迴圈節點。

### 3.3 核心模組（非節點）

```
core/
  schema.py            # JSON Schema（single source of truth）
  validator.py         # Schema + 語義 + 生成前預檢
  layout_solver.py     # bbox、polygon、split、gutter、reading_direction
  mask_renderer.py     # anti-aliased polygon mask（4x supersample）
  compositor.py        # 合成邏輯
  prompt_builder.py    # 4 層 prompt 拼接（style + character + page + scene）
  sampler_runner.py    # 封裝 KSampler 三部曲
  cache_manager.py     # panel hash + manifest + 斷點續跑
  types.py             # COMIC_SCRIPT 自訂型別
```

---

## 4. JSON Schema

三層結構：**Book → Page → Panel**。

### 4.1 Book 層

```json
{
  "version": "1.0",
  "job_id": "my_comic_ch01",
  "reading_direction": "ltr",
  "page_template": "custom",
  "page_width_px": 2480,
  "page_height_px": 3508,
  "bleed_px": 60,
  "gutter_px": 20,
  "page_background": "#FFFFFF",
  "base_seed": 12345,
  "style_prompt":     { "positive": "...", "negative": "..." },
  "character_prompt": { "positive": "...", "negative": "..." },
  "default_sampler": {
    "sampler_name": "euler",
    "scheduler":    "normal",
    "steps":        25,
    "cfg":          7.0,
    "denoise":      1.0
  },
  "default_border": { "width_px": 3, "color": "#000000", "style": "solid" },
  "pages": [ /* Page[] */ ]
}
```

**欄位語意**

- `version`：schema 版本，目前 `"1.0"`
- `job_id`：斷點續跑識別碼。同一 `job_id` 再跑會讀取既有 panel cache
- `reading_direction`：`"ltr"` 或 `"rtl"`，影響 panel 順序與橫向並排排列
- `page_template`：`"A4"` / `"B5"` / `"JP_Tankobon"` / `"Webtoon"` / `"custom"`；非 custom 時會覆寫 `page_width_px / page_height_px`
- `bleed_px`：頁面四周保留的外部出血空間，panel 從此邊界內緣開始排
- `gutter_px`：panel 之間的預設垂直間距
- `base_seed`：每格 seed = `base_seed + global_panel_index`，可被 panel 層覆寫

### 4.2 Page 層

```json
{
  "page_index": 1,
  "page_prompt": { "positive": "night, rain", "negative": "" },
  "layout_mode": "vertical_stack",
  "gutter_px": 20,
  "panels": [ /* Panel[] */ ]
}
```

- `page_index`：從 1 開始遞增、連續
- `page_prompt`：該頁共用氛圍（例如「夜晚、下雨」）
- `layout_mode`：目前支援 `"vertical_stack"`（M1）與 `"custom_grid"`（M3+）
- `gutter_px`：覆寫 book-level

### 4.3 Panel 層

```json
{
  "panel_index": 1,
  "scene_prompt": { "positive": "hero looks at sky", "negative": "" },
  "width_px": 2360,
  "height_px": 900,
  "align": "center",
  "shape": { "type": "rect" },
  "border": { "width_px": 3, "color": "#000000" },
  "sampler_override": {
    "seed": 99999,
    "steps": 40,
    "cfg": 8.5
  }
}
```

- `panel_index`：該頁內從 1 開始遞增、連續
- `align`：`"left"` / `"center"` / `"right"`（vertical_stack 下對齊方式）
- `shape`：見 §4.4
- `sampler_override`：所有欄位可選，未給就用 `default_sampler`

### 4.4 進階 shape

#### rect（預設）
```json
"shape": { "type": "rect" }
```

#### split preset（斜切姊妹格語法糖）

`shape_group` 是 `page.panels` 陣列中的一種特殊條目（與一般 panel 物件並列），loader 會把它展開成兩個實際的 panel：

```json
"panels": [
  { /* 一般 panel */ },
  {
    "shape_group": {
      "type": "split",
      "direction": "vertical",
      "angle_deg": 15,
      "offset_ratio": 0.5,
      "align": "center",
      "bbox": { "width_px": 2360, "height_px": 900 }
    },
    "children": [
      { "scene_prompt": {...}, "sampler_override": {...} },
      { "scene_prompt": {...} }
    ]
  },
  { /* 下一個一般 panel */ }
]
```

- 展開後 `panel_index` 自動遞增（跨越 shape_group 時連續編號）
- `children` 內**不得**出現 `width_px / height_px / shape / align`（由 group 決定）
- `children` 內可有 `scene_prompt / sampler_override / border`

- `direction`：切線走向（`"vertical"` = 上下分兩格、`"horizontal"` = 左右分兩格）
- `angle_deg`：斜切角度（0 = 水平或垂直；範圍 [-89, 89]）
- `offset_ratio`：切點相對位置（0~1）
- `children`：長度**必須為 2**；loader 會自動展開成兩個 panel，共用同一條 split line，像素級密合

#### polygon（fallback）
```json
{
  "panel_index": 3,
  "scene_prompt": { "positive": "...", "negative": "" },
  "width_px": 2360,
  "height_px": 900,
  "align": "center",
  "shape": {
    "type": "polygon",
    "vertices_ratio": [[0,0], [1,0], [1,0.7], [0,1]]
  }
}
```

- polygon 的 bbox 一律使用 panel 的 `width_px / height_px`，`shape` 內部**不再**重複指定尺寸
- `vertices_ratio` 為 0~1 相對座標，loader 乘以 panel bbox 得絕對頂點
- 要求：頂點順序為順時針或逆時針、不自相交、至少 3 頂點

### 4.5 繼承規則

- **Prompt**：最終 positive = `style + character + page + scene + positive_suffix`（逗號串接，空值略過）；negative 同理
- **Sampler**：panel `sampler_override` ⊃ book `default_sampler` ⊃ 節點 widget 預設
- **Border / gutter**：Panel ⊃ Page ⊃ Book ⊃ 節點 widget 預設

---

## 5. Layout 解算

### 5.1 座標系統

原點在頁面左上角，x 向右、y 向下（PIL / OpenCV 慣例）。`reading_direction` 只影響 panel 讀取 / 生成 / 合成順序，不改座標系。

### 5.2 vertical_stack 解算

1. 算內容區 inner bbox：`(bleed, bleed) ~ (W-bleed, H-bleed)`
2. 由上而下逐格：
   - 寬 = `panel.width_px`，依 `align` 決定 x 起點
   - y 起點 = 上一格 y 終點 + `gutter_px`
3. 驗證：Σ panel.height + Σ gutter ≤ 內容區高度

### 5.3 split 姊妹格共線解算

- 兩格共用同一條 split line `(P1, P2)`，由 `direction / angle_deg / offset_ratio / bbox` 算出
- 左（或上）格 polygon = `[TL, P1, P2, BL]`
- 右（或下）格 polygon = `[P1, TR, BR, P2]`
- 兩格像素級共用 `P1, P2` → 合成無縫無疊
- 每格 bbox = 各自 polygon 的最小外接矩形，作為 AI 生圖尺寸

### 5.4 Polygon mask（anti-aliased）

- 流程：`Image.new("L", bbox*4, 0)` → `ImageDraw.polygon(vertices*4, fill=255)` → `resize(bbox, Lanczos)`
- 4x supersample 確保斜線邊緣無階梯
- 姊妹格使用同一組頂點 → mask 邊緣像素級對齊

---

## 6. 生成管線

### 6.1 核心迴圈（`ComicBatchGenerator.generate`）

```python
out_dir    = f"{comfy_output}/comics/{job_id}"
panels_dir = f"{out_dir}/panels"

for page in script['pages']:
    for panel in page['panels_solved']:       # loader 已展開 shape_group
        cache_path = f"{panels_dir}/p{page.idx:03d}_{panel.idx:02d}.png"

        if exists(cache_path) and manifest_hash_matches(panel, cache_path):
            image = load_image(cache_path)
        else:
            pos = join(style.pos, char.pos, page.pos, panel.scene.pos, pos_suffix)
            neg = join(style.neg, char.neg, page.neg, panel.scene.neg, neg_suffix)
            s   = merge(default_sampler, panel.sampler_override)
            seed = panel.sampler_override.get('seed') or (base_seed + global_idx)
            w, h = panel.bbox_size

            cond_pos = clip_encode(clip, pos)
            cond_neg = clip_encode(clip, neg)
            latent   = empty_latent(w, h, batch_size=1)
            samples  = ksampler(model, seed, s.steps, s.cfg, s.sampler_name,
                                s.scheduler, cond_pos, cond_neg, latent, s.denoise)
            image    = vae_decode(vae, samples)

            save_image(image, cache_path)
            write_panel_manifest(cache_path, panel_hash)

        results.append({
            'page_index': page.idx, 'panel_index': panel.idx,
            'image': image, 'bbox': panel.bbox, 'polygon_abs': panel.polygon_abs,
        })
```

### 6.2 斷點續跑（Panel Manifest）

- 每張 panel PNG 旁邊寫 `.json` 紀錄 **panel hash**：`SHA256(prompt + seed + size + sampler_override)`
- 重跑時：hash 一致 → 直接 load；不一致 → 重生並覆蓋
- 使用者改某格 prompt 後重跑，只會重生該格

### 6.3 失敗處理

- 預設策略 `retry_then_skip`：重試 2 次，仍失敗則寫 placeholder（紅色 X）並記 log
- 節點參數 `on_failure` 可切 `"halt"`：立即中止並報錯

### 6.4 進度顯示

- 呼叫 ComfyUI 內建 `ProgressBar`，每格更新一次
- `generation_log` 輸出格式：`[page 01/05] panel 02/03 ... generated (3.2s)` 或 `... cached (0.1s)`

---

## 7. 頁面合成

### 7.1 合成流程（每頁）

```python
canvas = PIL.new("RGB", (page_w, page_h), page_background)

page_panels = filter(results, page_index == page.idx)   # 已按 reading_direction 排序

for panel in page_panels:
    img = panel.image

    if panel.shape_type == "rect":
        canvas.paste(img, panel.bbox_topleft)
    else:
        mask = render_aa_polygon_mask(panel.polygon_local, panel.bbox_size)
        canvas.paste(img, panel.bbox_topleft, mask=mask)

    if panel.border.width_px > 0:
        draw_polygon_outline(canvas, panel.polygon_abs,
                             width=panel.border.width_px, color=panel.border.color)

if debug_overlay:
    draw_debug_labels(canvas, page_panels)
```

### 7.2 關鍵細節

- **邊框畫在 canvas 上、不是 panel 圖上** → 斜線用 4x supersample 畫 line，無鋸齒
- 姊妹格共用的 split line **只畫一次**（防雙線重疊變粗）
- **Gutter 是負空間**：layout 階段就預留了間距，合成時背景色自然露出 = gutter
- **Debug overlay**：panel 編號 `[p1-p2]`、polygon 洋紅虛線外框、左下角 scene prompt 前 30 字

### 7.3 輸出

| 輸出埠 | 型別 | 說明 |
|---|---|---|
| `composed_pages` | IMAGE | 每頁一張合成圖 |
| `individual_panels` | IMAGE | 原始生圖 panel batch（pass-through）|
| `panel_bboxes_json` | STRING | 每頁每格的絕對 bbox、polygon、prompt metadata |

---

## 8. 驗證機制

### 8.1 三層驗證

**Layer 1 — JSON Schema**（`jsonschema` 套件）
- 型別、必填、enum、range
- 錯誤訊息帶路徑：`pages[2].panels[1].sampler_override.cfg: 15.0 > maximum 30.0`

**Layer 2 — 語義驗證**
- `page_index / panel_index` 從 1 連續遞增
- `shape_group.children` 長度 = 2
- `Σ panel.height + Σ gutter ≤ page_height - bleed*2`
- polygon 頂點不自相交
- 顏色符合 `#RRGGBB`
- `page_template` 存在

**Layer 3 — 生成前預檢**
- 引用的 LoRA / Checkpoint 名可解析
- 總 panel 數 × 預估秒數提示

### 8.2 錯誤訊息格式

```
❌ Comic script validation failed:

  pages[0].panels[2].shape.angle_deg
    expected: number in [-89, 89]
    actual:   95
    hint:     angle_deg is measured from orthogonal axis.

  pages[1].panels: total height 3600px + gutters 80px = 3680px
    exceeds inner content area 3388px (page 3508 - bleed*2).
    hint:     reduce a panel height or increase page_height_px.
```

### 8.3 Standalone CLI

```bash
python -m tk_comfyui_batch_image.validate path/to/script.json
# exit 0 = pass；non-zero = fail
```

AI 生完劇本後可自行呼叫此 CLI 自檢，不必啟動 ComfyUI。

---

## 9. Skill 交付包

放於 `docs/skills/comic-script-authoring/`：

```
docs/skills/comic-script-authoring/
├── SKILL.md                # Claude Code / superpowers 格式
├── schema.json             # JSON Schema draft-2020-12（single source of truth）
├── PROMPT_TEMPLATE.md      # 通用 LLM system prompt
├── README.md               # 人類讀的完整規格
└── examples/
    ├── 01_rectangles_only.json
    ├── 02_slash_split.json
    ├── 03_mixed_shapes.json
    ├── 04_webtoon_long.json
    └── 05_jp_manga_rtl.json
```

### 9.1 SKILL.md 內容大綱

- frontmatter：`name`、`description`（觸發條件）
- **絕對禁止事項**：改鍵名為中文、新增 schema 未定義欄位、發明 `shape.type`、用 `rgb()`、總高度超出頁面
- **欄位語意**：每個欄位 + 何時用 + 範例
- **撰寫步驟**：
  1. 決定 `reading_direction` 與 `page_template`
  2. 列出 `style_prompt` 與 `character_prompt`
  3. 逐頁：擬 `page_prompt`，決定 `layout_mode`
  4. 逐格：先 `shape`，再 `scene_prompt`
  5. 跑 CLI 驗證
  6. 驗證通過才交付
- **自檢 checklist**（輸出前必須全打勾）
- **完整範例**（引用 `examples/`）

### 9.2 JSON Schema 作為 Single Source of Truth

- `core/schema.py` 以 Python dict 維護，產生 `docs/skills/.../schema.json`
- 其他文件（SKILL.md / README.md / PROMPT_TEMPLATE.md）引用 schema.json，不另維護一份

---

## 10. 測試策略

- **Unit**：`core/` 每個模組獨立測試，不觸發 ComfyUI runtime
- **Golden image**：`mask_renderer` + `compositor` 用固定輸入算結果，比對 `tests/fixtures/golden/*.png` 的 SHA256；允許小閾值差異
- **Schema fuzz**：合法 / 非法 JSON fixture 覆蓋所有錯誤訊息分支
- **Integration**：mock `model / clip / vae` 為回傳固定 noise 的假物件，驗證 `ComicBatchGenerator` 全流程（含斷點續跑）
- **CI**：GitHub Actions 跑 `pytest` + `ruff` + `mypy`

---

## 11. 依賴

- `Pillow >= 10.0`（anti-aliased polygon fill）
- `jsonschema >= 4.0`
- `numpy`、`torch`（ComfyUI 內建）
- 無 ComfyUI 分支專屬依賴，跨版本相容

---

## 12. 檔案佈局

```
tk_comfyui_batch_image/
├── __init__.py                 # 註冊節點到 ComfyUI
├── pyproject.toml
├── README.md
├── LICENSE
├── nodes/
│   ├── __init__.py
│   ├── script_loader.py
│   ├── batch_generator.py
│   └── page_composer.py
├── core/
│   ├── __init__.py
│   ├── schema.py
│   ├── validator.py
│   ├── layout_solver.py
│   ├── mask_renderer.py
│   ├── compositor.py
│   ├── prompt_builder.py
│   ├── sampler_runner.py
│   ├── cache_manager.py
│   └── types.py
├── validate.py                 # `python -m tk_comfyui_batch_image.validate`
├── docs/
│   ├── superpowers/
│   │   └── specs/
│   │       └── 2026-04-23-comfyui-comic-batch-node-design.md   (this file)
│   └── skills/
│       └── comic-script-authoring/
├── tests/
│   ├── test_schema.py
│   ├── test_validator.py
│   ├── test_layout_solver.py
│   ├── test_mask_renderer.py
│   ├── test_compositor.py
│   ├── test_prompt_builder.py
│   ├── test_cache_manager.py
│   └── fixtures/
│       ├── scripts/
│       └── golden/
└── examples/
    ├── basic_vertical_stack.json
    └── advanced_slash_cut.json
```

---

## 13. 實作分期（Milestones）

| Phase | 範圍 | 使用者可見結果 |
|---|---|---|
| **M1 — 基礎** | schema + loader + rect-only `vertical_stack` layout + generator + composer + cache | 矩形垂直堆疊能跑通整本漫畫 |
| **M2 — 驗證 & skill** | validator（三層）+ CLI + SKILL.md + 5 個 examples + PROMPT_TEMPLATE | 另一個 AI 能按規範產出合法 JSON |
| **M3 — 斜切格** | `split` preset + 姊妹格展開 + aa polygon mask + 共線繪框 | 斜切漫畫格可產出且邊緣無縫 |
| **M4 — polygon fallback** | `polygon` 型態 + 頂點語義驗證 | 進階使用者可做任意多邊形 |
| **M5 — 打磨** | debug overlay、進度條、錯誤訊息美化、golden test、webtoon template | 生產可用 |

---

## 14. 關鍵設計決策記錄

| 決策 | 選擇 | 理由 |
|---|---|---|
| 節點迭代模型 | 內建 for-loop 一體化 | 使用者不必學 ComfyUI loop 節點，最省事 |
| Prompt 結構 | 4 層（style + character + page + scene）+ per-panel sampler override | 保角色一致性 + 重要格可強化品質 |
| 單位 | 像素起手（mm 為未來擴充） | digital-first，簡單；避免 DPI 複雜度污染 M1 |
| 斜切實作 | `split` preset 語法糖 + 多邊形 fallback | AI 易寫、使用者易懂，極端需求仍可表達 |
| Mask 抗鋸齒 | PIL 4x supersample + Lanczos | 零外部依賴、效果可接受 |
| 姊妹格共線 | 共用 `P1, P2` 像素級對齊 | 唯一能保證無縫的作法 |
| 斷點續跑 | Panel hash manifest | 改一格重跑不影響其他格 |
| Skill 交付 | SKILL.md + schema.json + PROMPT_TEMPLATE + README + 5 examples | 覆蓋 Claude、通用 LLM、嚴格驗證三種使用場景 |
| Schema 真相來源 | `core/schema.py` | 其他文件引用它，避免多處維護不同步 |

---

## 15. 風險與未決事項

- **ComfyUI 跨版本相容**：`KSampler` 等 API 若在新版有變動，可能需要包裝層；M1 先以當前穩定版為準
- **Polygon 邊緣 alpha 合成與 border 繪製順序**：目前設計 border 畫在 canvas 上而非 mask 邊緣；若使用者反映 border 超出 polygon，需再打磨
- **大圖記憶體**：整本漫畫 panel 全部 decode 後放 list 可能吃 VRAM/RAM；必要時改成 M5 的 streaming 模式（decode 一頁 → 合成 → 釋放）
- **Webtoon 超長頁**：Pillow 對超過 65535px 的 image 有限制，M5 處理分段策略
