"""Golden-set runner (T6): execute GOLDEN_CASES, compute pass/block rates, and diff
them against tests/golden/baseline.json. `make golden` = `python -m ppt_reflex.tools.make_golden`.

Regression rule: pass_rate (beautiful decks passing) or block_rate (ugly decks blocked
by ≥1 harmony rule) may never drop below baseline.
"""

from __future__ import annotations

import json
import os

from ppt_reflex.tests.golden.cases import GOLDEN_CASES
from ppt_reflex.tools.golden_harvest import build_deck

_BASELINE_PATH = os.path.join(os.path.dirname(__file__), "baseline.json")
_HARVESTED_PATH = os.path.join(os.path.dirname(__file__), "harvested.json")


def _load_harvested() -> list[dict]:
    """Harvested golden cases (from _feedback_auto.json) auto-merged into the run."""
    if not os.path.exists(_HARVESTED_PATH):
        return []
    try:
        with open(_HARVESTED_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def _all_cases() -> list[dict]:
    cases = [dict(c) for c in GOLDEN_CASES]
    for h in _load_harvested():
        if not isinstance(h, dict) or "deck" not in h:
            continue
        cases.append({
            "id": h.get("id", "harvested"),
            "positive": bool(h.get("positive", True)),
            "expect_block": h.get("expect_block"),
            "strict": h.get("strict", False),
            "build": lambda b, deck=h["deck"]: build_deck(b, deck),
        })
    return cases


def _fired_harmony(diags: list[dict]) -> set[str]:
    """The harmony rule names (category/rule/kind) that actually blocked this slide."""
    out: set[str] = set()
    for d in diags:
        if d.get("harmony") and d.get("severity") in ("error", "warning"):
            for key in ("category", "rule", "kind"):
                v = d.get(key)
                if v:
                    out.add(v)
    return out


def run_golden() -> dict:
    from ppt_reflex.builder import PPTBuilder

    results = []
    for case in _all_cases():
        try:
            b = PPTBuilder(template=case.get("template", "academic"),
                           style=case.get("style"),
                           strict_tokens=case.get("strict", False))
            case["build"](b)
            r = b.build_single_slide(0)
            fired = _fired_harmony(r.get("diagnostics", []))
            blocked = not r.get("harmony_ok", True)
            if case["positive"]:
                passed = not blocked
            else:
                eb = case.get("expect_block")
                passed = blocked and (eb is None or any(f.startswith(eb) for f in fired))
            results.append({
                "id": case["id"], "positive": case["positive"], "passed": passed,
                "blocked": blocked, "expect_block": case.get("expect_block"),
                "fired": sorted(fired), "harmony_ok": r.get("harmony_ok"),
            })
        except Exception as ex:  # a case that crashes is a failure
            results.append({
                "id": case["id"], "positive": case["positive"], "passed": False,
                "blocked": False, "expect_block": case.get("expect_block"),
                "fired": [], "error": f"{type(ex).__name__}: {ex}",
            })

    pos = [r for r in results if r["positive"]]
    neg = [r for r in results if not r["positive"]]
    pass_rate = (sum(1 for r in pos if r["passed"]) / len(pos)) if pos else 1.0
    block_rate = (sum(1 for r in neg if r["passed"]) / len(neg)) if neg else 1.0
    return {"results": results, "pass_rate": pass_rate, "block_rate": block_rate,
            "n_positive": len(pos), "n_negative": len(neg)}


def _load_baseline() -> dict:
    if not os.path.exists(_BASELINE_PATH):
        return {"pass_rate": 1.0, "block_rate": 1.0}
    with open(_BASELINE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_baseline() -> dict:
    cur = run_golden()
    base = _load_baseline()
    pass_delta = cur["pass_rate"] - base.get("pass_rate", 1.0)
    block_delta = cur["block_rate"] - base.get("block_rate", 1.0)
    regression = (cur["pass_rate"] < base.get("pass_rate", 1.0)
                  or cur["block_rate"] < base.get("block_rate", 1.0))
    return {
        "pass_rate": round(cur["pass_rate"], 4),
        "baseline_pass_rate": round(base.get("pass_rate", 1.0), 4),
        "pass_delta": round(pass_delta, 4),
        "block_rate": round(cur["block_rate"], 4),
        "baseline_block_rate": round(base.get("block_rate", 1.0), 4),
        "block_delta": round(block_delta, 4),
        "regression": regression,
        "n_positive": cur["n_positive"],
        "n_negative": cur["n_negative"],
        "results": cur["results"],
    }
