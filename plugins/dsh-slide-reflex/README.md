# dsh-slide-reflex

DSH plugin bridging the [ppt-reflex](https://github.com/lecutu/DeepSeek-PPT-skill) engine (v0.6.0) into DeepSeek Harness: a live per-page preview panel with a click/box-select feedback loop. No vision model needed.

## What it does

- **Host half** — a Typert Remote gateway (`slideReflex`) that drives the ppt-reflex python runner (streaming per-element build frames) and owns the file bridge (`_deck_auto.json`, `_frames_auto.jsonl`, `_feedback_auto.json`, `_selection_auto.json`, `_palette_auto.json`).
- **Browser half** — a `shell.overlay` panel: page-by-page canvas preview that follows the build in real time, click an element or drag-box-select an area, request recolors (auto-applied + rebuild), ask questions (forwarded to the agent), pick palette colors, switch zh/en.

## Workflow

```
user states need in chat → agent generates deck → builds via runner
  → panel previews page by page → user clicks/box-selects/recolors/asks
  → agent reads feedback files → fixes → rebuild → loop
```

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

## Known limitations

- Requires the ppt-reflex engine repo checked out at `cwd` with `_dsh_ppt_runner.py` present.
- Recolor requests apply to box/shape fill colors; semantic questions are forwarded to the agent, not auto-applied.
- Host defaults hard-code a Windows python path when no config row is given.

## License

MIT
