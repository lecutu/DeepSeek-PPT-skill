"""
grid/composition.py — Phase 2.5: global composition check (spatial + typography)

Input: LayoutPlan (Phase 1+2 completed)
Output: list[dict] — whitespace/balance/density/alignment/font/color issues
"""

from __future__ import annotations
from .plan import LayoutPlan


def global_composition_check(plan: LayoutPlan) -> list[dict]:
    """Global composition check — whitespace ratio, visual center of mass, density, alignment,
    font hierarchy, color ratio.

    Returns:
        list of dicts with keys: level ("info"|"warn"), category, message
    """
    issues: list[dict] = []

    _check_whitespace(plan, issues)
    _check_balance(plan, issues)
    _check_density(plan, issues)
    _check_alignment(plan, issues)
    _check_font_hierarchy(plan, issues)
    _check_font_size_variety(plan, issues)
    _check_color_ratio(plan, issues)
    _check_visual_chunks(plan, issues)
    _check_edge_safe_zone(plan, issues)

    return issues


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


def _check_color_ratio(plan: LayoutPlan, issues: list[dict]) -> None:
    """60-30-10 color rule: dominant ~60%, secondary ~30%, accent ~10%.
    Detects evenly-distributed color usage (classic AI cliché)."""
    elements = plan.elements
    if len(elements) < 3:
        return

    from collections import Counter
    color_usage: dict[str, float] = {}
    for e in elements:
        p = e.payload
        if not p:
            continue
        fc = getattr(p, 'fill_color', None)
        if fc is None:
            key = "transparent"
        elif isinstance(fc, tuple):
            key = f"#{fc[0]:02X}{fc[1]:02X}{fc[2]:02X}"
        else:
            key = str(fc)
        color_usage[key] = color_usage.get(key, 0) + e.w * e.h

    total = sum(color_usage.values())
    if total <= 0:
        return

    shares = sorted(color_usage.values(), reverse=True)
    n_colors = len(shares)

    # Evenly distributed colors → AI cliché
    if n_colors >= 4:
        avg_share = 1.0 / n_colors
        is_even = all(abs(s / total - avg_share) < 0.10 for s in shares[:n_colors])
        if is_even:
            issues.append({
                "level": "warn", "category": "color_ratio",
                "message": (
                    f"{n_colors} colors evenly distributed across the page. "
                    f"Aim for 60-30-10: one dominant color (~60%), one secondary (~30%), "
                    f"one accent (~10%). Even distribution reads as 'AI-generated template'."
                ),
                "n_colors": n_colors,
            })

    # No clear dominant (>50%)
    if n_colors >= 2 and shares and shares[0] / total < 0.50:
        issues.append({
            "level": "info", "category": "color_ratio",
            "message": (
                f"No dominant color (largest is {shares[0]/total:.0%}). "
                f"Pick a dominant color occupying ≥50% of visual area."
            ),
        })
