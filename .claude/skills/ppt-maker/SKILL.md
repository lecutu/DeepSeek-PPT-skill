# ppt-maker — PPT Creation Operating Manual (ppt-reflex harmony v1)

**This file is the single source of truth for the agent-facing ppt-reflex API (harmony v1, supersedes v0.6.0).** It is written for a fresh agent with no memory and no source-code access. Do **not** read `ppt_reflex/` or `grid/` source — the only exceptions are Escape Hatch L3 (§13) and the single-source vocabulary file `grid/agent_vocabulary.py` (§6). If something is not described here, it does not exist.

---

## 1. What this system is

Two cooperating surfaces:

| Surface | What it does | Agent's role |
|:--|:--|:--|
| **Engine** `ppt-reflex` harmony v1 | AI declares *layout intent* (`archetype` / `params` / `recipe` / `deco`); a constraint-solver computes coordinates; emits **dual-channel** structured diagnostics (violations `error`/`warning`, signals `advisory`) + ASCII feedback; supports a repair loop with a circuit breaker. No vision model needed. | Declare intent, read diagnostics, iterate. |
| **DSH plugin** (dynamic Cordis plugin `ppteg-1`, panel **`▸ PPT 预览`**) | User states a need in conversation → agent generates a deck → build frames are written to a file → panel previews page by page → user clicks / box-selects / changes colors / asks questions as feedback. | Run the file bridge, react to feedback. |

The agent never types raw coordinates or raw colors. It declares **what** it wants; the solver returns **where** things go.

---

## 2. Golden rules (read first)

1. Declare layout intent, never hand-write coordinates (except the escape hatches in §13).
2. Never write raw colors — relay preset names or the user's hex verbatim. Strict mode (default) rejects every raw color token with `raw_color_forbidden`; panel color edits run under `strict_tokens: false` and are the **human's** job (§4).
3. This file plus `grid/agent_vocabulary.py` (the single source of the CSS vocabulary, §6) are the only API references; do not read other engine source (except Escape Hatch L3).
4. Ask every missing questionnaire item exactly once; never guess (quick mode exempts you — §3).
5. Repair order: **geometry errors first → harmony violations next (must fix) → signals last (should eliminate)** (§12).

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

### Quick mode (user grants full discretion)

When the user explicitly authorizes "其他全由你发挥" / "随便" / "you decide" (or equivalent), **skip the per-item loop** — ask only the **topic** and proceed with the defaults:

| Item | Quick default |
|:--|:--|
| template | `business` |
| style | `corporate_minimal` |
| page count | 8 |
| density | `comfortable` (→ `normal`) |

Audience / occasion / colors / images fall back to the `business` + `corporate_minimal` preset contract (engine-owned hues). State the adopted defaults in one line so the user can override; anything they name later is applied on the next build.

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
    strict_tokens=True,          # default; the only mode the agent uses
)
```

> **The `theme` parameter has been removed.** Use `template` + `style`.
>
> **`strict_tokens=True` is the entry discipline (default).** The engine rejects
> every raw color token with `raw_color_forbidden` — `overrides` keys other than the
> two below, `box(fill_color=...)`, `shape(fill_color=/font_color=/font_size=)`,
> `arrow(color=/text_color=)`, `divider(color=)`. The agent never sets raw colors:
> colors come from the template + style + recipe tiers.
>
> **`overrides` is restricted to the palette relay.** Only `bg_hex` and
> `accent_hex` are accepted in strict mode (they carry a palette choice and are
> exempt from `raw_color_forbidden`); every other override key is rejected. Set them
> **only to relay a hex the user gave in conversation** — never read or merge
> `_palette_auto.json` yourself, the runner/host does that (§10). The human panel
> rebuilds with `strict_tokens: false` to exercise the remaining escape-hatch colors
> — that is the human's job, never yours.

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

### params — `grid_cards` only

Only `grid_cards` accepts `params`; any other archetype + any other key is rejected by the engine:

| param | values |
|:--|:--|
| `columns` | 1–4 |
| `gap` | pt (positive) |
| `density` | `compact` \| `normal` \| `airy` — CSS aliases accepted: `cozy`→`compact` · `comfortable`→`normal` · `spacious`→`airy` |

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

- `fill_color` is an RGB tuple `(R, G, B)` — **forbidden in strict mode**: the engine raises `raw_color_forbidden` and points at the recipe/style tier that owns the color.
- `box(recipe="kpi"|"quote")` pulls from the design-token recipes (§7).
- **CSS vocabulary — single source `grid/agent_vocabulary.py`.** The agent-facing surface accepts the CSS-flavored word for a thing alongside the internal enum; the tables below are **generated from that file** (the prompt vocabulary section is never hand-synced). When in doubt, read `grid/agent_vocabulary.py` — this is the sanctioned exception to golden rule 3.

| Domain | CSS vocab → internal |
|:--|:--|
| `image.fit_mode` | `contain`→`fit` (no crop, letterboxed) · `cover`→`fill` (crop to fill) · `crop`→`crop_center` · `fit` / `fill` / `crop_center` |
| `params.density` | `comfortable`→`normal` · `spacious`→`airy` · `cozy`→`compact` · `compact` / `normal` / `airy` |
| `box()` kwarg | `radius`→`corner_radius` |

**CSS hallucinations are rejected** (the error names the alternative):

| Rejected kwarg | Alternative |
|:--|:--|
| `margin` | margins are engine-solved — use `params.density` (comfortable/normal/airy) or an archetype's preset regions |
| `spacing` | spacing vocabulary lives in the `params.density` tier, not on an element |
| `padding` | internal padding comes from a recipe (`card`/`kpi`/`quote`) or tokens |
| `gap` | `gap` is an archetype param — `grid_cards` `params={"gap": <pt>}` |
| `z_index` / `zindex` | z-order is engine-solved from semantic role — use `role="emphasis"` / `"backdrop"` |
| `position` / `float` / `display` | placement is engine-solved from archetype regions |
| `border` | borders are engine-solved — use a recipe or the template contract |
| `box_shadow` | shadows come from the style preset / recipe, not a raw value |
| `opacity` | opacity is not an agent token — pick a style tier instead |
| `line_height` | line height is the template contract (`line_spacing`) |
| `text_align` | alignment is the `align_h` kwarg (`left`/`center`/`right`) |

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
| `L1` | element map — `#` marks overlap, `!` marks overflow, `?` marks a signal element | 20 pt per cell |
| `L2` | text numeric table | — |

---

## 9. Runner bridge (JSON over stdin) — escape path

The engine is driven through `D:\ppt\_dsh_ppt_runner.py`: it reads **one JSON object on stdin** and writes JSON to stdout. **In the normal workflow you never invoke this yourself** — the host watcher builds automatically from `_deck_auto.json` (§10). This section documents the native contract (the deck file uses the same format) and is the escape hatch when the watcher is unavailable.

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
  "frames_out": "D:/ppt/_frames_auto.jsonl",
  "direction": "reduce_text",   // optional: declare_direction() verb for this repair build (§12)
  "round": 2,                   // optional: repair round number (breaker bookkeeping)
  "render_png": true            // optional: also render slides to PNG → rendered_slides
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

Element fields by type: `title/subtitle/text/bullet/footer` → `{id, type, text, style?}` · `box` → `{id, type, text, recipe?, style?, fill_color?: [R,G,B], shape_id?, ph?, align_h?}` · `shape` → `{id, type, shape_id, fill_color?, pw?, ph?, text?}` · `image` → `{id, type, image_path, fit_mode?, layout_mode?, caption?}` (fit_mode: `contain`/`cover`/`fit`/`fill`/`crop_center`, default `fit`) · `table` → `{id, type, headers: [...], rows: [[...]]}` · `divider` → `{id, type}`.

### Inspect — region-scoped inspection (read-only, pure memory)

Two ways to trigger the same read-only inspection:

- **Preferred — the `ppt_build` tool:** call it with `action=inspect` and params `deck` / `slide` / `elem_ids` (host-registered tool; returns `builder.inspect_slide(slide_idx, elem_ids)`).
- **Fallback — bash escape** (only when the tool is unavailable): `python D:\ppt\_dsh_ppt_runner.py --inspect <deck.json> <slide_idx> [elem_id ...]`

Both solve the slide in memory — **never render, never write a PPTX**. Returns:

- `supply` (L0 overview: zones, free rects, density) · `spatial` (nearest-neighbor, alignment groups, gap matrix) · `profile` (inferred decorative/title/footer roles) · `overlap`
- `violations` / `signals` — dual-channel diagnostics scoped to the slide
- with `elem_ids`: a scoped `region` block adds local metrics — `local_density` vs page mean, in-region alignment residual, gap-sequence rhythm, font-size hierarchy levels, pairwise contrast, local color ratio

Run it **before** proposing feedback options (§11).

### stream mode (`"stream": true`)

stdout is JSONL — one object per line. Frame lines come first, then the final result:

```
{"frame": {"clear_slide": ..., "slide": 0}}
{"frame": {"slide": 0, "kind": "...", "elem_id": "...", "text": "...", "x": ..., "y": ..., "w": ..., "h": ..., "fill": ..., "font_size": ...}}
...
{"result": {"path": "...", "ok": ..., "geometry_ok": ..., "harmony_ok": ..., "diagnostics": [...], "design_hints": [...], "build_number": ..., "hard_blocked": ..., "summary": "...", "template": "...", "style": "...", "ascii": [{"L0": "...", "L1": "...", "L2": "..."}], "survey": ...}}
```

- The last line is always the `result` object. Its key fields:

| Field | Meaning |
|:--|:--|
| `ok` / `geometry_ok` | zero geometry errors (`severity: "error"`) — the build gate |
| `harmony_ok` | zero error/**warning** among the harmony rules — the aesthetic gate (§12) |
| `diagnostics` | aggregated; signals (`advisory`) are **never trimmed** |
| `design_hints` | design-policy hints + circuit-breaker escalations |
| `build_number` | breaker build count (persists across processes) |
| `hard_blocked` | true when the breaker has BLOCKed a fingerprint → `ok` false regardless |
| `blocked_fingerprints` | which `(slide, kind, elem_id)` fingerprints are blocked |
| `entropy_stalled` | true when recent builds show no error change (stop micro-tuning) |
| `collapsed` | dedup / batch / trimmed counters |
| `page_summaries` | per-page aggregated summary — **read this first**, not the raw diagnostic list |
| `rendered_slides` | present when `render_png`/`render_dir` is set: `[{slide, path, width, height}]` — PNGs under `D:\ppt\_render_vision\slide_XX.png` |
| `survey` | injected by the plugin |

Prefer `page_summaries` + `design_hints` + `summary` over the full `diagnostics` array; drill into `diagnostics` only when a summary points at a specific slide/element.

- `ascii` is a list of per-slide `{L0, L1, L2}` objects.

### non-stream mode

stdout is **one line**: the `result` JSON only.

---

## 10. DSH workflow — the file bridge (mandatory)

The host watcher watches `D:\ppt\_deck_auto.json`: **writing the deck file is the build trigger.**

### Tools overview

Four layers (four tool surfaces):

| Layer | Tools | Use |
|:--|:--|:--|
| ① File tools (preset) | `fs-local` + `str-replace-editor` — write / edit `_deck_auto.json` | **default build path** — write the file, the watcher builds and streams frames to the panel |
| ② `ppt_build` (host-registered) | explicit engine operations — protocol table below | immediate result / visual PNG / region diagnostics |
| ③ bash (preset) | `persistent-bash` | **escape only** — runner CLI / manual checks |
| ④ Host global + MCP (auto, no preset declaration) | `todo` / `goal` / `subagent` / `web_search` / `skill` / `workflow` / `jobs` / `ask-user` · MCP: `zotero` / `paper-distill` / `academic-research` / `pubchem` / `obsidian` | content research (MCP / web_search); `skill` loads this manual (`D:\ppt\.claude\skills\ppt-maker\SKILL.md`) |

**Usage rule:** default = write the deck file and wait for the watcher auto-build; content research = MCP / web_search; immediate result / visual PNG / region diagnostics = `ppt_build`; full manual = `skill`; bash = escape only.

**`ppt_build` action protocol:**

| action | Params | Returns | Use for |
|:--|:--|:--|:--|
| `build` | `deck` (defaults to `_deck_auto.json`), plus the payload fields (`template` / `style` / `overrides` / `slides` / `direction` / `round`) | `{ok, geometry_ok, harmony_ok, diagnostics, page_summaries, summary}` | immediate rebuild; explicit trigger when the watcher is unavailable |
| `renderSlides` | — | `rendered_slides: [{slide, path, width, height}]` — PNGs under `D:\ppt\_render_vision\slide_XX.png` | visual verification & delivery |
| `inspect` | `slide` (int), `elem_ids` (optional) | `builder.inspect_slide(...)` region evidence (§9) | feedback protocol (§11) |

The agent follows these steps in order:

| Step | Action |
|:--|:--|
| 1 | User states need in conversation → run the questionnaire (§3, incl. quick mode). |
| 2 | Generate the deck → write `D:\ppt\_deck_auto.json` (the **only** file you touch). |
| 3 | **Wait for the auto-build.** The watcher picks up the file, builds, and streams frames to the panel. Do **not** run the runner yourself. For an immediate rebuild — or when the watcher is unavailable — call `ppt_build` `action=build` instead. On a repair round, write `"direction"` (a §12 verb) and `"round"` into the deck file before it triggers. |
| 4 | Tell the user to open the panel **`▸ PPT 预览`** (if not already open). For a visual check before delivery, call `ppt_build` `action=renderSlides` and review `D:\ppt\_render_vision\slide_XX.png`. |
| 5 | Handle feedback (§11) → edit the deck file; the watcher rebuilds automatically. |

- `_deck_auto.json` is the full build payload minus palette: `template` / `style` / `overrides` (relay-only, see below) / `slides` — each slide carries `archetype`, `params`, `frame` / `rail` / `corner_mark`, `elements`, `arrows` — plus optional `direction` + `round`.
- **Palette merge is the runner/host's job, never yours.** `_palette_auto.json` is merged into `overrides` by the host before building (conversation hex wins over palette). Set `overrides.accent_hex` / `overrides.bg_hex` yourself **only** to relay a hex the user gave in conversation.
- Manual runner invocation (`python _dsh_ppt_runner.py < deck.json`, §9) is **escape-only** — for when the watcher is unavailable; the deck JSON format is identical.

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
| `color` | panel — already auto-applied (it rebuilds with `strict_tokens: false`); agent ignores it |
| `question` | agent |
| `area` | agent |

Feedback requests and selection data now **inline the affected element's text** — a single read of `_feedback_auto.json` gives you the slide, `elem_id`, the element text, and the user's words. Do **not** cross-read `_selection_auto.json` to reconstruct context.

### Region-feedback protocol (run before offering options)

For `area` / `question` feedback, first cross the fuzzy word with region evidence via inspection (§9):

- **Preferred:** call the `ppt_build` tool with `action=inspect` (params: `deck`, `slide`, `elem_ids`).
- **Fallback:** if `ppt_build` is unavailable, the bash escape `python D:\ppt\_dsh_ppt_runner.py --inspect <deck.json> <slide_idx> [elem_id ...]`.

| User says | Inspect → read | Fix verbs (must be §12 directions) |
|:--|:--|:--|
| "crowded" / 挤 | `region.local_density`, `gap_sequence_std_pt` | lower the density tier, or `remove_elements` / `reduce_text` |
| "messy" / 乱 | `region.font_size_levels`, `alignment_residual_pt`, `focal_point` | `switch_layout` / `switch_region_order` / `rearrange_regions` |
| "ugly" / 丑 | `region.local_color_ratio`, `pairwise_contrast`, `hue_harmony` | `switch_style` / `switch_template`, or change `recipe` |
| "hard to read" / 看不清 | `pairwise_contrast` + `tri_*` diagnostics | `dark_to_light` / `light_to_dark` / `switch_template` — fix the scheme, never single colors |

When feedback is vague, offer **2–3 concrete options** and let the user choose. If the user cannot decide, produce a **dual-option comparison** (two variants side by side).

---

## 12. Diagnostic repair loop

### Reading the result

- Read `page_summaries` (per-page aggregation) + `design_hints` + `summary` **first**; drill into the full `diagnostics` array only when a summary points at a specific slide/element.
- Two-level handling: `error` = **must fix** (blocks the build gate); `warning` = **suggest** — fix when cheap; harmony warnings stay must-fix before presenting (below).

Two gates, fixed in order (golden rule 5):

1. **Geometry** — when `ok` / `geometry_ok` is `false`, fix every `severity: "error"` violation first (they block the build).
2. **Harmony** — when `harmony_ok` is `false`, fix every harmony **violation** (`severity: "warning"`, `harmony: true`) next. These do not block `ok`, but they are **must-fix before presenting**: the deck passes structurally while breaking the aesthetic floor.
3. **Signals** — `severity: "advisory"` (`channel: "signal"`) should be eliminated when cheap; they never block and are never trimmed, but lingering signals mark the deck as not-yet-polished.

### Dual-channel table

| Channel | severity | Gate | Kinds / rules |
|:--|:--|:--|:--|
| violation | `error` | blocks `ok` / `geometry_ok` | `overflow_vertical` · `silent_overflow` · `overlap` · `region_out_of_page` · `tight_gap` · … |
| violation | `warning` (harmony) | blocks `harmony_ok` | `color_ratio` · `focal_point.ambiguous` · `focal_point.split` · `hue_harmony` · `chroma_families` |
| signal | `advisory` | never blocks; never trimmed | `focal_point.missing` · `image_style_conflict` |

### Harmony rules (thresholds live in `grid/rules.json` v1.0.0 — never hard-coded)

| Rule | What it checks | Fix (declaration-level only — never direct colors) |
|:--|:--|:--|
| `color_ratio` | 60-30-10 by filled area, OKLCH hue families: dominant ≥50%, secondary ≤35%, accent ≤15% | rework the fill/image area ratio — recipe, style tier, element sizes/archetype |
| `focal_point.ambiguous` | ≥2 elements tie for the largest font size | make one element the unambiguous largest (style tier / structure) |
| `focal_point.split` | ≥2 elements qualify as the focal point (unique max, contrast ≥1.5×, ≥4% from edges) | demote secondary candidates so exactly one dominates |
| `focal_point.missing` | no element meets all focal conditions (signal) | set a unique largest-font-size focal element (title/heading) or a main hero image; keep it ≥4% of page width from the edges |
| `hue_harmony` | every hue-family pair must be monochrome/analogous (≤30°) / complementary (150–210°) / triadic (120±15°) in OKLCH | restrict to one hue family or a sanctioned pairing — via style/recipe/template |
| `chroma_families` | ≤2 high-chroma families (C > 0.15) | desaturate / merge — via style tier, never raw color |
| `image_style_conflict` | image dominant hue vs style accent within 30° analogous limit (signal) | swap the image, or choose a style whose accent is analogous |

### CircuitBreaker protocol

- **Declare before every repair build:** `builder.declare_direction("...")` or deck JSON `"direction": "..."`. The valid verbs (from `design_policy.py` — never invent new words):

  mechanical: `increase_box_height` · `increase_box_width` · `decrease_font_size` · `increase_region` · `rearrange_regions`
  content: `reduce_text` · `split_text` · `shorter_lines` · `remove_elements`
  layout: `split_slide` · `switch_layout` · `switch_region_order`
  color/scheme: `change_text_color` · `change_fill_color` · `switch_template` · `switch_style` · `dark_to_light` · `light_to_dark`
  (reserved: `unknown`)

- **Escalation** (per `(slide, kind, elem_id)` fingerprint): same direction **2× → WARN**, **3× → BLOCK**; **3+ different mechanical directions on the same error → BLOCK** (thrashing). A BLOCKed fingerprint sets `hard_blocked: true` and forces `ok: false` regardless of geometry; `blocked_fingerprints` lists them.
- **2 consecutive WARNs on the same violation → switch archetype** (a design-level change), then `clear_circuit_breaker()` (or a fresh runner process) — never keep micro-tuning the same spot.
- **Persistence:** `build_count` accumulates across processes in `D:\ppt\_breaker_state.json`, keyed by a deck fingerprint (archetype + element-kind sequence). Content edits do **not** reset it.
- **Entropy stall:** `entropy_stalled` when ~3 builds show error fluctuation <20% → stop micro-tuning, redesign.
- **Maximum 3 rounds** of repair. If still not clean, **degrade explicitly**: state that the declaration cannot express the need, mark the deck as degraded, and offer an escape hatch (§13).

---

## 13. Escape hatches — only when declarations cannot express the result

If a declaration cannot cover the requirement, **say so explicitly and degrade**; never force it.

| Level | What | When |
|:--|:--|:--|
| **L1** | Hand-write `regions` in the deck to override the archetype; use the `blank` primitive for fully manual layout. | Archetype geometry is insufficient. |
| **L2** | Override the solver with element params `pw` / `ph` / `align_h` / `role`. | Per-element fine control is needed. (`margin` is a rejected CSS kwarg — use density or regions.) |
| **L3** | Write Python in the conversation that calls the engine API / `python-pptx` / `officecli` directly to modify the file. | Nothing above suffices. |

L3 is the only case where reading engine source or bypassing the runner is permitted.

---

## 14. DON'T

1. Do **not** hand-write `regions` coordinates — except Escape Hatches L1 / L2 / L3.
2. Do **not** write raw colors (`fill_color`, `arrow(color=...)`, `divider(color=...)`, `overrides` beyond `accent_hex`/`bg_hex`) — `raw_color_forbidden`; relay presets or the user's hex verbatim; panel color edits are the human's job.
3. Do **not** read `grid/` (or `ppt_reflex/`) source — this file plus `grid/agent_vocabulary.py` are the sole fact sources; only Escape Hatch L3 is exempt.
4. Do **not** fix harmony violations by inventing colors or fine-tuning coordinates — change style/recipe/structure.
5. Do **not** ignore signals forever — eliminate `focal_point.missing` / `image_style_conflict` when cheap.
6. Do **not** keep repeating a blocked direction — the breaker counts; switch to an untried design-level direction.
7. Do **not** force a declaration that does not express the intent — degrade via an escape hatch.
8. Do **not** skip missing questionnaire items or guess — ask each missing item exactly once (unless quick mode is granted, §3).
9. Do **not** run the runner manually to build — the watcher auto-builds from `_deck_auto.json`; manual invocation is escape-only (§9).
10. Do **not** read or merge `_palette_auto.json` yourself — the runner/host does the palette merge (§10).
