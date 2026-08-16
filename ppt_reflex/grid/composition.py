"""
grid/composition.py — Phase 2.5: global composition check (spatial + typography + harmony)

Input: LayoutPlan (Phase 1+2 completed) + optional context dict
Output: list[dict] — canonical diagnostics with severity + channel.

Two diagnostic channels (T5):
  - violation: severity "error" | "warning"  → blocks geometry_ok (error) / harmony_ok (warning)
  - signal:    severity "advisory"           → never blocks, never trimmed by the aggregator

Harmony floor (T2–T4) = color_ratio / image_style_conflict / focal_point / hue_harmony /
chroma_families. These carry `"harmony": true` so the builder can compute harmony_ok =
zero error/warning among them. `focal_point.missing` and `image_style_conflict` are
signals (advisory), so they inform but never block harmony_ok.

Scope guard — deliberately NOT implemented (kept here so they don't creep back in):
  - no anchor interpolation / style auto-sampling generator (style space is non-convex)
  - no visual-weight saliency model (that would smuggle in a vision model and break
    the "deterministic, verifiable floor" promise)
  - no HTML→PPTX conversion (live.py is retired; the direction is correct, don't revisit)
  - no saturation-lightness "same plane" constraint (false-positive rate > benefit)
  - no renaming of internal enums / primitives / style names (T7 is an alias layer only)
"""

from __future__ import annotations

import json
import os

from .plan import LayoutPlan
from .types import ContentType
from .oklch import srgb_to_oklch, hue_distance, chroma, lightness
from .color_utils import hex_to_rgb, contrast_ratio, rgb_to_hex

# ── Rules governance (T6): thresholds live in rules.json, never in code ──
_RULES_PATH = os.path.join(os.path.dirname(__file__), "rules.json")

_DEFAULT_RULES = {
    "color_ratio": {
        "dominant_band": [0.50, 0.70],
        "secondary_band": [0.20, 0.35],
        "accent_band": [0.05, 0.15],
    },
    "focal_point": {"contrast_multiplier": 1.5, "edge_margin_pct": 0.04},
    "image_style": {"analogous_max_deg": 30, "neutral_chroma_threshold": 0.05},
    "hue_harmony": {
        "analogous_max_deg": 30,
        "complementary_band": [150, 210],
        "triadic_center": 120,
        "triadic_tolerance": 15,
        "neutral_chroma_threshold": 0.05,
    },
    "chroma": {"high_chroma_threshold": 0.15, "max_high_chroma_families": 2},
}


def _rules() -> dict:
    """Load rules.json; fall back to defaults if missing. Re-read on every call so a
    human edit (and a version bump) takes effect immediately."""
    try:
        with open(_RULES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(_DEFAULT_RULES)
        for k, v in data.items():
            if k.startswith("_"):
                continue
            if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k].update(v)
            else:
                merged[k] = v
        return merged
    except (OSError, json.JSONDecodeError):
        return dict(_DEFAULT_RULES)


def rules_version() -> str:
    try:
        with open(_RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("version", "unknown")
    except (OSError, json.JSONDecodeError):
        return "unknown"


# ═══════════════════════════════════════════════════════════════
# Canonical issue helpers
# ═══════════════════════════════════════════════════════════════

def _violation(category, message, *, rule=None, severity="warning", actual=None,
               expected_band=None, fix_hint=None, elem_id=None, metrics=None, harmony=True):
    return {
        "category": category, "rule": rule or category, "severity": severity,
        "channel": "violation", "message": message, "harmony": harmony,
        "actual": actual, "expected_band": expected_band, "fix_hint": fix_hint,
        "elem_id": elem_id, "metrics": metrics,
    }


def _signal(category, message, *, rule=None, elem_id=None, metrics=None, harmony=True):
    return {
        "category": category, "rule": rule or category, "severity": "advisory",
        "channel": "signal", "message": message, "harmony": harmony,
        "elem_id": elem_id, "metrics": metrics,
    }


def _normalize(issue: dict) -> dict:
    """Convert legacy {"level": ...} issues into the canonical severity/channel shape."""
    if "severity" in issue:
        return issue
    sev = {"error": "error", "warn": "warning", "warning": "warning",
           "info": "info"}.get(issue.get("level", "info"), "info")
    out = dict(issue)
    out.pop("level", None)
    out["severity"] = sev
    out["channel"] = "info" if sev == "info" else "violation"
    out.setdefault("harmony", False)
    out.setdefault("rule", out.get("category", ""))
    return out


def global_composition_check(plan: LayoutPlan, context: dict | None = None) -> list[dict]:
    """Global composition check — whitespace, balance, density, alignment, font
    hierarchy, color ratio (T2), focal point (T3), hue harmony + chroma (T4).

    context (optional): {"bg_hex", "accent_hex", "accent2_hex", ...} — the resolved
    template/style palette. Without it the harmony checks that need a palette degrade
    to no-ops (they are still run, they just have nothing to compare against).
    """
    ctx = context or {}
    issues: list[dict] = []

    _check_whitespace(plan, issues)
    _check_balance(plan, issues)
    _check_density(plan, issues)
    _check_alignment(plan, issues)
    _check_font_hierarchy(plan, issues)
    _check_font_size_variety(plan, issues)
    _check_color_ratio(plan, issues, ctx)
    _check_visual_chunks(plan, issues)
    _check_edge_safe_zone(plan, issues)
    # T2–T4 harmony floor (new categories — same phase-2.5 hook, no parallel system)
    _check_image_style_conflict(plan, issues, ctx)
    _check_focal_point(plan, issues, ctx)
    _check_hue_harmony(plan, issues, ctx)
    _check_chroma_families(plan, issues, ctx)

    return [_normalize(i) for i in issues]


# ═══════════════════════════════════════════════════════════════
# Check functions
# ═══════════════════════════════════════════════════════════════

def _check_whitespace(plan: LayoutPlan, issues: list[dict]) -> None:
    total_area = plan.page_w * plan.page_h
    if total_area <= 0:
        return

    elem_area = sum(e.w * e.h for e in plan.elements)
    deco_area = sum(
        abs(d.x2 - d.x1) * abs(d.y2 - d.y1) * 0.1
        for d in plan.decorations
        if d.deco_type == "arrow" and d.x2 != 0
    )
    occupied = elem_area + deco_area
    ratio = occupied / total_area

    if ratio < 0.08:
        issues.append({
            "level": "warn", "category": "whitespace",
            "message": f"Content occupies only {ratio:.0%} of page — too sparse.",
        })
    elif ratio > 0.80:
        issues.append({
            "level": "warn", "category": "whitespace",
            "message": f"Content occupies {ratio:.0%} of page — too dense, reduce element count or size.",
        })
    elif ratio > 0.65:
        issues.append({
            "level": "warn", "category": "whitespace",
            "message": f"Content occupies {ratio:.0%} of page — whitespace below 35%. "
                       f"Design guides recommend ≥40% whitespace (content ≤60%).",
        })
    elif ratio > 0.60:
        issues.append({
            "level": "info", "category": "whitespace",
            "message": f"Content occupies {ratio:.0%} of page — whitespace at {1-ratio:.0%}, "
                       f"approaching the ≥40% whitespace target.",
        })


def _check_balance(plan: LayoutPlan, issues: list[dict]) -> None:
    elements = plan.elements
    if not elements:
        return

    total_area = sum(e.w * e.h for e in elements)
    if total_area <= 0:
        return

    cx = sum((e.x + e.w / 2) * e.w * e.h for e in elements) / total_area
    cy = sum((e.y + e.h / 2) * e.w * e.h for e in elements) / total_area

    page_cx = plan.page_w / 2
    page_cy = plan.page_h / 2
    third_w = plan.page_w / 3
    third_h = plan.page_h / 3

    dx = abs(cx - page_cx)
    dy = abs(cy - page_cy)

    if dx > third_w or dy > third_h:
        direction = ""
        if dx > third_w:
            direction += "right-heavy" if cx > page_cx else "left-heavy"
        if dy > third_h:
            direction += "bottom-heavy" if cy > page_cy else "top-heavy"
        issues.append({
            "level": "info", "category": "balance",
            "message": f"Visual center ({cx:.0f},{cy:.0f}) deviates from page center ({page_cx:.0f},{page_cy:.0f}) — {direction}.",
        })


def _check_density(plan: LayoutPlan, issues: list[dict]) -> None:
    for region in plan.regions:
        region_area = region.w * region.h
        if region_area <= 0:
            continue
        elem_area = sum(
            e.w * e.h for e in plan.elements
            if e.elem_id in region.elements
        )
        ratio = elem_area / region_area
        if ratio > 0.90:
            issues.append({
                "level": "warn", "category": "density",
                "message": f"Region '{region.region_id}' ({region.purpose}) at {ratio:.0%} fill — "
                           f"no room for decoration or breathing space.",
            })


def _check_alignment(plan: LayoutPlan, issues: list[dict]) -> None:
    for region in plan.regions:
        region_elems = [e for e in plan.elements if e.elem_id in region.elements]
        if len(region_elems) < 2:
            continue
        left_edges = sorted(e.x for e in region_elems)
        spread = left_edges[-1] - left_edges[0]
        if spread > 10:
            issues.append({
                "level": "info", "category": "alignment",
                "message": f"Region '{region.region_id}': left edges span {spread:.0f}pt "
                           f"(from {left_edges[0]:.0f} to {left_edges[-1]:.0f}) — "
                           f"consider uniform left alignment.",
            })


def _check_font_hierarchy(plan: LayoutPlan, issues: list[dict]) -> None:
    titles = []
    bodies = []
    for e in plan.elements:
        p = e.payload
        if not p or not p.text.strip():
            continue
        # 用语义样式名判断（builder._s 注入 payload.style_name），
        # 不再读恒为 None 的 p.role（2026-08 审查：旧版因此永不触发）
        style = (getattr(p, "style_name", "") or "").lower()
        if style in ("heading", "subtitle", "subheading"):
            titles.append((e.elem_id, p.font_size))
        else:
            bodies.append((e.elem_id, p.font_size))

    if not titles or not bodies:
        return

    min_title_sz = min(sz for _, sz in titles)
    violators = [(eid, sz) for eid, sz in bodies if sz >= min_title_sz]

    if violators:
        examples = ", ".join(f"{eid}({sz:.0f}pt)" for eid, sz in violators[:3])
        issues.append({
            "level": "warn",
            "category": "font_hierarchy",
            "message": (
                f"Font hierarchy broken: {len(violators)} body elements have font_size "
                f">= smallest title ({min_title_sz:.0f}pt). "
                f"Offenders: {examples}"
                f"{'...' if len(violators) > 3 else ''}. "
                f"Shrink body text or enlarge titles to restore hierarchy."
            ),
            "violator_count": len(violators),
            "min_title_pt": min_title_sz,
        })


def _check_font_size_variety(plan: LayoutPlan, issues: list[dict]) -> None:
    """Max 4 distinct font sizes per slide (power-design #7, Refactoring UI)."""
    sizes: set[float] = set()
    for e in plan.elements:
        p = e.payload
        if p and p.text.strip() and p.font_size:
            sizes.add(round(p.font_size, 1))
    if len(sizes) > 4:
        examples = sorted(sizes, reverse=True)
        issues.append({
            "level": "info", "category": "font_variety",
            "message": (
                f"{len(sizes)} distinct font sizes on this slide: {examples}. "
                f"Design guides cap at 4 (Refactoring UI / power-design). "
                f"Merge sizes into a 2-3 tier hierarchy."
            ),
            "font_sizes": sorted(examples, reverse=True),
        })


def _check_visual_chunks(plan: LayoutPlan, issues: list[dict]) -> None:
    """3-5 visual chunks ideal, max 7±2 (power-design #3, Miller 1956)."""
    n = len(plan.elements)
    if n > 8:
        issues.append({
            "level": "info", "category": "visual_chunks",
            "message": (
                f"{n} elements on this slide — above the 5-8 chunk ideal. "
                f"Too many visual blocks fragments attention; group or remove some."
            ),
            "element_count": n,
        })
    elif n > 5:
        issues.append({
            "level": "info", "category": "visual_chunks",
            "message": (
                f"{n} elements — toward the upper limit of the 3-5 chunk ideal. "
                f"Fine if they group into few visual units."
            ),
            "element_count": n,
        })


def _check_edge_safe_zone(plan: LayoutPlan, issues: list[dict]) -> None:
    """5% edge safe-zone on all sides (power-design #5)."""
    page_w = plan.page_w
    page_h = plan.page_h
    if page_w <= 0 or page_h <= 0:
        return
    safe_x = page_w * 0.05
    safe_y = page_h * 0.05

    violations = []
    for e in plan.elements:
        if e.x < safe_x or e.y < safe_y:
            side = []
            if e.x < safe_x:
                side.append("left")
            if e.y < safe_y:
                side.append("top")
            violations.append((e.elem_id, side))
            continue
        if e.x + e.w > page_w - safe_x:
            violations.append((e.elem_id, ["right"]))
        elif e.y + e.h > page_h - safe_y:
            violations.append((e.elem_id, ["bottom"]))

    if violations:
        examples = ", ".join(f"{eid}({','.join(sides)})" for eid, sides in violations[:4])
        issues.append({
            "level": "info", "category": "edge_safe_zone",
            "message": (
                f"{len(violations)} element(s) touch the 5% edge safe-zone: {examples}. "
                f"Keep content ≥5% from edges for projection/title-safe."
            ),
            "violation_count": len(violations),
        })


# ═══════════════════════════════════════════════════════════════
# T2: color ledger + 60-30-10 ratio + image accounting
# ═══════════════════════════════════════════════════════════════

def _dominant_color(path: str) -> tuple | None:
    """Deterministic dominant color of an image via a 4-bit-per-channel histogram.
    No visual model — pure pixel counting. Returns an sRGB tuple or None."""
    from PIL import Image
    try:
        img = Image.open(path).convert("RGB")
        img.thumbnail((64, 64))
    except Exception:
        return None

    step = 256 // 4  # 64 — 4 levels per channel → 64 bins
    hist: dict[tuple, int] = {}
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            key = (r // step, g // step, b // step)
            hist[key] = hist.get(key, 0) + 1
    if not hist:
        return None
    top = max(hist, key=hist.get)
    return (top[0] * step + step // 2, top[1] * step + step // 2, top[2] * step + step // 2)


def _family_key(lch: dict, neutral_threshold: float = 0.05) -> str:
    """Bucket an OKLCH color into a hue family. Near-neutral → 'neutral'; otherwise a
    30° hue bucket ('h0'..'h11')."""
    if chroma(lch) <= neutral_threshold:
        return "neutral"
    return f"h{int(round(lch['h'] / 30.0)) % 12}"


def _color_ledger(plan: LayoutPlan, ctx: dict) -> list[dict]:
    """Collect (rgb, lch, area, kind) entries for every filled element + image.
    Area = element geometric area (w*h) — the deterministic proxy for visual weight."""
    ledger = []
    for e in plan.elements:
        p = e.payload
        area = max(0.0, e.w * e.h)
        if area <= 0:
            continue
        if e.content_type == ContentType.IMAGE and p and getattr(p, "image_path", ""):
            path = getattr(p, "image_path", "")
            rgb = _dominant_color(path) if os.path.isfile(path) else None
            if rgb is not None:
                ledger.append({"elem_id": e.elem_id, "rgb": rgb,
                               "lch": srgb_to_oklch(rgb), "area": area, "kind": "image"})
        elif p and getattr(p, "fill_color", None) is not None:
            rgb = tuple(p.fill_color)
            ledger.append({"elem_id": e.elem_id, "rgb": rgb,
                           "lch": srgb_to_oklch(rgb), "area": area, "kind": "fill"})
    return ledger


def _check_color_ratio(plan: LayoutPlan, issues: list[dict], ctx: dict) -> None:
    """60-30-10 color rule in OKLCH hue families, weighted by filled area.

    The floor catches the classic AI cliché — evenly-distributed / no-dominant color
    usage — measured perceptually (OKLCH), not in RGB space. It deliberately does NOT
    flag "dominant > 70%" or "accent < 5%": a monochrome or 2-color scheme is a
    deliberate choice, not a cliché. So the enforced bounds are:

      dominant share  >= dominant_band[0]  (50%)  — else no focal color
      secondary share <= secondary_band[1] (35%)  — else too even
      accent share    <= accent_band[1]    (15%)  — else accent bloated (3+ families)
    """
    ledger = _color_ledger(plan, ctx)
    if len(ledger) < 2:
        return
    total = sum(x["area"] for x in ledger)
    if total <= 0:
        return

    neutral_threshold = _rules()["hue_harmony"]["neutral_chroma_threshold"]
    fam_areas: dict[str, float] = {}
    for x in ledger:
        key = _family_key(x["lch"], neutral_threshold)
        fam_areas[key] = fam_areas.get(key, 0.0) + x["area"]

    shares = sorted(fam_areas.values(), reverse=True)
    shares = [s / total for s in shares]
    n = len(shares)
    if n < 2:
        return  # single family = monochrome — no ratio to violate

    band = _rules()["color_ratio"]
    actual = {f"share_{i + 1}": round(shares[i], 3) for i in range(min(3, n))}

    def _emit(which, idx, lo, hi):
        issues.append(_violation(
            "color_ratio", rule="color_ratio",
            severity="warning",
            actual=dict(actual),
            expected_band={which: [lo, hi]},
            message=(f"{which} color family at {shares[idx]:.0%} — breaks the "
                     f"60-30-10 hierarchy (expected {which} in {lo:.0%}–{hi:.0%})."),
            fix_hint="Rework the fill/image area ratio so one family dominates "
                     "(≥50%), a second is secondary (≤35%), and the accent stays ≤15%.",
        ))

    # dominant floor: no clear dominant color → evenly-distributed cliché
    if shares[0] < band["dominant_band"][0]:
        _emit("dominant", 0, *band["dominant_band"])
    # secondary ceiling: second family too large → too even (e.g. 1:1)
    if n >= 2 and shares[1] > band["secondary_band"][1]:
        _emit("secondary", 1, *band["secondary_band"])
    # accent ceiling: third family too large → three-way even split
    if n >= 3 and shares[2] > band["accent_band"][1]:
        _emit("accent", 2, *band["accent_band"])


def _check_image_style_conflict(plan: LayoutPlan, issues: list[dict], ctx: dict) -> None:
    """T2: image dominant color vs style accent. A chromatic image whose dominant hue is
    NOT analogous (≤ analogous_max_deg) to the style accent reads as a foreign element
    in a tightly-controlled palette → signal image_style_conflict (advisory, not blocking)."""
    accent_hex = ctx.get("accent_hex")
    if not accent_hex:
        return
    accent_lch = srgb_to_oklch(hex_to_rgb(accent_hex))
    rules = _rules()["image_style"]
    if chroma(accent_lch) <= rules["neutral_chroma_threshold"]:
        return  # neutral accent — nothing chromatic to conflict with

    for e in plan.elements:
        p = e.payload
        if e.content_type != ContentType.IMAGE or not p or not getattr(p, "image_path", ""):
            continue
        path = getattr(p, "image_path", "")
        if not os.path.isfile(path):
            continue
        rgb = _dominant_color(path)
        if rgb is None:
            continue
        dom = srgb_to_oklch(rgb)
        if chroma(dom) <= rules["neutral_chroma_threshold"]:
            continue  # grayscale image fits any palette
        d = hue_distance(accent_lch["h"], dom["h"])
        if d > rules["analogous_max_deg"]:
            issues.append(_signal(
                "image_style_conflict", rule="image_style_conflict",
                elem_id=e.elem_id,
                metrics={"image_hue": round(dom["h"], 1),
                         "accent_hue": round(accent_lch["h"], 1),
                         "hue_distance": round(d, 1)},
                message=(f"Image '{e.elem_id}' dominant hue {dom['h']:.0f}° is "
                         f"{d:.0f}° from the style accent {accent_lch['h']:.0f}° "
                         f"(> {rules['analogous_max_deg']}° analogous limit) — "
                         f"the image may read as foreign to the palette."),
            ))


# ═══════════════════════════════════════════════════════════════
# T3: focal point uniqueness
# ═══════════════════════════════════════════════════════════════

def _check_focal_point(plan: LayoutPlan, issues: list[dict], ctx: dict) -> None:
    """Exactly one visual focal point per slide, operationalized as:

    1. the largest-font-size text element is UNIQUE (tie → focal_point.ambiguous);
    2. focal font size / mean(other text sizes) ≥ contrast_multiplier (default 1.5);
    3. focal element stays ≥ edge_margin_pct × page_w from every page edge.

    No element satisfying all three → focal_point.missing (signal, non-blocking).
    Two+ candidates → focal_point.split (violation).
    """
    text_elems = [e for e in plan.elements
                  if e.payload and (e.payload.text or "").strip() and (e.payload.font_size or 0) > 0]
    if not text_elems:
        issues.append(_signal("focal_point", rule="focal_point.missing",
                              message="Slide has no text element — no focal point."))
        return

    rules = _rules()["focal_point"]
    n_mult = rules["contrast_multiplier"]
    margin = plan.page_w * rules["edge_margin_pct"]

    def _margin_ok(e):
        return (e.x >= margin and e.y >= margin
                and e.x + e.w <= plan.page_w - margin
                and e.y + e.h <= plan.page_h - margin)

    max_fs = max(e.payload.font_size for e in text_elems)
    max_elems = [e for e in text_elems if abs(e.payload.font_size - max_fs) < 1e-9]

    # Condition 1: unique largest
    if len(max_elems) > 1:
        issues.append(_violation(
            "focal_point", rule="focal_point.ambiguous", severity="warning",
            elem_id=",".join(sorted(e.elem_id for e in max_elems[:4])),
            message=(f"{len(max_elems)} elements tie for the largest font size "
                     f"({max_fs:.0f}pt) — no unique focal point."),
            fix_hint="Make one element the unambiguous largest (enlarge it or shrink the others).",
        ))
        return

    focal = max_elems[0]
    others = [e for e in text_elems if e is not focal]
    mean_other = (sum(e.payload.font_size for e in others) / len(others)) if others else 0.0
    multiplier = (focal.payload.font_size / mean_other) if mean_other > 0 else 0.0

    # Candidates = elements satisfying contrast + margin (the "prominent, well-placed" set)
    candidates = []
    for e in text_elems:
        fs = e.payload.font_size
        if others and e is not focal:
            m = fs / mean_other
        else:
            m = multiplier
        if m >= n_mult and _margin_ok(e):
            candidates.append(e)

    if len(candidates) >= 2:
        issues.append(_violation(
            "focal_point", rule="focal_point.split", severity="warning",
            elem_id=",".join(sorted(c.elem_id for c in candidates[:4])),
            message=(f"{len(candidates)} elements qualify as the focal point — "
                     f"attention is split."),
            fix_hint="Demote secondary candidates so exactly one element dominates.",
        ))
        return

    # Exactly one candidate, or the unique max is the only candidate.
    if focal not in candidates:
        reasons = []
        if multiplier < n_mult:
            reasons.append(f"contrast multiplier {multiplier:.2f} < {n_mult}")
        if not _margin_ok(focal):
            reasons.append("too close to the page edge")
        issues.append(_signal("focal_point", rule="focal_point.missing",
                              elem_id=focal.elem_id,
                              metrics={"multiplier": round(multiplier, 2),
                                       "focal_pt": round(focal.payload.font_size, 1),
                                       "mean_other_pt": round(mean_other, 1)},
                              message=(f"No element satisfies all focal-point conditions "
                                       f"({' ; '.join(reasons) if reasons else 'none'}).")))


# ═══════════════════════════════════════════════════════════════
# T4: hue harmony + chroma ceiling
# ═══════════════════════════════════════════════════════════════

def _chromatic_families(plan: LayoutPlan, ctx: dict) -> dict[str, dict]:
    """Group chromatic fills/images into 30° hue families. Returns {family_key: {hue, max_chroma, area}}."""
    ledger = _color_ledger(plan, ctx)
    rules = _rules()["hue_harmony"]
    nt = rules["neutral_chroma_threshold"]
    fams: dict[str, dict] = {}
    for x in ledger:
        lch = x["lch"]
        if chroma(lch) <= nt:
            continue  # neutral — no hue
        key = _family_key(lch, nt)
        rec = fams.setdefault(key, {"hue": int(round(lch["h"] / 30.0)) % 12 * 30,
                                    "max_chroma": 0.0, "area": 0.0})
        rec["max_chroma"] = max(rec["max_chroma"], chroma(lch))
        rec["area"] += x["area"]
    return fams


def _hue_harmonious(d: float, rules: dict) -> bool:
    if d <= rules["analogous_max_deg"]:
        return True  # monochrome / analogous
    lo, hi = rules["complementary_band"]
    if lo <= d <= hi:
        return True  # complementary
    tri_lo = rules["triadic_center"] - rules["triadic_tolerance"]
    tri_hi = rules["triadic_center"] + rules["triadic_tolerance"]
    if tri_lo <= d <= tri_hi:
        return True  # triadic
    return False


def _check_hue_harmony(plan: LayoutPlan, issues: list[dict], ctx: dict) -> None:
    """T4: every pair of chromatic hue families must be monochrome/analogous(≤30°) /
    complementary(150–210°) / triadic(120±15°), all measured in OKLCH."""
    fams = _chromatic_families(plan, ctx)
    keys = sorted(fams)
    if len(keys) <= 1:
        return
    rules = _rules()["hue_harmony"]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            h1, h2 = fams[keys[i]]["hue"], fams[keys[j]]["hue"]
            d = hue_distance(h1, h2)
            if not _hue_harmonious(d, rules):
                issues.append(_violation(
                    "hue_harmony", rule="hue_harmony", severity="warning",
                    metrics={"hue_a": h1, "hue_b": h2, "distance": round(d, 1)},
                    message=(f"Hue families at {h1}° and {h2}° are {d:.0f}° apart — "
                             f"not monochrome/analogous/complementary/triadic."),
                    fix_hint="Restrict the slide to one hue family (or an analogous/"
                             "complementary/triadic pairing) so it reads as a single scheme.",
                ))


def _check_chroma_families(plan: LayoutPlan, issues: list[dict], ctx: dict) -> None:
    """T4: at most max_high_chroma_families (default 2) color families with C > 0.15."""
    fams = _chromatic_families(plan, ctx)
    rules = _rules()["chroma"]
    hi = rules["high_chroma_threshold"]
    cap = rules["max_high_chroma_families"]
    high = [k for k, rec in fams.items() if rec["max_chroma"] > hi]
    if len(high) > cap:
        issues.append(_violation(
            "chroma_families", rule="chroma_families", severity="warning",
            metrics={"high_chroma_families": sorted(high),
                     "max_chroma": [round(fams[k]["max_chroma"], 3) for k in high]},
            message=(f"{len(high)} high-chroma color families (C > {hi}) on one slide — "
                     f"cap is {cap}."),
            fix_hint="Keep high-saturation accents to ≤2 families; desaturate or merge the rest.",
        ))
