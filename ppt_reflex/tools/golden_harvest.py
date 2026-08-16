"""tools/golden_harvest.py — distill `_feedback_auto.json` history into golden samples (T6).

The panel/agent writes feedback to `_feedback_auto.json` over time:
  - a deck the user called "丑" / "rejected"  → NEGATIVE sample (should be blocked)
  - a deck the user accepted / approved       → POSITIVE sample (should pass harmony)

This tool reads that history, classifies each entry by its verdict, and writes a
`harvested.json` list of golden cases in the same shape the golden runner can replay.
Harvested samples are review-then-promote: a human merges them into tests/golden/cases.py
(or leaves them in harvested.json, which the runner auto-loads).

Feedback schema (one entry):
  {
    "verdict": "ugly" | "rejected" | "accepted" | "approved",   # required
    "deck":    { "template": "...", "style": "...",              # required
                 "slides": [ {"title": "...", "archetype": "...",
                              "elements": [ {"id","type","text", ...} ] } ] },
    "note":    "optional free-text reason",
    "expect_block": "optional rule name for negative samples"
  }

Usage:
    python -m ppt_reflex.tools.golden_harvest [feedback_path] [out_path]
"""

from __future__ import annotations

import json
import os
import sys

# Default paths (feedback history → harvested golden cases)
_DEFAULT_FEEDBACK = r"D:\ppt\_feedback_auto.json"
_DEFAULT_OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "golden", "harvested.json",
)

_POSITIVE_VERDICTS = {"accepted", "approved", "good", "pass", "通过", "验收通过", "好"}
_NEGATIVE_VERDICTS = {"ugly", "rejected", "bad", "block", "fail", "丑", "难看", "差", "拒绝"}


def classify_verdict(verdict: str) -> str | None:
    """Map a free-text verdict to 'positive' | 'negative' | None (unknown)."""
    v = (verdict or "").strip().lower()
    if v in _POSITIVE_VERDICTS:
        return "positive"
    if v in _NEGATIVE_VERDICTS:
        return "negative"
    return None


def _color(c):
    if isinstance(c, list) and len(c) == 3:
        return tuple(int(v) for v in c)
    return None


def _element(b, e):
    t = e.get("type", "text")
    text = e.get("text", "") or ""
    region = e.get("region", "main")
    if t == "title":
        return b.title(text, region=region)
    if t == "subtitle":
        return b.subtitle(text, region=region)
    if t == "text":
        return b.text(text, style=e.get("style", "Body"), region=region)
    if t == "bullet":
        return b.bullet(text, region=region)
    if t == "footer":
        return b.footer(text)
    if t == "box":
        return b.box(text, style=e.get("style", "Body"), region=region,
                     fill_color=_color(e.get("fill_color")),
                     shape_id=e.get("shape_id", "rounded_rectangle"),
                     ph=e.get("ph"), align_h=e.get("align_h", "left"),
                     recipe=e.get("recipe"))
    if t == "shape":
        return b.shape(e.get("shape_id", "star"), region=region,
                       fill_color=_color(e.get("fill_color")),
                       pw=e.get("pw"), ph=e.get("ph"), text=text)
    if t == "image":
        return b.image(e.get("image_path", ""), region=region, pw=e.get("pw"),
                       ph=e.get("ph"), fit_mode=e.get("fit_mode", "fit"),
                       layout_mode=e.get("layout_mode", ""), caption=e.get("caption", ""))
    if t == "table":
        return b.table(e.get("headers", []), e.get("rows", []), region=region,
                       font_size=e.get("font_size", 12.0),
                       header_bg=_color(e.get("header_bg")))
    if t == "divider":
        return b.divider(region=region, color=_color(e.get("color")))
    raise ValueError(f"unknown element type: {t}")


def build_deck(b, deck: dict) -> None:
    """Replay a deck spec (runner request shape) onto a PPTBuilder. Shared by the
    golden runner so harvested cases are executable."""
    for s in deck.get("slides", []):
        by_id = {}
        elements = []
        for e in s.get("elements", []):
            spec = _element(b, e)
            elements.append(spec)
            if e.get("id"):
                by_id[e["id"]] = spec
        arrows = []
        for a in s.get("arrows", []):
            frm, to = a.get("from"), a.get("to")
            if frm in by_id and to in by_id:
                arrows.append(b.arrow(by_id[frm], by_id[to], text=a.get("text", "")))
        b.add_slide(s.get("title", ""), archetype=s.get("archetype"),
                    params=s.get("params"), regions=s.get("regions"),
                    elements=elements, arrows=arrows)


def harvest(feedback_path: str = _DEFAULT_FEEDBACK, out_path: str | None = None) -> dict:
    """Read feedback history, classify, and write harvested golden cases. Returns a
    summary dict. Missing input file → no-op (returns zero counts)."""
    out_path = out_path or _DEFAULT_OUT
    if not os.path.exists(feedback_path):
        return {"ok": True, "input": feedback_path, "positive": 0, "negative": 0,
                "skipped": 0, "note": "feedback file not found — nothing to harvest"}

    with open(feedback_path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    if isinstance(entries, dict):
        entries = entries.get("entries", entries.get("feedback", []))

    cases = []
    skipped = 0
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or "deck" not in entry:
            skipped += 1
            continue
        verdict = classify_verdict(entry.get("verdict", "") or entry.get("feedback", ""))
        if verdict is None:
            skipped += 1
            continue
        cases.append({
            "id": f"harvested_{i}_{verdict}",
            "positive": verdict == "positive",
            "expect_block": entry.get("expect_block"),
            "strict": entry.get("strict", not (verdict == "negative")),
            "tag": entry.get("tag") or ("region" if (entry.get("region") or entry.get("area")) else None),
            "deck": entry["deck"],
        })

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    return {
        "ok": True, "input": feedback_path, "output": out_path,
        "positive": sum(1 for c in cases if c["positive"]),
        "negative": sum(1 for c in cases if not c["positive"]),
        "skipped": skipped,
    }


def main() -> int:
    fb = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_FEEDBACK
    out = sys.argv[2] if len(sys.argv) > 2 else None
    summary = harvest(fb, out)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
