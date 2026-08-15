"""
grid/ascii_map.py — layered ASCII feedback for layout review.

Three precision tiers, matched to what each element kind actually needs:
  L0 structure map — 40pt cells: regions, decoration skins, big fills.
  L1 element map  — 20pt cells: every element one letter, overlaps '#',
                    overflow '!', arrows as lines.
  L2 text table   — no ASCII (row-level precision cannot be drawn): per-text
                    font size / line count / line height / first-line y /
                    box height / overflow pt.

ASCII is always an INDEX; authoritative numbers live beside it (L2 + the
existing diagnostics JSON). 960×540 canvas default.
"""
from __future__ import annotations

_CELL_L0 = 40
_CELL_L1 = 20
_W, _H = 960, 540

_EL_LETTERS = {"text": "T", "textbox": "B", "shape": "S", "image": "I", "table": "A", "footer": "F"}


def _grid(w: float, h: float, cell: float) -> list[list[str]]:
    cols = max(1, int(w / cell) + 1)
    rows = max(1, int(h / cell) + 1)
    return [[" " for _ in range(cols)] for _ in range(rows)]


def _fill_rect(g, x, y, w, h, cell, ch) -> None:
    r0, c0 = max(0, int(y / cell)), max(0, int(x / cell))
    r1 = min(len(g), int((y + h) / cell) + 1)
    c1 = min(len(g[0]), int((x + w) / cell) + 1)
    for r in range(r0, r1):
        for c in range(c0, c1):
            if g[r][c] == " ":
                g[r][c] = ch
            elif g[r][c] != ch:
                g[r][c] = "#"


def _border(g, x, y, w, h, cell) -> None:
    r0, c0 = max(0, int(y / cell)), max(0, int(x / cell))
    r1 = min(len(g) - 1, int((y + h) / cell))
    c1 = min(len(g[0]) - 1, int((x + w) / cell))
    for c in range(c0, c1 + 1):
        for r in (r0, r1):
            if g[r][c] == " ":
                g[r][c] = "+"
    for r in range(r0, r1 + 1):
        for c in (c0, c1):
            if g[r][c] == " ":
                g[r][c] = "|"


def _render(g, title: str) -> str:
    lines = ["+{}+".format("-" * len(g[0]))]
    lines.append(f"|{title:<{len(g[0])}}|")
    lines.append("+{}+".format("-" * len(g[0])))
    for row in g:
        lines.append("|" + "".join(row) + "|")
    lines.append("+{}+".format("-" * len(g[0])))
    return "\n".join(lines)


def render_slide_ascii(plan, canvas=None, slide_index: int = 0) -> dict:
    """Render one solved slide's three-tier ASCII feedback.

    Returns {"L0": str, "L1": str, "L2": [dict, ...]} — L2 is the numeric
    text-precision table (no ASCII).
    """
    # L0: structure — regions + decoration skins + large fills
    g0 = _grid(_W, _H, _CELL_L0)
    region_marks = {}
    for i, reg in enumerate(plan.regions):
        letter = chr(ord("A") + (i % 26))
        region_marks[reg.region_id] = letter
        _border(g0, reg.x, reg.y, reg.w, reg.h, _CELL_L0)
    deco = []
    for d in plan.decorations:
        if getattr(d, "deco_type", "") == "arrow" and getattr(d, "x2", 0):
            _fill_rect(g0, min(d.x1, d.x2), min(d.y1, d.y2),
                       max(abs(d.x2 - d.x1), _CELL_L0), max(abs(d.y2 - d.y1), _CELL_L0),
                       _CELL_L0, "-")
            deco.append(d)

    # L1: elements — one letter each, '#' overlap, '!' overflow
    g1 = _grid(_W, _H, _CELL_L1)
    l2: list[dict] = []
    for pe in plan.elements:
        p = getattr(pe, "payload", None)
        kind = getattr(pe, "content_type", None)
        kind_s = kind.name.lower() if kind is not None else "text"
        ch = _EL_LETTERS.get(kind_s, "?")
        _fill_rect(g1, pe.x, pe.y, pe.w, pe.h, _CELL_L1, ch)
        if kind_s in ("text", "textbox") and p:
            text = (getattr(p, "text", "") or "").strip()
            if text:
                fs = getattr(p, "font_size", 0) or 0
                ls = getattr(p, "line_spacing", 1.2) or 1.2
                import math
                lines = text.split("\n")
                est_line_h = fs * ls
                need = sum(max(1, math.ceil(len(ln) * fs / max(1, pe.w - 12))) for ln in lines) * est_line_h
                overflow = round(need - pe.h, 1)
                if overflow > 0:
                    _fill_rect(g1, pe.x, pe.y + pe.h - _CELL_L1, pe.w, _CELL_L1, _CELL_L1, "!")
                l2.append({
                    "elem_id": pe.elem_id,
                    "text": text[:24],
                    "font_size": round(fs, 1),
                    "n_lines": len(lines),
                    "est_height_pt": round(need, 1),
                    "box_h_pt": round(pe.h, 1),
                    "y_pt": round(pe.y, 1),
                    "overflow_pt": overflow,
                })

    return {
        "L0": _render(g0, f"slide {slide_index} L0 structure (40pt/cell)"),
        "L1": _render(g1, f"slide {slide_index} L1 elements (20pt/cell, #=overlap !=overflow)"),
        "L2": l2,
    }
