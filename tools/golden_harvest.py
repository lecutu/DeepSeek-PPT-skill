"""tools/golden_harvest.py - distill _feedback_auto.json history into golden cases (T6).

The human panel / reviewer writes deck verdicts to _feedback_auto.json over time:
  - a deck called "丑" / "rejected" / "ugly"   -> NEGATIVE sample (ugly golden case)
  - a deck that passed acceptance             -> POSITIVE sample (beautiful golden case)

This skeleton implements the file reading + entry classification + golden-case
entry structure. It does NOT replay the engine (that is make_golden.py's job) and
does not require historical data to exist - a missing file is a clean no-op.

Output: tests/golden/harvested.json - a list of golden cases in the SAME schema
as golden_*.json, so a human can review-then-promote by copying entries into
tests/golden/golden_harvested_*.json (make_golden.py picks them up automatically).

Feedback entry schema (one of):
  {"verdict": "ugly"|"rejected"|"accepted"|"approved"|..., "deck": {...}, "note": "...",
   "expect_block": "color_ratio"}          # expect_block only for negative samples
  {"feedback": "丑"|"难看"|"通过"|"验收通过"|..., "deck": {...}}
  a list of such entries, or {"entries": [...], "feedback": [...]}

deck schema (same as golden_*.json "slides"): {"template","style","slides":[{...}]}

Usage:
    python tools/golden_harvest.py                 # default paths
    python tools/golden_harvest.py <feedback.json> [out.json]
"""

from __future__ import annotations

import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_FEEDBACK = os.path.join(_REPO, "_feedback_auto.json")
_DEFAULT_OUT = os.path.join(_REPO, "tests", "golden", "harvested.json")

_POSITIVE = {"accepted", "approved", "good", "pass", "ok", "fine", "beautiful",
             "通过", "验收通过", "好", "好看", "美"}
_NEGATIVE = {"ugly", "rejected", "bad", "block", "fail", "broken", "reject",
             "丑", "难看", "差", "拒绝", "不合格"}


def classify_verdict(verdict) -> str | None:
    """Map a free-text verdict to 'beautiful' | 'ugly' | None (unknown)."""
    if verdict is None:
        return None
    v = str(verdict).strip().lower()
    if v in _POSITIVE:
        return "beautiful"
    if v in _NEGATIVE:
        return "ugly"
    return None


def load_feedback(path: str) -> list:
    """Read the feedback history file (tolerant of list / dict / empty)."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("entries", "feedback", "items"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def _to_golden_case(entry: dict, idx: int) -> dict | None:
    """Translate one feedback entry into a golden-case dict (or None to skip)."""
    deck = entry.get("deck")
    if not isinstance(deck, dict) or "slides" not in deck:
        return None
    verdict = classify_verdict(entry.get("verdict", entry.get("feedback")))
    if verdict is None:
        return None

    kind = verdict  # "beautiful" | "ugly"
    expected = ({"blocks": [entry["expect_block"]]}
                if kind == "ugly" and entry.get("expect_block")
                else ({"ok": True, "harmony_ok": True} if kind == "beautiful" else None))
    if expected is None:
        return None

    # NOTE skeleton: slides pass through as-is; a future extension may normalize
    # element specs (e.g. map "text" fields, strip raw colors from strict decks).
    case = {
        "id": "harvested_%03d_%s" % (idx, kind),
        "kind": kind,
        "template": deck.get("template", "academic"),
        "style": deck.get("style"),
        "strict_tokens": bool(deck.get("strict_tokens", True)),
        "note": "harvested from _feedback_auto.json: verdict=%r %s"
                % (entry.get("verdict", entry.get("feedback")),
                   ("(" + str(entry.get("note")) + ")") if entry.get("note") else ""),
        "expected": expected,
        "slides": deck["slides"],
    }
    return case


def harvest(feedback_path: str = _DEFAULT_FEEDBACK,
            out_path: str | None = None) -> dict:
    """Read feedback history, classify, and write candidate golden cases."""
    out_path = out_path or _DEFAULT_OUT
    entries = load_feedback(feedback_path)
    cases, skipped = [], 0
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            skipped += 1
            continue
        case = _to_golden_case(entry, i)
        if case is None:
            skipped += 1
            continue
        cases.append(case)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    return {
        "ok": True,
        "input": feedback_path,
        "output": out_path,
        "entries_seen": len(entries),
        "beautiful": sum(1 for c in cases if c["kind"] == "beautiful"),
        "ugly": sum(1 for c in cases if c["kind"] == "ugly"),
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
