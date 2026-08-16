"""tools/make_golden.py - T6 golden-set regression runner (harmony v1).

Runs every deck in tests/golden/golden_*.json through the REAL engine
(PPTBuilder -> build() into a temp dir, never D:\\ppt\\output), judges each
deck against its declared expectation, computes:

    pass_rate   = beautiful decks with ok && harmony_ok  / total beautiful
    block_rate  = ugly decks whose expected rule fired    / total ugly

then diffs the rates (and per-case outcomes) against tests/golden/baseline.json.
Any metric drop below baseline - or any case that passed at baseline but fails
now - is a regression: exit code 1. First run uses --init to record baseline.

Usage:
    python tools/make_golden.py            # compare against baseline (CI)
    python tools/make_golden.py --init     # (re)generate baseline.json
    python tools/make_golden.py --json     # machine-readable report on stdout
"""

from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import shutil
import sys
import tempfile

# path discipline: force THIS repo's ppt_reflex (a stale editable install of
# the package may shadow it from site-packages)
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from ppt_reflex.builder import PPTBuilder                      # noqa: E402
from ppt_reflex.grid.composition import rules_version         # noqa: E402

_GOLDEN_DIR = os.path.join(_REPO, "tests", "golden")
_ASSETS_DIR = os.path.join(_GOLDEN_DIR, "assets")
_BASELINE_PATH = os.path.join(_GOLDEN_DIR, "baseline.json")

# rule names (or prefixes) the ugly-set judge matches against diagnostics.
# image_style_conflict is a T5 *signal* (advisory) - it never blocks harmony_ok,
# but it MUST still reach the agent; the judge accepts advisory-level matches for it.
_HARMONY_SEVERITIES = ("error", "warning", "advisory")


# ---------------------------------------------------------------
# Deck replay (declarative JSON -> PPTBuilder calls)
# ---------------------------------------------------------------

def _color(v):
    """[r,g,b] list -> tuple, else None."""
    if isinstance(v, (list, tuple)) and len(v) == 3:
        try:
            return tuple(int(x) for x in v)
        except (TypeError, ValueError):
            return None
    return None


def _build_element(b: PPTBuilder, e: dict):
    t = e.get("type", "text")
    region = e.get("region", "main")
    text = e.get("text", "") or ""
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
                     recipe=e.get("recipe"), role=e.get("role", ""),
                     align_h=e.get("align_h", "left"))
    if t == "shape":
        return b.shape(e.get("shape_id", "rectangle"), region=region,
                       fill_color=_color(e.get("fill_color")),
                       pw=e.get("pw"), ph=e.get("ph"), text=text,
                       font_size=e.get("font_size"), role=e.get("role", ""))
    if t == "image":
        return b.image(e.get("path", ""), region=region,
                       layout_mode=e.get("layout_mode", ""),
                       caption=e.get("caption", ""), fit_mode=e.get("fit_mode", "fit"))
    if t == "table":
        return b.table(e.get("headers", []), e.get("rows", []), region=region,
                       font_size=e.get("font_size", 12.0))
    if t == "divider":
        return b.divider(region=region, color=_color(e.get("color")))
    raise ValueError("unknown element type: " + repr(t))


def _replay_deck(b: PPTBuilder, deck: dict) -> None:
    """Declare every slide of a golden deck onto the builder (no build yet)."""
    for s in deck.get("slides", []):
        elements = [_build_element(b, e) for e in s.get("elements", [])]
        b.add_slide(
            s.get("title", ""),
            archetype=s.get("archetype"),
            params=s.get("params"),
            regions=s.get("regions"),
            elements=elements,
            frame=s.get("frame", ""),
            rail=s.get("rail", ""),
            corner_mark=s.get("corner_mark", ""),
        )


# ---------------------------------------------------------------
# Synthetic image assets (deterministic solid-color PNGs)
# ---------------------------------------------------------------

def ensure_assets(deck: dict) -> None:
    """Materialize deck['assets'] = {name: {"rgb":[r,g,b],"size":[w,h]}} as PNGs
    under tests/golden/assets so the harmony ledger's dominant-color detector has
    real files to read. Deterministic: same spec -> same bytes."""
    assets = deck.get("assets") or {}
    for name, spec in assets.items():
        rgb = _color(spec.get("rgb"))
        if rgb is None:
            continue
        w, h = spec.get("size", [240, 160])
        path = os.path.join(_ASSETS_DIR, name + ".png")
        if os.path.exists(path):
            continue
        os.makedirs(_ASSETS_DIR, exist_ok=True)
        from PIL import Image
        Image.new("RGB", (int(w), int(h)), rgb).save(path)


def _resolve_path(rel: str) -> str:
    """Deck-relative asset path -> absolute path under the golden dir."""
    if not rel:
        return rel
    if os.path.isabs(rel):
        return rel
    return os.path.join(_GOLDEN_DIR, rel)


# ---------------------------------------------------------------
# Case loading
# ---------------------------------------------------------------

def load_cases() -> list:
    cases = []
    for path in sorted(glob.glob(os.path.join(_GOLDEN_DIR, "golden_*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            case = json.load(f)
        case["_file"] = os.path.basename(path)
        kind = case.get("kind", "beautiful")
        if kind not in ("beautiful", "ugly"):
            raise ValueError(case.get("id", path) + ": kind must be beautiful|ugly")
        for s in case.get("slides", []):
            for e in s.get("elements", []):
                if e.get("type") == "image" and e.get("path"):
                    e["path"] = _resolve_path(e["path"])
        cases.append(case)
    if not cases:
        raise SystemExit("no golden_*.json decks found under " + _GOLDEN_DIR)
    return cases


# ---------------------------------------------------------------
# Judging
# ---------------------------------------------------------------

def _fired_rules(diags: list) -> list:
    """Harmony diagnostics that actually fired, with severity. A diagnostic is
    harmony-governed if it carries harmony=true (T2-T4) - signalled or blocking."""
    out = []
    for d in diags:
        if not d.get("harmony"):
            continue
        sev = d.get("severity", "")
        if sev not in _HARMONY_SEVERITIES:
            continue
        rule = d.get("rule") or d.get("category") or d.get("kind") or ""
        if rule:
            out.append({"rule": rule, "severity": sev, "message": d.get("message", "")})
    return out


def _matches(expect: str, fired: list) -> dict:
    for f in fired:
        if f["rule"].startswith(expect):
            return f
    return None


def evaluate(case: dict, build_dir: str) -> dict:
    """Build one deck through the real engine and judge it."""
    try:
        b = PPTBuilder(template=case.get("template", "academic"),
                       style=case.get("style"),
                       strict_tokens=bool(case.get("strict_tokens", True)))
        _replay_deck(b, case)
        r = b.build(os.path.join(build_dir, case["id"] + ".pptx"))

        diags = r.get("diagnostics", [])
        fired = _fired_rules(diags)
        kind = case.get("kind", "beautiful")

        if kind == "beautiful":
            passed = bool(r.get("ok")) and bool(r.get("harmony_ok"))
            return {"id": case["id"], "kind": kind, "passed": passed,
                    "blocked": not r.get("harmony_ok", True),
                    "expect": None, "fired": fired,
                    "ok": r.get("ok"), "harmony_ok": r.get("harmony_ok"),
                    "n_errors": sum(1 for d in diags if d.get("severity") == "error"),
                    "file": case["_file"]}

        # ugly: every expected rule must have fired (severity accepted per rule kind)
        expect = list(case.get("expected", {}).get("blocks", []))
        matched = {e: bool(_matches(e, fired)) for e in expect}
        passed = bool(expect) and all(matched.values())
        return {"id": case["id"], "kind": kind, "passed": passed,
                "blocked": not r.get("harmony_ok", True),
                "expect": expect, "fired": fired,
                "matched": matched,
                "ok": r.get("ok"), "harmony_ok": r.get("harmony_ok"),
                "n_errors": sum(1 for d in diags if d.get("severity") == "error"),
                "file": case["_file"]}
    except Exception as ex:  # a deck that crashes is a failure, not a crash
        return {"id": case.get("id", "?"), "kind": case.get("kind", "?"),
                "passed": False, "blocked": False, "expect": None,
                "fired": [], "error": type(ex).__name__ + ": " + str(ex),
                "file": case.get("_file", "")}


def run_golden() -> dict:
    cases = load_cases()
    build_dir = tempfile.mkdtemp(prefix="ppt_reflex_golden_")
    try:
        for c in cases:
            ensure_assets(c)
        results = [evaluate(c, build_dir) for c in cases]
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)

    pos = [r for r in results if r["kind"] == "beautiful"]
    neg = [r for r in results if r["kind"] == "ugly"]
    pass_rate = (sum(1 for r in pos if r["passed"]) / len(pos)) if pos else 1.0
    block_rate = (sum(1 for r in neg if r["passed"]) / len(neg)) if neg else 1.0
    return {"results": results, "pass_rate": pass_rate, "block_rate": block_rate,
            "n_beautiful": len(pos), "n_ugly": len(neg),
            "rules_version": rules_version()}


# ---------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------

def _load_baseline() -> dict:
    if not os.path.exists(_BASELINE_PATH):
        return None
    try:
        with open(_BASELINE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _write_baseline(run: dict) -> None:
    baseline = {
        "schema": 1,
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "rules_version": run["rules_version"],
        "_note": "golden-set floor. Regenerate with 'python tools/make_golden.py --init' "
                 "after an INTENTIONAL rules.json threshold change. Any pass_rate / "
                 "block_rate drop below these values (or a per-case pass->fail flip) "
                 "fails CI.",
        "pass_rate": round(run["pass_rate"], 4),
        "block_rate": round(run["block_rate"], 4),
        "n_beautiful": run["n_beautiful"],
        "n_ugly": run["n_ugly"],
        "cases": {
            r["id"]: {
                "kind": r["kind"], "passed": r["passed"], "blocked": r["blocked"],
                "expect": r.get("expect"),
                "fired": [f["rule"] for f in r.get("fired", [])],
                "error": r.get("error"),
            }
            for r in run["results"]
        },
    }
    with open(_BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)


def compare_baseline(run: dict) -> dict:
    base = _load_baseline()
    if base is None:
        return {"report": None, "regression": False, "baseline_missing": True}

    base_pass = base.get("pass_rate", 1.0)
    base_block = base.get("block_rate", 1.0)
    base_cases = base.get("cases", {})

    flips = [r["id"] for r in run["results"]
             if base_cases.get(r["id"], {}).get("passed") and not r["passed"]]

    regression = (run["pass_rate"] < base_pass or run["block_rate"] < base_block
                  or bool(flips))
    return {
        "report": {
            "rules_version": run["rules_version"],
            "baseline_rules_version": base.get("rules_version"),
            "pass_rate": round(run["pass_rate"], 4),
            "baseline_pass_rate": round(base_pass, 4),
            "pass_delta": round(run["pass_rate"] - base_pass, 4),
            "block_rate": round(run["block_rate"], 4),
            "baseline_block_rate": round(base_block, 4),
            "block_delta": round(run["block_rate"] - base_block, 4),
            "n_beautiful": run["n_beautiful"],
            "n_ugly": run["n_ugly"],
            "regression": regression,
            "pass_to_fail_flips": flips,
        },
        "regression": regression,
    }


# ---------------------------------------------------------------
# CLI
# ---------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="T6 harmony golden-set regression runner")
    ap.add_argument("--init", action="store_true",
                    help="record baseline.json from the current run (first run / after "
                         "an intentional rules.json change)")
    ap.add_argument("--json", action="store_true",
                    help="emit the full machine-readable report as JSON")
    args = ap.parse_args()

    run = run_golden()
    results = run["results"]
    failed = [r for r in results if not r["passed"]]

    if args.init:
        _write_baseline(run)
        print("[baseline] wrote " + _BASELINE_PATH +
              " (pass_rate=" + format(run["pass_rate"], ".2%") +
              ", block_rate=" + format(run["block_rate"], ".2%") + ")")

    cmp = compare_baseline(run)
    rep = cmp.get("report")

    if args.json:
        print(json.dumps({"run": {k: v for k, v in run.items() if k != "results"},
                          "baseline": rep, "cases": results}, ensure_ascii=False, indent=2))

    print()
    print("rules.json version: " + run["rules_version"])
    print("beautiful: %d decks, pass_rate=%.2f%%" % (run["n_beautiful"], run["pass_rate"] * 100)
          + (("  (baseline %.2f%%, delta %+.2f%%)" % (rep["baseline_pass_rate"] * 100, rep["pass_delta"] * 100)) if rep else ""))
    print("ugly:      %d decks, block_rate=%.2f%%" % (run["n_ugly"], run["block_rate"] * 100)
          + (("  (baseline %.2f%%, delta %+.2f%%)" % (rep["baseline_block_rate"] * 100, rep["block_delta"] * 100)) if rep else ""))

    print()
    print("per-case:")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        if r["kind"] == "beautiful":
            detail = ("ok=%s harmony_ok=%s fired=%s" % (r.get("ok"), r.get("harmony_ok"),
                      [f["rule"] for f in r.get("fired", [])]))
        else:
            matched = r.get("matched", {})
            mstr = ",".join("%s:%s" % (k, "Y" if v else "N") for k, v in matched.items())
            detail = ("expect=" + ",".join(r.get("expect") or []) + " matched=" + mstr +
                      " fired=" + str([f["rule"] for f in r.get("fired", [])]))
        err = "  ERROR: " + r["error"] if r.get("error") else ""
        print("  [%s] %-38s %s%s" % (status, r["id"], detail, err))

    if rep and rep.get("pass_to_fail_flips"):
        print()
        print("REGRESSION (pass->fail flips): " + str(rep["pass_to_fail_flips"]))
    if failed:
        print()
        print("%d case(s) failed." % len(failed))
    if cmp.get("baseline_missing") and not args.init:
        print()
        print("no baseline.json - run 'python tools/make_golden.py --init' first.")
        return 1
    if cmp.get("regression"):
        print()
        print("REGRESSION: pass/block rate dropped below baseline.")
        return 1
    if failed:
        return 1
    print()
    print("OK: golden-set green, no regression.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
