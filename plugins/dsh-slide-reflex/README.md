# dsh-slide-reflex

DSH plugin bridging the [ppt-reflex](https://github.com/lecutu/DeepSeek-PPT-skill) engine (harmony v1) into DeepSeek Harness: a **PNG-based live preview panel** with click/box-select feedback loop. No vision model needed.

## Engine philosophy (引擎思想)

ppt-reflex is a **vision-free engine**: the agent never writes coordinates or raw colors — it declares a deck (archetypes, recipes, semantic intent), and the constraint solver computes layout/color/typography. The only ground truth is the **rendered output**. This plugin therefore previews the **real rendered PNGs** (engine-generated, 960×540 per page), not a canvas re-draw of intermediate state. Frames (`_frames_auto.jsonl`) are kept as the **element-geometry source** for click/box-select hit-testing; the visuals come from `_render_vision/*.png`.

## What it does

- **Host half** — a Typert Remote gateway (`slideReflex`) that:
  - runs a **deck watcher**: any change to `_deck_auto.json` auto-builds via the python runner and **auto-renders PNGs** (`<cwd>/_render_vision/slide_XX.png`) — the preview build is render-enabled;
  - owns the file bridge (`_deck_auto.json`, `_frames_auto.jsonl`, `_feedback_auto.json`, `_selection_auto.json`, `_palette_auto.json`, `_breaker_state.json`);
  - exposes the RPC surface (below) and the agent-facing `ppt_build` tool (build / renderSlides / inspect).
- **Browser half** — a panel injected into the conversation input bar (only for `ppt-maker` preset sessions): per-page **PNG preview** with page nav + thumbnails, click an element or drag-box-select an area (hit-tested against frame geometry), request recolors (auto-applied + rebuild), ask questions (forwarded to the agent), pick palette colors, switch zh/en.

## Preview loop (预览闭环)

```
user states need in chat → agent writes D:\ppt\_deck_auto.json
  → host watcher (800ms poll + 400ms debounce) auto-builds AND renders PNGs (~1-4s)
  → panel polls previewState (400ms) → epoch bump = new build → loads PNGs via slideImage
  → user sees the real rendered pages; clicks / box-selects / recolors / asks
  → feedback lands in _feedback_auto.json / _selection_auto.json
  → agent reads feedback → fixes deck → writes again → loop
  → user says "定稿" → final .pptx is produced (engine output, not a preview)
```

The panel fetches the host RPC endpoints directly (`POST /api/slideReflex/<method>`, `client-request` envelope) — no typert remotes mount chain, no `ctx.interval` dependency, and errors are shown in the panel status bar instead of being swallowed.

## RPC surface (`slideReflex` namespace)

| Method | Args | Returns |
|:--|:--|:--|
| `previewState` | — | `{ok, epoch, building, rendered:[{slide,file,mtime}], elements:{slide:[{elem_id,x,y,w,h,text}]}}` — latest rendered PNG list + per-slide element geometry (from frames file) |
| `slideImage` | `{request:{slide}}` | `{ok, slide, mtime, data}` — one rendered page as base64 PNG |
| `framesFile` | `{request:{since}}` | incremental frame stream (geometry/legacy; epoch bumps on completed builds, truncation rewind) |
| `build` | `{request:{...deck}}` | explicit build (no render unless requested) |
| `renderSlides` | `{request:{deck?, render_dir?}}` | explicit PNG render, returns `rendered_slides` |
| `loadDeck` / `loadPalette` | — | current deck / palette |
| `saveSelection` / `saveFeedback` / `savePalette` | `{request:{...}}` | write feedback bridges |
| `applyFeedbackBuild` | `{request:{requests}}` | apply color requests to deck + rebuild (strict_tokens off) |

Host `ppt_build` tool: `action="build" | "renderSlides" | "inspect"` (see tool description).

## Install

Add the bundle to a profile:

```jsonc
// $DSH_HOME/profiles/<name>/package.json
{
  "dependencies": { "dsh-slide-reflex": "file:path/to/dsh-slide-reflex" /* or npm version */ },
  "dsh": { "profile": { "bundles": ["dsh-slide-reflex"] } }
}
```

then `dsh plugin --profile <name> add dsh-slide-reflex` (or `pnpm install` in the profile directory) and restart DSH.

## Config (optional, in cordis.patch.yml)

```yaml
- insert:
    - id: dsh-slide-reflex
      name: dsh-slide-reflex
      config:
        python: 'C:\path\to\python.exe'
        cwd: 'D:\ppt'
        framesFile: 'D:/ppt/_frames_auto.jsonl'
        deckFile: 'D:/ppt/_deck_auto.json'
        feedbackFile: 'D:/ppt/_feedback_auto.json'
        selectionFile: 'D:/ppt/_selection_auto.json'
        paletteFile: 'D:/ppt/_palette_auto.json'
```

Defaults (index.js `DEFAULTS`) hard-code `D:\ppt` paths; `render_dir` is confined to `cwd` — absolute paths outside it fall back to `<cwd>/_render_vision`.

## Development / deployment (维护须知)

- **Source**: `D:\ppt\plugins\dsh-slide-reflex\` — edit here.
- **Deploy**: copy `lib/` + `typert.js` + `cordis.patch.yml` to the host-loading copy (`D:\dsh-plugins\dsh-slide-reflex\`); the profile's `node_modules\dsh-slide-reflex` is a symlink to it.
- **Host-side changes** (`index.js`, `typert.js`) require a **DSH restart** (no hot reload); the served **client bundle** refreshes on hard reload (Ctrl+F5) after copying `client.js`.
- Files are UTF-8 without BOM, LF line endings.

## Troubleshooting (排障速查)

| Symptom | Cause / fix |
|:--|:--|
| Panel blank, status "等待构建" | `_render_vision` empty → no build has rendered yet (write deck / check watcher). If status shows "出错: …" instead, the RPC failed — that text names the reason. |
| Panel shows stale pages | Hard-reload the page (Ctrl+F5); host restart required for host-side changes. |
| `previewState` HTTP 404 | Host runs old code → restart DSH. |
| Agent reports bash "terminal inspection unsupported" | Expected on win32 — shell group was removed from the preset; use `ppt_build` tool only. |
| Frames file empty / build_number jumps by 2 | Build failure mid-write or duplicate watch triggers; check the host console for runner stderr. |
| `dsh-plugin-desktop` load error in web profile | Unrelated: desktop-only plugin vs web mode; ignore or remove from the profile. |

## Vision channel (视觉通道)

The engine is vision-free, but its **rendered output is the ground truth** for everyone with eyes. PNGs land in `<cwd>/_render_vision/slide_XX.png` (960×540) through two paths:

| Path | Trigger | How |
|:--|:--|:--|
| **Implicit (auto)** | any watcher build (deck change) | watcher builds with `render_png: true`; preview renders come for free |
| **Explicit** | on demand | `slideReflex/renderSlides` RPC or `ppt_build action="renderSlides"` |

Consumers:

- **Humans** — the v3 panel shows these PNGs directly (no re-draw).
- **Vision-capable models / review agents** — read the PNG files as image input, e.g.:
  ```
  Inspect D:\ppt\_render_vision\slide_00.png and slide_01.png:
  1) any text overflow / clipped text (compare against expectations)
  2) visual crowding / alignment issues
  3) color harmony / contrast problems
  Then report concrete per-slide findings to fix in the deck.
  ```
- **Blind models** — keep the text/ASCII diagnostics: `ppt_build action="inspect"` (region geometry) plus the build result's `ascii` layout map.

Explicit render example:

```json
{ "action": "renderSlides" }   // via ppt_build; deck defaults to _deck_auto.json
// → { ok: true, rendered_slides: [ { slide: 0, path: "D:/ppt/_render_vision/slide_00.png", width: 960, height: 540 } ] }
```

`render_dir` is confined to the configured `cwd`; absolute paths outside it are ignored and the default directory is used instead.

## Known limitations

- Requires the ppt-reflex engine repo checked out at `cwd` with `_dsh_ppt_runner.py` present.
- Recolor requests apply to box/shape fill colors; semantic questions are forwarded to the agent, not auto-applied.
- Host defaults hard-code a Windows python path when no config row is given.
- Panel entry only appears in sessions composed from the `ppt-maker` agent preset (`agentPreset === 'ppt-maker'`).
- Box-select hit-testing relies on frame geometry; if frames are missing (failed build) the selection may be empty even though the PNG rendered.

## License

MIT
