# ppt-reflex · Correct PowerPoint without a vision model

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-110%20passing-brightgreen.svg)](ppt_reflex/grid/tests/)
[![Version](https://img.shields.io/badge/version-1.0.0-536DFE.svg)](pyproject.toml)
[![Vision-free](https://img.shields.io/badge/vision-free-8e44ad.svg)]()
[![DSH plugin](https://img.shields.io/badge/DSH-dynamic%20plugin-536DFE.svg)]()

**ppt-reflex is an engine that lets LLMs without vision produce *correct* PowerPoint decks — plus a DeepSeek Harness (DSH) plugin that adds live preview and a feedback loop.**

Blind LLMs — DeepSeek first, but any text-only model — cannot see the `.pptx` they generate. The usual workaround makes the model guess harder: it writes coordinates, crosses its fingers, and hopes. ppt-reflex inverts that pipeline. The AI never writes a coordinate and never guesses how anything looks. It declares **layout intent** — an archetype, parameters, a recipe, a decoration skin — and a deterministic constraint-solving engine computes every coordinate, measures every glyph, and reports back in text.

Three things replace vision:

1. **Real font measurement** — PIL glyph-level FreeType metrics (CJK-aware, East Asian Width-aware) compute how much space text actually needs *before* render.
2. **Structured diagnostics** — every build returns machine-readable issues with `phase`, `kind`, `severity`, `message`, and `options` the AI can act on.
3. **Three-tier ASCII feedback** — an L0 structure map, an L1 element map, and an L2 numeric text table give the model a "picture" it can actually read.

The AI reads the diagnostics, edits its declaration, and re-runs. A `CircuitBreaker` watches for mechanical micro-adjustments and forces a design-level rethink before the loop burns itself out.

## The Agent-Engine Loop

```
            ┌─────────────────────────────────────────────┐
            │                LLM AGENT                    │
            │      (no vision — reads JSON, not pixels)   │
            │                                             │
            │   ① declare intent                          │
            │      archetype + params + recipe + skin     │
            │   ② read diagnostics + L0/L1/L2 ASCII       │
            │   ③ decide fix → declare_direction()        │
            └───────────────┬─────────────────▲───────────┘
                            │                 │
              declaration   ▼                 │  diagnostics (JSON)
                            │                 │  + three-tier ASCII
            ┌───────────────▼─────────────────┴───────────┐
            │            ENGINE (deterministic)           │
            │  resolve archetype → phase1 layout →        │
            │  collision → composition → WCAG contrast →  │
            │  PIL text metrics → freeze → roundtrip      │
            │                                             │
            │  CircuitBreaker guards the fix loop         │
            └───────────────┬─────────────────▲───────────┘
                            │                 │
                  build()   ▼                 │  fix_slide() / rebuild()
                            │                 │
             .pptx written — ok:true = visually correct
```

**It is not "AI generates, human fixes." It is "AI declares, engine computes, AI reads, AI decides, loop."** Every LLM can read JSON. That is the whole trick.
**Design philosophy — the engine speaks the AI's own language.** The declaration layer is deliberately HTML/CSS-isomorphic: the model's deepest muscle memory. `grid_cards` reads like a CSS grid, `fit_mode` accepts `contain`/`cover` like `object-fit`, `density` accepts `comfortable`/`spacious`, `recipe` works like a component class. This is **not** HTML→PPTX conversion — nothing ever renders from HTML; the engine only borrows the vocabulary so a blind LLM can drive layout with knowledge it already has. The mapping lives in one place: `ppt_reflex/grid/agent_vocabulary.py`.


## Features

- **Blind-LLM friendly by design.** The AI writes no coordinates and no raw `python-pptx` calls. It declares *what* it wants — `archetype`, `params`, `recipe`, `frame/rail/corner_mark` — and the engine solves *where*.
- **Deterministic constraint solver.** Coordinates come from a reproducible pipeline, not from a sampled model. Same declaration → same layout, every time.
- **Real font measurement.** `text_metrics.py` measures glyph advances with PIL/FreeType against Microsoft YaHei (CJK-capable), falling back gracefully. Overflow is caught *before* the file is written, with the exact point deficit.
- **Structured diagnostics.** `{slide, phase, kind, severity, message, options}` per issue, deduplicated and batch-collapsed so the agent reads a clean feed, never a log flood.
- **Three-tier ASCII feedback.** `L0` structure map (regions, skins, fills) · `L1` element map (one letter per element, `#` overlap, `!` overflow) · `L2` numeric text table (font size, line count, height, overflow pt).
- **Guaranteed-fix loop.** The AI declares a fix direction (`b.declare_direction("split_slide")`) and re-runs. `CircuitBreaker` escalates: same direction twice → WARN, three times → BLOCK; three different mechanical tweaks → BLOCK; error-count stagnation → "stop micro-tuning."
- **Real-time visualization (DSH plugin).** A `shell.overlay` panel previews each slide as it builds; per-element frames stream in real time. You can click an element, drag-box select, request a recolor, or flag a problem.
- **Two-level correctness floor.** `geometry_ok` (zero geometric errors) and `harmony_ok` (zero aesthetic-rule violations) — both verifiable floors, never taste. The ceiling is the human at the panel.
- **Harmony rules, OKLCH-measured.** 60-30-10 area color ratio, focal-point uniqueness, hue harmony (mono/analogous/complementary/triadic) — all measured in OKLCH, all thresholds centralised in `grid/rules.json`.
- **Entry discipline.** `PPTBuilder(strict_tokens=True)` by default rejects raw colors and hand-written coordinates with `raw_color_forbidden`; the human panel path stays exempt — humans are the ceiling and may override (override-triggered contrast issues surface as `human_override_warning`).
- **Aesthetic judgment stays human.** Palettes, hex codes, and presets are human-curated assets. The engine only enforces the *objective* floor — WCAG AA contrast (≥ 4.5:1) and legibility — and never pretends to have taste.
- **Design tokens + recipes as human assets.** `tokens.json` / `recipes.json` hold tiered values (spacing, radius, shadow, type scale, color) and named components (`card`, `kpi`, `quote`). The AI references *level names*, never raw numbers; humans own the values.

## What's new in v0.6.0

| Change | What it means |
|:--|:--|
| **Theme layer removed** | No more semantic-template indirection. `template + style + overrides` is the whole story. |
| **Parameterized primitives** | `grid_cards` accepts `columns` (1–4), `gap` (pt), and `density` (`compact`/`normal`/`airy`); the engine computes the grid. |
| **Design tokens + recipes** | `tokens.json` + `recipes.json` + `get_token()` / `resolve_recipe()`; recipes `card`, `kpi`, `quote` pre-resolve token values. |
| **Decoration skins** | `frame="top_bottom_band"`, `rail="left"|"right"`, `corner_mark="tl"|"tr"` — geometry is engine-solved, not hand-written. |
| **PIL real font measurement** | Glyph-level FreeType advances replace em-based estimation. |
| **ASCII layered feedback** | `L0`/`L1`/`L2` — structure, elements, and numeric text precision. |
| **Render hook** | `set_render_frame_hook(fn)` fires per element before draw — the streaming-preview bridge. |
| **DSH plugin bridge** | `_dsh_ppt_runner.py` — stdin JSON in, result JSON out, with streaming frames and ASCII attached. |

## What's new in harmony v1 (supersedes v0.6.0)

| Change | What it means |
|:--|:--|
| **OKLCH colour core** | `grid/oklch.py` — sRGB↔OKLCH, hue distance, chroma/lightness helpers |
| **Two-channel diagnostics** | violations → `error`/`warning` (block `ok`); signals → `advisory` (never trimmed, never batch-folded) |
| **Area-based colour ratio** | 60-30-10 bands measured by filled area; images enter via PIL dominant colour (`image_style_conflict` signal) |
| **Focal-point uniqueness** | exactly one focal element per page (`focal_point.missing` / `split` / `ambiguous`) |
| **Hue harmony** | mono / analogous / complementary / triadic, all in OKLCH; ≤2 high-chroma families per page |
| **Entry discipline** | `strict_tokens=True` by default; agent-facing docstring rewritten without raw colours or coordinates |
| **CSS-isomorphic vocabulary** | `contain`/`cover`, `comfortable`/`spacious`, `radius` alias; CSS hallucinations rejected with alternatives |
| **Region diagnostics** | `inspect_slide(idx, elem_ids)` + `runner --inspect` — pure in-memory, T5-consistent schema |
| **Dual gate** | `geometry_ok` (zero geometry errors) **and** `harmony_ok` (zero harmony violations) — both must pass before presenting |
| **Page summaries** | `page_summaries` per-page aggregation — read first, drill into `diagnostics` only when pointed |
| **Persistent circuit breaker** | `build_count` accumulates across processes in `_breaker_state.json`; `hard_blocked` / `blocked_fingerprints` / `entropy_stalled` in every result |
| **Watcher auto-build** | the host watcher builds from `_deck_auto.json` — writing the deck file *is* the build trigger |
| **`ppt_build` tool** | host-registered explicit operations: `build` / `renderSlides` / `inspect` |
| **Recipe theme remap** | recipe fills resolve through the active style palette (dark templates no longer produce light-card/dark-text) |
| **Adaptive headers** | header height follows the resolved title size instead of a fixed 72 pt |
| **Bidirectional ink contrast** | dark-fill→white *and* light-fill→ink text colour both resolved from luminance |

## Quick Start

### Install

```bash
git clone <this-repo> && cd <repo>
pip install -e .
```

Python 3.10+. Two runtime dependencies: `python-pptx` and `Pillow`.

### Minimal deck

```python
from ppt_reflex.builder import PPTBuilder

b = PPTBuilder(template="business", style="corporate_minimal")  # strict_tokens=True by default

b.add_slide("Why This Exists",
    archetype="content",
    elements=[
        b.title("python-pptx Is Blind"),
        b.bullet("Text overflow and invisible text are silent failures"),
        b.bullet("ppt-reflex adds a pre-render diagnostic pass"),
        b.box("Every LLM can read JSON.\nNo vision required.",
              recipe="card"),   # colors come from template + style + recipe tiers — never raw
    ],
)

result = b.build("output.pptx")
print(result["summary"])
# → "3 issues (0 errors, 3 warnings)"
```

### Runner command (DSH stdin-JSON bridge)

```bash
python _dsh_ppt_runner.py < deck_request.json
```

`deck_request.json` (identical format to `_deck_auto.json` — the deck file is the full payload):

```json
{
  "action": "build",
  "template": "business",
  "style": "corporate_minimal",
  "output": "output.pptx",
  "slides": [
    {
      "title": "Why This Exists",
      "archetype": "content",
      "elements": [
        {"id": "t1", "type": "title", "text": "python-pptx Is Blind"},
        {"id": "b1", "type": "box", "text": "No vision required.",
         "recipe": "card"}
      ]
    }
  ]
}
```

### Result example

```json
{
  "path": "output.pptx",
  "ok": true,
  "geometry_ok": true,
  "harmony_ok": true,
  "summary": "0 issues — clean",
  "diagnostics": [],
  "design_hints": [],
  "page_summaries": [
    {"slide": 0, "elements": 2, "errors": 0, "harmony": 0, "signals": 0}
  ],
  "build_number": 1,
  "hard_blocked": false,
  "blocked_fingerprints": [],
  "entropy_stalled": false,
  "ascii": [ { "L0": "...structure map...", "L1": "...element map...", "L2": [ { "elem_id": "e_2", "font_size": 14, "overflow_pt": -6 } ] } ],
  "survey": { "topic": "…", "template": "business", "questions": "…" }
}
```

**Two gates, fixed in order:** `geometry_ok` (zero `error`-severity geometry violations) and `harmony_ok` (zero harmony `warning`s) are both verifiable floors. `ok: true` means the file is structurally correct; harmony warnings are must-fix before presenting; `advisory` signals should be eliminated when cheap but never block.

## DSH Plugin Workflow

The DSH plugin is a **host-composed Cordis plugin**: it lives in the profile bundle and patch layer, and the same profile is shared by the Web harness and the DSH Desktop harness — one install, both ends. The `slideReflex` service is provided by the host layer; the agent preset (`ppt-maker`) only scopes the panel via its client Gate and no longer re-mounts the plugin.

The conversation flow is a closed loop:

```
user says what they need
        │
        ▼
agent questionnaire (8 items, click-select; quick mode on "you decide")
   topic / audience / template / style /
   content source / images / slide count / density
        │
        ▼
generate deck (archetypes + params + recipes + skins)
        │
        ▼
write D:\ppt\_deck_auto.json  ──►  host watcher auto-builds
        │
        ▼
panel preview (shell.overlay), frames stream in real time
        │
        ▼
feedback loop
   click element · drag-box select · recolor request · problem flag
        │
        ▼
agent edits the deck file  ──►  watcher rebuilds  ──►  preview again
```

**Build trigger = writing the deck file.** The host watcher watches `D:\ppt\_deck_auto.json`; on change it runs the engine and streams frames to the panel — the agent never invokes the runner to build (that is escape-only). For an immediate rebuild or a visual check, the host-registered **`ppt_build`** tool offers three actions: `build` (rebuild from the deck), `renderSlides` (PNGs under `_render_vision/`), and `inspect` (region-scoped diagnostics for the feedback protocol).

**Panel preview** renders at the same 960×540 coordinates the `.pptx` will use — same deterministic pipeline, two render targets. Per-element frames are pushed in real time through `set_render_frame_hook`, so you watch elements land one by one.

**Workflow file bridge** (the plugin and the agent exchange state through JSON files):

| File | Purpose |
|:--|:--|
| `_deck_auto.json` | Deck plan (slides, archetypes, elements) — **the only file the agent touches** |
| `_frames_auto.jsonl` | Build frames — the panel polls this for its preview |
| `_feedback_auto.json` | User problem feedback from the panel (inlines the affected element's text) |
| `_selection_auto.json` | Element selection (click / drag-box) |
| `_palette_auto.json` | Panel palette — **merged into `overrides` by the runner/host, never by the agent** |
| `_breaker_state.json` | CircuitBreaker persistence (build counts per deck fingerprint, across processes) |

## API Overview

| API | Signature | Purpose |
|:--|:--|:--|
| `PPTBuilder` | `PPTBuilder(template, style, overrides, page_w=960, page_h=540)` | Sole AI entry point; lazy template + style load |
| `add_slide` | `add_slide(title, *, archetype, params, regions, elements, arrows, frame, rail, corner_mark)` | Declare one slide; archetype auto-routes elements into zones |
| `title / subtitle / text / bullet / footer` | `(text, *, style, region)` | Text primitives |
| `box` | `(text, *, recipe, fill_color, shape_id, …)` | Card component; `recipe` = `card`/`kpi`/`quote` |
| `shape` | `(shape_id, *, fill_color, pw, ph, text, …)` | 20 shapes; shape-inline text auto-centers |
| `image` | `(path, *, fit_mode, layout_mode, caption)` | Contain-fit; `layout_mode` or `auto_layout_mode()` |
| `table` | `(headers, rows, *, region)` | Auto-sized table, accent header row |
| `divider / arrow` | — | Decoration, always safe |
| `build / build_stream` | `(path)` | Full build (one-shot) or per-slide streaming generator |
| `fix_slide / rebuild` | `(idx, …)` / `(changed_slides, path)` | In-place edit + hash-cached incremental rebuild |
| `verify` | `(path)` | Reopen `.pptx`, pure-geometry structural check (no vision) |
| `declare_direction` | `(direction)` | Declare fix strategy to the CircuitBreaker (17 verbs, see SKILL §12) |
| `inspect_slide` | `(idx, elem_ids)` | Pure in-memory region inspection for the feedback protocol |
| `set_render_frame_hook` | `(fn)` | Per-element callback for streaming previews |
| `list_templates / list_style_presets / list_archetypes` | `()` | Lightweight catalogs for the agent to browse |
| `get_token / resolve_recipe` | `(category, level)` / `(name)` | Design-token and recipe resolution |

**12 layout archetypes:** `title_cover` · `content` · `two_column` · `comparison` · `data_showcase` · `grid_cards` · `image_hero` · `conclusion` · `section` · `quote` · `timeline` · `blank`.

**6 templates:** `academic` · `business` · `minimal` · `data_report` · `teaching` · `product`.
**6 style presets:** `academic_rigorous` · `corporate_minimal` · `tech_dark` · `editorial_magazine` · `creative_vibrant` · `government_solemn`.

## Escape Hatches

The engine is a floor, not a ceiling. Three layers let the agent take back control when a declaration is not expressive enough:

1. **Hand-written regions.** Skip the archetype entirely and pass explicit `regions=[("name", x, y, w, h, z), …]`. You get the diagnostics and the fix loop even on fully manual layouts.
2. **Element parameters.** Every primitive accepts explicit overrides — `pw`/`ph`, `fill_color`, `corner_radius`, `align_h`, `font_size`. Declarative defaults, imperative escape.
3. **Agent takeover code.** When neither is enough, drop to raw `python-pptx` (or the `officecli` skill) for that one slide. The engine's value is the *loop*, not a lock-in.

## Roadmap

- **Golden-set regression (T6)** — baseline of ≥10 "beautiful" + ≥10 "ugly" decks with expected pass/block per rule; `make golden` diffs pass/intercept rates against `tests/golden/baseline.json` and fails on any regression. Threshold changes in `rules.json` must run it. *(baseline + runner + 110 passing tests landed in harmony v1)*
- **Harvest golden cases** from real feedback (`_feedback_auto.json` history: user-"ugly" = negative, accepted decks = positive) via `tools/golden_harvest.py`.
- **More recipes and tokens** — grow the human-curated asset layer (`kpi` variants with `value_size` for unambiguous focal hierarchy, data-table recipes).
- **More parameterized primitives** — bring `columns`/`gap`/`density`-style parameters to more archetypes.
- **Reference-PPTX layout extraction** — `layout_extractor.py` already infers zones from an existing deck; wire it into `register_archetype()`.
- **Full ASCII → diagnostic cross-linking** — make every `#`/`!` in the L1 map clickable to its JSON diagnostic.

---

**ppt-reflex** is MIT licensed. Built for AI agents. Blind-proof by design — `ok: true` means the file is correct, and no one had to see it.
