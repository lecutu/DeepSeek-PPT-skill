# ppt-maker — PPT Creation Operating Manual (ppt-reflex v0.6.0)

**This file is the single source of truth for the ppt-reflex v0.6.0 API.** It is written for a fresh agent with no memory and no source-code access. Do **not** read `ppt_reflex/` or `grid/` source (the only exception is Escape Hatch L3). If something is not described here, it does not exist.

---

## 1. What this system is

Two cooperating surfaces:

| Surface | What it does | Agent's role |
|:--|:--|:--|
| **Engine** `ppt-reflex` v0.6.0 | AI declares *layout intent* (`archetype` / `params` / `recipe` / `deco`); a constraint-solver computes coordinates; emits structured diagnostics + ASCII feedback; supports a repair loop. No vision model needed. | Declare intent, read diagnostics, iterate. |
| **DSH plugin** (dynamic Cordis plugin `ppteg-1`, panel **`▸ PPT 预览`**) | User states a need in conversation → agent generates a deck → build frames are written to a file → panel previews page by page → user clicks / box-selects / changes colors / asks questions as feedback. | Run the file bridge, react to feedback. |

The agent never types raw coordinates. It declares **what** it wants; the solver returns **where** things go.

---

## 2. Golden rules (read first)

1. Declare layout intent, never hand-write coordinates (except the escape hatches in §13).
2. Never invent color values — relay preset names or the user's hex verbatim.
3. This file is the only API reference; do not read engine source (except Escape Hatch L3).
4. Ask every missing questionnaire item exactly once; never guess.

---

## 3. Questionnaire (8 items)

Before generating, collect all 8 items. Ask any **missing** item **once** via structured multi-select; do not re-ask answered items; never guess; never ask twice.

| # | Item | Options / format |
|:--|:--|:--|
| 1 | Topic | free text |
| 2 | Audience | executives · customers · colleagues · teachers · public |
| 3 | Occasion | work report · proposal · training · launch · defense |
| 4 | Page count | default **8** |
| 5 | Style | 6 presets (carry mood) — see §4 |
| 6 | Color scheme | a preset, **or** primary + background hex. **Relay only, do not create.** |
| 7 | Images | path list, in order (may be empty) |
| 8 | Density | compact · standard · airy |

---

## 4. Builder API — entry

```python
from ppt_reflex.builder import PPTBuilder, load_style_presets, list_archetypes
```

### PPTBuilder

```python
PPTBuilder(
    template="academic|business|minimal|data_report|teaching|product",
    style="academic_rigorous|tech_dark|corporate_minimal|editorial_magazine|creative_vibrant|government_solemn" | None,
    overrides={"bg_hex": "#...", "accent_hex": "#..."},
    page_w=960,
    page_h=540,
)
```

> **The `theme` parameter has been removed.** Use `template` + `style`.

**Templates:**

| id | vibe |
|:--|:--|
| `academic` | rigorous, high info density |
| `business` | professional, conclusion-first |
| `minimal` | breathing room, one message per slide |
| `data_report` | grid feel, data-dense |
| `teaching` | friendly, well-structured |
| `product` | premium, dark, centered |

**Styles (6 presets, carry mood):**

`academic_rigorous` | `tech_dark` | `corporate_minimal` | `editorial_magazine` | `creative_vibrant` | `government_solemn`

**Helpers:**

- `load_style_presets()` — list style presets and their fields.
- `list_archetypes()` — list the available primitives (§5).

### add_slide

```python
add_slide(
    title="",
    *,
    archetype=None,
    params=None,
    regions=None,
    elements=None,
    arrows=None,
    frame="",
    rail="",
    corner_mark="",
)
```

---

## 5. Primitives (archetypes), params, deco

### 12 primitives

`title_cover` · `content` · `two_column` · `comparison` · `data_showcase` · `grid_cards` · `image_hero` · `conclusion` · `section` · `quote` · `timeline` · `blank`

`blank` = **fully manual region** — you declare everything yourself.

### params

Only `grid_cards` takes `params`:

| param | values |
|:--|:--|
| `columns` | 1–4 |
| `gap` | pt |
| `density` | `compact` \| `normal` \| `airy` |

### Deco skins (engine computes geometry — do not write coordinates)

| key | values |
|:--|:--|
| `frame` | `top_bottom_band` |
| `rail` | `left` \| `right` |
| `corner_mark` | `tl` \| `tr` |

---

## 6. Element methods

| Method | Key parameters | Notes |
|:--|:--|:--|
| `title(text)` | `text` | slide/section heading |
| `subtitle(text)` | `text` | secondary heading |
| `text(text, style=...)` | `style="Body"\|"Subheading"\|"Caption"\|"Heading"` | body text |
| `bullet(text)` | `text` | one list item |
| `footer(text)` | `text` | footer line |
| `box(text, style, fill_color, shape_id, ph, align_h, recipe, corner_radius)` | `recipe="card"\|"kpi"\|"quote"` | card / KPI / quote container |
| `shape(shape_id, fill_color, pw, ph, text)` | `pw`/`ph` size | decorative or labeled shape |
| `image(path, pw, ph, fit_mode, layout_mode, caption)` | `path` | image |
| `table(headers, rows)` | `headers`, `rows` | data table |
| `divider(color)` | `color` | decoration |
| `arrow(from_elem_or_id, to, text, direction)` | `from`/`to` = element or id | connector |

- `fill_color` is an RGB tuple `(R, G, B)`.
- `box(recipe="kpi"|"quote")` pulls from the design-token recipes (§7).

---

## 7. Design tokens & recipes

```python
from ppt_reflex.grid.design_tokens import get_token, resolve_recipe
```

| Source | Contents |
|:--|:--|
| `tokens.json` | tiers for `spacing` / `radius` / `shadow` / `type_scale` / `color` |
| `recipes.json` | `card` / `kpi` / `quote` |

- `get_token(...)` — read a design-token tier.
- `resolve_recipe(...)` — resolve a named recipe (`card` / `kpi` / `quote`).

---

## 8. Archetypes, hooks, ASCII feedback

### resolve_archetype

```python
from ppt_reflex.grid.archetypes import resolve_archetype
```

Returns a **new, parameterized primitive instance** (clone an archetype with overridden params).

### set_render_frame_hook

```python
from ppt_reflex.builder import set_render_frame_hook

set_render_frame_hook(fn)   # fn(elem_id, content_type, payload, x, y, w, h)
```

Called **right before every element renders** — read-only observation (return value ignored); use it for streaming previews or inspection.

### render_slide_ascii

```python
from ppt_reflex.grid.ascii_map import render_slide_ascii
```

Returns `{ L0, L1, L2 }`:

| Level | Meaning | Grid |
|:--|:--|:--|
| `L0` | structure map | 40 pt per cell |
| `L1` | element map — `#` marks overlap, `!` marks overflow | 20 pt per cell |
| `L2` | text numeric table | — |

---

## 9. Runner bridge (JSON over stdin)

The engine is driven through `D:\ppt\_dsh_ppt_runner.py`. It reads **one JSON object on stdin** and writes JSON to stdout.

### catalog

```json
{"action": "catalog"}
```

Returns `templates` / `styles` (with accent + bg colors) / `archetypes`.

### build

```json
{
  "action": "build",
  "template": "...",
  "style": "...",
  "overrides": {"bg_hex": "#...", "accent_hex": "#..."},
  "page_w": 960,
  "page_h": 540,
  "output": "...",
  "slides": [ "..." ],
  "stream": true,
  "frames_out": "D:/ppt/_frames_auto.jsonl"
}
```

**`slides[].elements` types:**

`title` · `subtitle` · `text` · `bullet` · `box` (uses `recipe`) · `shape` · `image` (uses `image_path`) · `table` · `footer` · `divider`

**`slides[].arrows`:** `[{"from": ..., "to": ..., "text": ...}]`

**Minimal deck example** (one slide; every element has an `id`, text fields are short):

```json
{
  "action": "build",
  "template": "business",
  "style": "corporate_minimal",
  "output": "D:/ppt/out.pptx",
  "slides": [
    {
      "title": "Q3 Review",
      "archetype": "title_cover",
      "frame": "top_bottom_band",
      "rail": "left",
      "elements": [
        {"id": "t1", "type": "title", "text": "Q3 Review"},
        {"id": "s1", "type": "subtitle", "text": "Growth and risks"},
        {"id": "c1", "type": "box", "text": "Executive deck", "recipe": "card"}
      ],
      "arrows": []
    }
  ]
}
```

Element fields by type: `title/subtitle/text/bullet/footer` → `{id, type, text, style?}` · `box` → `{id, type, text, recipe?, style?, fill_color?: [R,G,B], shape_id?, ph?, align_h?}` · `shape` → `{id, type, shape_id, fill_color?, pw?, ph?, text?}` · `image` → `{id, type, image_path, layout_mode?, caption?}` · `table` → `{id, type, headers: [...], rows: [[...]]}` · `divider` → `{id, type}`.

### stream mode (`"stream": true`)

stdout is JSONL — one object per line. Frame lines come first, then the final result:

```
{"frame": {"clear_slide": ..., "slide": 0}}
{"frame": {"slide": 0, "kind": "...", "elem_id": "...", "text": "...", "x": ..., "y": ..., "w": ..., "h": ..., "fill": ..., "font_size": ...}}
...
{"result": {"path": "...", "ok": ..., "diagnostics": [...], "summary": "...", "template": "...", "style": "...", "ascii": [{"L0": "...", "L1": "...", "L2": "..."}], "survey": ...}}
```

- The last line is always the `result` object.
- `ascii` is a list of per-slide `{L0, L1, L2}` objects.

### non-stream mode

stdout is **one line**: the `result` JSON only.

---

## 10. DSH workflow — the file bridge (mandatory)

The agent must follow these steps in order:

| Step | Action |
|:--|:--|
| 1 | User states need in conversation → run the 8-item questionnaire (§3). |
| 2 | Generate the deck → write `D:\ppt\_deck_auto.json`. |
| 3 | Read `D:\ppt\_palette_auto.json` (panel palette, user-selected) → merge into `overrides`. Conversation-provided hex always wins. |
| 4 | Build: in `pwsh`, run the runner with the deck + `"stream": true` + `"frames_out"`. Redirect stdout if desired — frames go to the file. |
| 5 | Tell the user to open the panel **`▸ PPT 预览`**. |
| 6 | Handle feedback (§11) → on any change, re-run step 4. |

- `_deck_auto.json` mirrors the `build` payload's `slides` array: each slide carries `archetype`, `params`, `frame` / `rail` / `corner_mark`, `elements`, `arrows`.
- `_palette_auto.json` is the panel's color palette written from user selections; merge it into `overrides`, but conversation hex takes priority.

---

## 11. Feedback handling

Read `D:\ppt\_feedback_auto.json`:

```json
{
  "requests": [
    {
      "type": "color" | "question" | "area",
      "slide": 0,
      "elem_id": "..." | null,
      "color_hex": "#..." | null,
      "question": "..." | null,
      "area": {"x": 0, "y": 0, "w": 0, "h": 0} | null,
      "elems": ["..."] | null
    }
  ]
}
```

| `type` | Handled by |
|:--|:--|
| `color` | panel — already auto-applied; agent ignores it |
| `question` | agent |
| `area` | agent |

Resolve "this" / "that" references by reading `D:\ppt\_selection_auto.json`.

### Fuzzy-word mapping

| User says | Meaning → action |
|:--|:--|
| "crowded" / 挤 | lower the density tier, or delete elements |
| "empty" / 空 | raise the density tier, or add elements |
| "messy" / 乱 | change the primitive |
| "ugly" / 丑 | change `style` or `recipe` |
| "hard to read" / 看不清 | run a contrast diagnosis |

When feedback is vague, offer **2–3 concrete options** and let the user choose. If the user cannot decide, produce a **dual-option comparison** (two variants side by side).

---

## 12. Diagnostic repair loop

When `result.ok == false`, fix only the diagnostics with `severity == "error"`.

Kinds include: `overflow_vertical` · `silent_overflow` · `overlap` · `region_out_of_page` · `tight_gap` · …

Rules:

- Change the **declaration** (archetype / params / recipe / deco / element count) — never fine-tune coordinates.
- Maximum **3 rounds** of repair.

---

## 13. Escape hatches — only when declarations cannot express the result

If a declaration cannot cover the requirement, **say so explicitly and degrade**; never force it.

| Level | What | When |
|:--|:--|:--|
| **L1** | Hand-write `regions` in the deck to override the archetype; use the `blank` primitive for fully manual layout. | Archetype geometry is insufficient. |
| **L2** | Override the solver with element params `pw` / `ph` / `align_h` / `margin` / `role`. | Per-element fine control is needed. |
| **L3** | Write Python in the conversation that calls the engine API / `python-pptx` / `officecli` directly to modify the file. | Nothing above suffices. |

L3 is the only case where reading engine source or bypassing the runner is permitted.

---

## 14. DON'T

1. Do **not** hand-write `regions` coordinates — except Escape Hatches L1 / L2 / L3.
2. Do **not** create color values — relay preset names or the user's hex verbatim.
3. Do **not** read `grid/` (or `ppt_reflex/`) source — this file is the sole fact source; only Escape Hatch L3 is exempt.
4. Do **not** force a declaration that does not express the intent — degrade via an escape hatch.
5. Do **not** skip missing questionnaire items or guess — ask each missing item exactly once.
