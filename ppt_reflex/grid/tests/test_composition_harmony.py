"""T2–T5: harmony floor + dual-channel diagnostics.

Tests composition.py's T2 (color_ratio + image_style_conflict), T3 (focal_point),
T4 (hue_harmony + chroma), and builder's signal-exempt aggregation + geometry_ok/
harmony_ok split.
"""
import os
import tempfile

import pytest

from ppt_reflex.grid.plan import LayoutPlan, PageElement
from ppt_reflex.grid.types import ContentType, ElementPayload
from ppt_reflex.grid.composition import global_composition_check


def _el(eid, font_size=14, text="x", fill=None, w=200, h=100, x=100, y=100,
        image_path="", ctype=ContentType.TEXT, style_name="Body"):
    return PageElement(
        elem_id=eid, region_id="main", content_type=ctype, x=x, y=y, w=w, h=h,
        payload=ElementPayload(text=text, font_size=font_size, fill_color=fill,
                               image_path=image_path, style_name=style_name),
    )


def _plan(*elems, page_w=960, page_h=540):
    return LayoutPlan(page_w=page_w, page_h=page_h, elements=list(elems))


def _by_rule(diags, rule):
    return [d for d in diags if d.get("rule") == rule]


# ═══════════════════════════════════════════════════════════════
# T2: color_ratio (60-30-10 in OKLCH)
# ═══════════════════════════════════════════════════════════════

def test_color_ratio_complementary_1to1_violation():
    # cyan vs orange ~ 1:1 → no clear dominant/secondary band → violation
    plan = _plan(
        _el("a", fill=(0, 229, 255), w=200, h=200),
        _el("b", fill=(255, 109, 0), w=200, h=200),
    )
    diags = global_composition_check(plan, {"bg_hex": "FFFFFF"})
    color = _by_rule(diags, "color_ratio")
    assert color, "expected a color_ratio violation"
    assert all(d["severity"] == "warning" for d in color)
    assert all(d["channel"] == "violation" for d in color)
    assert all(d.get("harmony") for d in color)


def test_color_ratio_60_30_10_passes():
    # neutral 60% / accent 30% / accent2 10% → in band
    plan = _plan(
        _el("neutral", fill=(244, 246, 249), w=300, h=200),   # surface (neutral)
        _el("accent", fill=(29, 78, 216), w=150, h=200),      # blue accent
        _el("accent2", fill=(192, 57, 43), w=50, h=200),      # red accent
    )
    diags = global_composition_check(plan, {"bg_hex": "FFFFFF"})
    assert not _by_rule(diags, "color_ratio")


# ═══════════════════════════════════════════════════════════════
# T2: image_style_conflict (signal)
# ═══════════════════════════════════════════════════════════════

def test_image_style_conflict_warm_vs_cyan():
    from PIL import Image
    tmp = os.path.join(tempfile.gettempdir(), "warm_test.png")
    Image.new("RGB", (120, 120), (255, 140, 66)).save(tmp)  # warm orange
    plan = _plan(_el("img", image_path=tmp, w=300, h=200, ctype=ContentType.IMAGE))
    diags = global_composition_check(plan, {"accent_hex": "22D3EE"})  # tech_dark cyan
    sig = _by_rule(diags, "image_style_conflict")
    assert sig, "expected image_style_conflict signal"
    assert sig[0]["severity"] == "advisory"
    assert sig[0]["channel"] == "signal"


# ═══════════════════════════════════════════════════════════════
# T3: focal_point
# ═══════════════════════════════════════════════════════════════

def test_focal_point_missing_single_text():
    plan = _plan(_el("t", font_size=16, text="body"))
    diags = global_composition_check(plan, {})
    missing = _by_rule(diags, "focal_point.missing")
    assert missing and missing[0]["severity"] == "advisory"
    assert missing[0]["channel"] == "signal"


def test_focal_point_ambiguous_tie():
    plan = _plan(
        _el("a", font_size=16, text="a"),
        _el("b", font_size=16, text="b"),
    )
    diags = global_composition_check(plan, {})
    amb = _by_rule(diags, "focal_point.ambiguous")
    assert amb and amb[0]["severity"] == "warning"


def test_focal_point_clear_title_body_passes():
    # 28pt title vs 14pt body → multiplier 2.0 ≥ 1.5 → has focal point (no missing)
    plan = _plan(
        _el("title", font_size=28, text="Title", style_name="Heading"),
        _el("body", font_size=14, text="body text", style_name="Body"),
    )
    diags = global_composition_check(plan, {})
    assert not _by_rule(diags, "focal_point.missing")
    assert not _by_rule(diags, "focal_point.ambiguous")
    assert not _by_rule(diags, "focal_point.split")


# ═══════════════════════════════════════════════════════════════
# T4: hue_harmony + chroma
# ═══════════════════════════════════════════════════════════════

def test_hue_harmony_clashing_violation():
    # red vs magenta → ~60° apart → clashing (not analogous/complementary/triadic)
    plan = _plan(
        _el("red", fill=(255, 0, 0), w=150, h=150),
        _el("magenta", fill=(255, 0, 255), w=150, h=150),
    )
    diags = global_composition_check(plan, {"bg_hex": "FFFFFF"})
    assert _by_rule(diags, "hue_harmony"), "expected hue_harmony violation"


def test_hue_harmony_complementary_passes():
    # cyan vs orange ~ complementary (163°) → harmonious, no violation
    plan = _plan(
        _el("cyan", fill=(0, 229, 255), w=150, h=150),
        _el("orange", fill=(255, 109, 0), w=150, h=150),
    )
    diags = global_composition_check(plan, {"bg_hex": "FFFFFF"})
    assert not _by_rule(diags, "hue_harmony")


def test_chroma_families_cap():
    # three high-chroma families (red/green/blue) → > 2 → violation
    plan = _plan(
        _el("r", fill=(255, 0, 0), w=100, h=100),
        _el("g", fill=(0, 255, 0), w=100, h=100),
        _el("b", fill=(0, 0, 255), w=100, h=100),
    )
    diags = global_composition_check(plan, {"bg_hex": "FFFFFF"})
    assert _by_rule(diags, "chroma_families"), "expected chroma_families violation"


# ═══════════════════════════════════════════════════════════════
# T5: signal-exempt aggregation + geometry_ok/harmony_ok
# ═══════════════════════════════════════════════════════════════

def test_aggregator_signal_never_trimmed():
    from ppt_reflex.builder import _aggregate_diagnostics
    diags = []
    for i in range(20):  # 20 info + 20 advisory → info cap is 5
        diags.append({"kind": "noise", "severity": "info", "message": f"i{i}"})
        diags.append({"kind": "focal_point", "rule": "focal_point.missing",
                      "severity": "advisory", "channel": "signal",
                      "elem_id": f"e{i}", "message": "no focus"})
    agg, stats = _aggregate_diagnostics(diags)
    advisories = [d for d in agg if d.get("channel") == "signal"]
    assert len(advisories) == 20, "signals must never be trimmed"
    assert stats["trimmed_info"] == 15
    assert stats["advisories"] == 20


def test_harmony_ok_helper():
    from ppt_reflex.builder import _harmony_ok
    assert _harmony_ok([]) is True
    assert _harmony_ok([{"harmony": True, "severity": "advisory"}]) is True
    assert _harmony_ok([{"harmony": True, "severity": "warning"}]) is False
    assert _harmony_ok([{"harmony": False, "severity": "warning"}]) is True


if __name__ == "__main__":
    test_color_ratio_complementary_1to1_violation()
    test_color_ratio_60_30_10_passes()
    test_image_style_conflict_warm_vs_cyan()
    test_focal_point_missing_single_text()
    test_focal_point_ambiguous_tie()
    test_focal_point_clear_title_body_passes()
    test_hue_harmony_clashing_violation()
    test_hue_harmony_complementary_passes()
    test_chroma_families_cap()
    test_aggregator_signal_never_trimmed()
    test_harmony_ok_helper()
    print("\n✓ All harmony tests PASSED")
