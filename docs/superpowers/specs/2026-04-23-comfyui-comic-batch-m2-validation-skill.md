# ComfyUI 漫畫批次生成節點 — M2 驗證 & Skill 交付包設計

- **Status**: Spec draft — pending plan
- **Date**: 2026-04-23
- **Milestone**: M2 (follows M1 foundation, HEAD `1aef0f2`)
- **Parent spec**: `docs/superpowers/specs/2026-04-23-comfyui-comic-batch-node-design.md`

---

## 1. 目標

讓 AI（扮演漫畫分鏡師）能根據自然語言劇本產出合法的 JSON，並在不開 ComfyUI 的前提下自行驗證格式是否正確；同時提供一套可直接安裝/貼用的 skill 交付包，對 Claude Code、通用 LLM、人類工具使用者三種場景都走得通。

---

## 2. Scope 與非 scope

**In scope**
- Layer 2 semantic validator（M1 功能子集 5 條規則）
- Layer 1 + Layer 2 共用入口 `validate(data)`，`ComicScriptLoader` 升級呼叫
- Standalone CLI：`python -m tk_comfyui_batch_image.validate`
- `core/schema.py → docs/skills/.../schema.json` export + drift test
- Skill pack：`SKILL.md` / `PROMPT_TEMPLATE.md` / `README.md` / `examples/` × 5
- Examples 同時包含 `screenplay.md`（輸入劇本）+ `output.json`（AI 應產結果）

**Out of scope**
- Layer 3 pre-generation checks（LoRA 可解析、模型名存在等）— 延後
- `shape_group` / `polygon` 相關 Layer 2 規則 — M3 / M4
- `page_template != "custom"` 的尺寸解析表 — 延後
- AI 輸出 quality 測試 — 不是 validator 責任
- 任何 ComfyUI runtime 行為的改動

---

## 3. 使用者工作流

```
[人類寫自然語言劇本]
         │
         ▼
[AI 讀 SKILL.md / PROMPT_TEMPLATE.md，扮演漫畫分鏡師]
         │
         ▼
[AI 輸出 JSON 草稿]
         │
         ▼
[AI 呼叫 CLI: python -m tk_comfyui_batch_image.validate --json]
         │
     ┌───┴───┐
     │       │
  fail      pass
     │       │
     ▼       ▼
  [修 JSON] [交給使用者]
     │
     └─── 回迴圈
              │
              ▼
     [使用者把 JSON 餵給 ComfyUI workflow → ComicScriptLoader 內部也會再 validate 一次作為安全網]
              │
              ▼
          出圖
```

---

## 4. 架構

### 4.1 檔案配置

```
tk_comfyui_batch_image/
├── core/
│   ├── validator.py         ← 擴充：加 Layer 2 + 共用 validate() 入口
│   └── schema.py            ← 既有，single source of truth
├── validate.py              ← 新增：CLI 入口
├── schema_export.py         ← 新增：core/schema.py → JSON
│
docs/skills/comic-script-authoring/
├── schema.json              ← schema_export.py 產出（不手動維護）
├── SKILL.md                 ← Claude Code + superpowers 格式
├── PROMPT_TEMPLATE.md       ← 通用 LLM 的 system prompt 版
├── README.md                ← 人類工具使用者（非 JSON 作者）
└── examples/
    ├── 01_minimal/
    │   ├── screenplay.md
    │   └── output.json
    ├── 02_vertical_stack_3panel/
    ├── 03_per_panel_override/
    ├── 04_rtl_reading/
    └── 05_character_prompt_style/
```

### 4.2 兩個驗證入口共用核心

```python
# core/validator.py
def validate(data: dict) -> None:
    _validate_schema(data)        # Layer 1（M1 已存在的 jsonschema）
    errors = []
    for rule in _LAYER2_RULES:    # Layer 2（M2 新增）
        errors.extend(rule(data))
    if errors:
        raise ValidationError("\n".join(errors))
```

- **節點內**（`nodes/script_loader.py:77`）：把 `validate_schema(data)` 換成 `validate(data)`
- **CLI**（`validate.py`）：薄 wrapper，負責 I/O、輸出格式、exit code

### 4.3 Layer 2 規則 plug-in 設計

```python
_LAYER2_RULES: list[Callable[[dict], list[str]]] = [
    r_page_index_continuity,
    r_panel_index_continuity,
    r_layout_fits_page,
    r_panel_width_fits,
    r_page_template_dim_consistency,
]
```

每條 rule 為 pure function 回傳 `list[str]`。M3 加 shape_group 時 append 新 rule 進去即可。

---

## 5. Layer 2 規則（M1 子集）

### R1 — Page index 從 1 連續遞增
- 規則：`pages[i].page_index == i + 1`
- 錯訊範例：
  ```
  [L2] pages[2].page_index
    expected 3, got 5 (pages must be contiguous from 1).
  ```

### R2 — Panel index 在每頁內連續從 1 遞增
- 規則：`pages[i].panels[j].panel_index == j + 1`
- 錯訊格式同 R1

### R3 — `vertical_stack` layout 裝得進頁面
- 規則：`Σ panels[].height_px + (n-1) × gutter_px ≤ page_height_px - bleed_px × 2`
- `gutter_px` 取 page override 優先，否則 book-level
- `page_height_px` 來自：`page_template == "custom"` 時取顯式值（見 R5）
- 錯訊：
  ```
  [L2] pages[0]
    total height 800px (panels) + 20px (gutters) = 820px
    exceeds inner area 728px (= 768 - bleed 20*2).
    hint: reduce a panel height, lower gutter_px, or raise page_height_px.
  ```

### R4 — 每個 panel 的 width 裝得進頁面
- 規則：`panel.width_px ≤ page_width_px - bleed_px × 2`
- 錯訊：
  ```
  [L2] pages[0].panels[2]
    width 500px exceeds inner width 472px (= 512 - bleed 20*2).
    hint: reduce panel.width_px or raise page_width_px.
  ```

### R5 — `page_template` 與顯式尺寸一致
- `page_template == "custom"` → 必填 `page_width_px` + `page_height_px`
- `page_template != "custom"` 且同時提供顯式尺寸 → **reject**（嚴格，避免兩處真相）
- 錯訊：
  ```
  [L2] root
    page_template="custom" requires page_width_px and page_height_px.
  ```

---

## 6. CLI

### 6.1 Entrypoint

```bash
python -m tk_comfyui_batch_image.validate <file1> [file2 ...] [options]
```

### 6.2 Options

| Flag | 預設 | 行為 |
|---|---|---|
| `--json` | off | 機器格式輸出，關閉彩色 |
| `--max-errors N` | 20 | 每檔最多顯示 N 個錯，截斷會標記 `truncated` |
| `--no-color` | off | 人讀模式關閉 ANSI，CI 用 |

### 6.3 Exit codes

| Code | 含意 |
|---|---|
| 0 | 全部檔案通過 |
| 1 | 至少一個檔案 validation 失敗 |
| 2 | CLI 用法錯（沒檔案、未知 flag） |
| 3 | 檔案 I/O / JSON parse 錯 |

### 6.4 人讀輸出格式

成功：
```
✓ examples/01_minimal.json
  version 1.0, 1 page, 1 panel, job_id=minimal
```

失敗：
```
✗ examples/02_broken.json  (3 errors)

  [L2] pages[0]
    total height 820px exceeds inner 728px.
    hint: reduce a panel height or raise page_height_px.

  [L1] pages[0].panels[2].shape.type
    expected one of ["rect"], got "split"

  ... and 1 more error suppressed (raise --max-errors to see all)
```

多檔摘要：
```
---
Summary: 3 files, 2 ✓ ok, 1 ✗ fail
```

### 6.5 `--json` 輸出

```json
{
  "summary": { "total": 3, "ok": 2, "fail": 1 },
  "files": [
    {
      "path": "examples/01_minimal.json",
      "status": "ok",
      "errors": [],
      "info": { "job_id": "minimal", "page_count": 1, "panel_count": 1 }
    },
    {
      "path": "examples/02_broken.json",
      "status": "fail",
      "errors": [
        {
          "layer": 2,
          "path": "pages[0]",
          "message": "total height 820px exceeds inner 728px",
          "hint": "reduce a panel height or raise page_height_px"
        }
      ],
      "truncated": false
    }
  ]
}
```

AI 自檢迴圈主要讀 `summary.fail` 與 `files[].errors[]`。

---

## 7. Skill pack

### 7.1 Single source of truth

- `core/schema.py`（Python dict）為真相
- `schema_export.py` 序列化出 `docs/skills/.../schema.json`
- `SKILL.md` / `PROMPT_TEMPLATE.md` / `README.md` 都**不重複列欄位**，只講流程/原則/禁事/checklist，需要細節時 link 到 `schema.json`
- CI / pytest 跑 drift test，兩邊不同步就 fail

### 7.2 SKILL.md 內容大綱

```markdown
---
name: comic-script-authoring
description: Turn a natural-language screenplay into a validated comic JSON.
---

# Comic Script Authoring

你是專業的漫畫分鏡師（manga panel composition artist）。

## 流程
1. 讀完整本劇本
2. 敲定書本常數：reading_direction / style_prompt / character_prompt
3. 逐場景決定：新頁 vs 延續 / 格子大小 / scene_prompt
4. 輸出 JSON
5. 跑 CLI 自檢
6. 有錯就修，再驗

## 預設畫布（使用者沒指定時）
- page_template = "custom"
- page_width_px = 1080
- page_height_px = 1920

## 格子大小基準（以 1080×1920 為參照，按比例縮放）
| 分類 | height_px 範圍 | 占頁面高度比例 | 適用場景 |
|---|---|---|---|
| 超大 | 1200–1700 | 60–90% | 情緒高潮、揭露 |
| 大   | 800–1200  | 40–60% | 重要場景 |
| 中   | 500–800   | 25–40% | 一般敘事 |
| 小   | 300–500   | 15–25% | 反應鏡頭、節奏 beat |
| 極小 | <300      | <15%   | 特寫、時間流逝 |

## 一頁格數建議
- 標準敘事：2–4 格
- 快節奏：5–6 格
- 高情緒：1–2 格
- 超過 6 格：除非刻意，考慮分頁

## 分鏡原則（使用者沒指定時自己判斷）
- 情緒高潮 / 揭露 → 大格
- 節奏 beat / 反應 → 小格堆疊
- 場景建立 → 頁首大格
- 對話切換 → 上下矩形近似正反打（M1 限制）
- 閱讀方向（rtl 日式、ltr 西式）

## 絕對禁止
- 不發明 schema 沒定義的欄位
- 不把 key 改中文 / 任何其他語言
- `shape.type` 只能 `"rect"`（M1）
- `layout_mode` 只能 `"vertical_stack"`（M1）
- 顏色只能 `#RRGGBB`
- `page_template="custom"` 必須給尺寸
- Σ panel.height + gutter 不超 page_height - bleed*2

## 自檢迴圈（產完 JSON 必跑）
1. 把草稿存 `/tmp/draft.json`
2. 跑 `python -m tk_comfyui_batch_image.validate /tmp/draft.json --json`
3. 讀回傳：
   - summary.fail == 0 → 交使用者
   - summary.fail > 0 → 逐一修 errors[*].path 指出的欄位
     - layer=1 → schema 錯
     - layer=2 → 語義錯，按 hint 修
4. 回步驟 2，直到 exit 0

絕對不要：沒跑 CLI 就交、用 JSON 註解敷衍（JSON 不支援）、跳過錯誤。

## 自檢 checklist（產完必打勾）
- [ ] CLI validate 回 exit 0？
- [ ] 每個 panel shape 都是 rect？
- [ ] panel 高度總和 + gutter 有塞進頁面？
- [ ] reading_direction 跟文化 context 一致？
- [ ] character_prompt 整本一致？

## 範例
見 examples/01_minimal/ 到 examples/05_character_prompt_style/
每個目錄有 screenplay.md（輸入）+ output.json（該產的結果）

## Schema reference
欄位、型別、enum、range → 看 schema.json
```

### 7.3 PROMPT_TEMPLATE.md 差異

- 無 frontmatter，純 system prompt
- 自檢迴圈改協作模式（LLM 無 shell）：
  ```
  1. 輸出 JSON 草稿於 ```json 區塊
  2. 請使用者存檔後執行 CLI 並貼回結果
  3. 根據 errors 修正，重新輸出完整 JSON
  4. 重複到通過
  ```

### 7.4 README.md 內容大綱

- 這個 skill pack 做什麼（劇本 → JSON 工具鏈）
- 三條整合路徑：Claude Code / 通用 LLM / 程式化 pipeline
- End-to-end 範例（劇本 → JSON → CLI → ComfyUI）
- 常見錯誤 cookbook（3–5 條）
- 指向 `schema.json` / `examples/` / 專案 root README

### 7.5 Examples × 5

| # | 資料夾 | 教什麼 | 劇本留白處 |
|---|---|---|---|
| 01 | `01_minimal/` | 最少必要欄位 | 無 |
| 02 | `02_vertical_stack_3panel/` | vertical_stack + align | 格子大小（情緒線索） |
| 03 | `03_per_panel_override/` | per-panel sampler_override | 某格要更高品質 |
| 04 | `04_rtl_reading/` | reading_direction="rtl" | 日式風 → AI 選 rtl |
| 05 | `05_character_prompt_style/` | 4 層 prompt 協作 | 跨格角色一致性 |

每個目錄：`screenplay.md`（人類自然語言）+ `output.json`（AI 應產結果）

---

## 8. 測試策略

### 8.1 新增測試

| 檔案 | 測試數 | 涵蓋 |
|---|---|---|
| `tests/test_validator_layer2.py` | ~13 | 5 條規則各 2–3 cases |
| `tests/test_cli_validate.py` | ~10 | exit codes、輸出格式、truncation |
| `tests/test_schema_export.py` | 1 | `schema.json` 跟 `core/schema.py` 同步 |
| `tests/test_examples_valid.py` | 5（param） | 每個 example `output.json` 合法 |

總計約 **29 個新測試**，疊在 M1 的 74 上 → M2 後 ~103 個。

### 8.2 不做的測試（YAGNI）

- AI 輸出 quality（不穩）
- ComfyUI end-to-end（M1 `test_integration_e2e.py` 已覆蓋）
- 整篇錯訊 exact snapshot（改字 fail，改比對 key phrase）

### 8.3 M1 regression 保證

- `ComicScriptLoader` 由 `validate_schema(data)` 升級為 `validate(data)`
- M1 既有 74 測試應全部仍通過（fixtures 都合規）
- 若揭露破綻 → 修 fixture 而非跳過測試

---

## 9. 實作階段與依賴

| Phase | 內容 | 依賴 | 測試增量 |
|---|---|---|---|
| **P1** | Layer 2 validator（5 條規則） | - | +13 |
| **P2** | CLI | P1 | +10 |
| **P3** | Schema export + drift test | - | +1 |
| **P4** | Examples × 5 + regression test | P1, P3 | +5 |
| **P5** | SKILL.md / PROMPT_TEMPLATE.md / README.md | P1–P4 產物 | 0 |

```
P1 ─┬─► P4
    │
P3 ─┘
P2 (獨立)
P1, P2, P3, P4 ─► P5
```

subagent-driven-development 切約 8–10 task，最大平行度 ~4（P1/P2/P3 可平行）。

---

## 10. Acceptance criteria

- [ ] `core/validator.py` 有 `validate()`（Layer 1 + Layer 2），5 條 Layer 2 規則全實作
- [ ] `nodes/script_loader.py` 升級呼叫 `validate()`
- [ ] `validate.py` CLI 可執行：單檔/多檔、`--json`、`--max-errors`、`--no-color`、4 個 exit code
- [ ] `schema_export.py` 可執行
- [ ] `docs/skills/comic-script-authoring/` 5 個 artifacts 齊全
- [ ] 5 個 examples 每個通過 CLI validate（exit 0）
- [ ] 總測試 ~103 個 pytest 全綠，ruff clean
- [ ] Schema drift test 存在且綠
- [ ] `tk_comfyui_batch_image/__init__.py` 不動（M2 不改節點集合）

---

## 11. 風險與未決事項

- **page_template 非 custom 的尺寸表**：schema enum 定了 A4/B5/JP_Tankobon/Webtoon 但沒有具體 width/height。M2 R5 先 reject 顯式尺寸，具體尺寸表延到 M5 或視使用情境插入。AI 目前被引導優先用 `custom`。
- **ltr / rtl 對 vertical_stack 的影響**：M1 單頁內都是上到下，rtl 只影響跨頁裝訂順序。M3 以後如果加水平排版，rtl 才會顯著。SKILL.md 先講清楚這點避免 AI 誤解。
- **CLI 對非 JSON 檔處理**：glob 可能接到非 .json 副檔名。預計 `json.load` 失敗時回 exit 3 + 錯訊，不特別檢查副檔名。
- **AI 自檢迴圈上限**：沒設硬上限（3 次後放棄之類）；相信 AI 的 agentic loop 自己收斂。若後續觀察到無限迴圈再加。

---

## 12. 對未來 milestone 的影響

- **M3（shape_group + polygon split）**：新增 Layer 2 規則（`children` 長度 = 2、姊妹格共線）append 到 `_LAYER2_RULES`；`examples/` 新增 `06_slash_split/`
- **M4（polygon fallback）**：新增 polygon 自相交檢查；`examples/` 新增 `07_polygon/`
- **M5（webtoon + polish）**：補 Layer 3 pre-generation checks（若仍有需要）；`examples/` 新增 `08_webtoon_long/`
- 每個後續 milestone 都走相同的 spec → plan → implement 流程
