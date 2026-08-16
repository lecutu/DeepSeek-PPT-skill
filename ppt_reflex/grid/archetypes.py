"""
grid/archetypes.py — Slide archetypes: named layout patterns with preset regions.

Each archetype defines:
  - regions: preset coordinates (no pixel math for AI)
  - zone_map: which element type → which region (auto-routing)
  - ai_guide: one-line routing description for agent prompts

Canvas: 960×540pt default. All coordinates relative to top-left.
"""

from __future__ import annotations
from dataclasses import dataclass, field, replace
from .agent_vocabulary import normalize_density

@dataclass
class SlideArchetype:
    """A named slide layout — regions + element routing rules."""
    id: str
    name: str
    description: str
    regions: list[tuple]          # [(name, x, y, w, h, z_order), ...]
    zone_map: dict[str, str] = field(default_factory=dict)
    ai_guide: str = ""
    # 分布组：ctype → 候选 region 列表，同类元素按声明顺序轮流分配
    # （兑现 ai_guide 的"first→A, second→B / 自动分布到 4 卡位"承诺）
    distribute: dict[str, list[str]] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# 12 Archetypes for 960×540 canvas
# ═══════════════════════════════════════════════════════════

ARCHETYPES: dict[str, SlideArchetype] = {
    # ── Narrative ──
    "title_cover": SlideArchetype(
        id="title_cover",
        name="Title Cover",
        description="Opening slide — bold title, tagline, visual anchor",
        regions=[
            ("header", 60, 60, 840, 100, 1),
            ("hero", 60, 180, 840, 200, 2),
            ("footer", 60, 420, 840, 80, 3),
        ],
        zone_map={"title": "header", "subtitle": "hero", "text": "hero",
                  "shape": "hero", "image": "hero", "footer": "footer", "box": "footer"},
        ai_guide="title→header, subtitle/text/shape/image→hero, footer/box→footer",
    ),
    "content": SlideArchetype(
        id="content",
        name="Content (Bullets)",
        description="Standard content — header + bullet list + sidebar card",
        regions=[
            ("header", 60, 30, 840, 72, 1),
            ("main", 60, 110, 520, 380, 2),
            ("sidebar", 600, 110, 300, 380, 3),
        ],
        zone_map={"title": "header", "subtitle": "header", "bullet": "main",
                  "text": "main", "table": "main", "box": "sidebar",
                  "image": "sidebar", "shape": "sidebar", "footer": "sidebar"},
        ai_guide="title→header, bullet/text/table→main, box/image/shape→sidebar",
    ),
    "two_column": SlideArchetype(
        id="two_column",
        name="Two Column",
        description="Side-by-side content — header + equal left/right columns",
        regions=[
            ("header", 60, 30, 840, 72, 1),
            ("left", 60, 110, 400, 390, 2),
            ("right", 500, 110, 400, 390, 3),
        ],
        zone_map={"title": "header", "subtitle": "header",
                  "bullet": "left", "text": "left", "box": "left",
                  "image": "right", "shape": "right", "table": "right",
                  "footer": "right"},
        ai_guide="title→header, bullet/text/box→left, image/shape/table→right",
    ),

    # ── Comparison / Decision ──
    "comparison": SlideArchetype(
        id="comparison",
        name="Comparison (A vs B)",
        description="Two items side-by-side — pros/cons, before/after, option A/B",
        regions=[
            ("header", 60, 30, 840, 72, 1),
            ("item_a", 60, 110, 360, 380, 2),
            ("vs_center", 440, 240, 80, 60, 4),
            ("item_b", 540, 110, 360, 380, 3),
        ],
        zone_map={"title": "header", "subtitle": "header",
                  "box": "item_a", "bullet": "item_a", "text": "item_a",
                  "image": "item_b", "shape": "item_b", "table": "item_b",
                  "footer": "vs_center"},
        distribute={"box": ["item_a", "item_b"], "bullet": ["item_a", "item_b"],
                    "text": ["item_a", "item_b"]},
        ai_guide="title→header, first box/bullet→item_a, second box/bullet→item_b",
    ),

    # ── Data ──
    "data_showcase": SlideArchetype(
        id="data_showcase",
        name="Data Showcase",
        description="Table or chart front-and-center — header + data + caption",
        regions=[
            ("header", 60, 30, 840, 72, 1),
            ("data", 60, 110, 840, 320, 2),
            ("caption", 60, 450, 840, 60, 3),
        ],
        zone_map={"title": "header", "subtitle": "header",
                  "table": "data", "image": "data", "shape": "data",
                  "text": "caption", "footer": "caption", "box": "caption"},
        ai_guide="title→header, table/image/shape→data, text/footer/box→caption",
    ),
    "grid_cards": SlideArchetype(
        id="grid_cards",
        name="Grid Cards (2×2)",
        description="Four equal cards — features, team, use cases (web analogy: 三列特性卡片区 / feature-card grid)",
        regions=[
            ("header", 60, 30, 840, 72, 1),
            ("card_tl", 60, 110, 400, 180, 2),
            ("card_tr", 500, 110, 400, 180, 2),
            ("card_bl", 60, 310, 400, 180, 2),
            ("card_br", 500, 310, 400, 180, 2),
        ],
        zone_map={"title": "header", "subtitle": "header",
                  "box": "card_tl", "image": "card_tl", "shape": "card_tl",
                  "text": "card_tl", "bullet": "card_tl"},
        distribute={"box": ["card_tl", "card_tr", "card_bl", "card_br"],
                    "image": ["card_tl", "card_tr", "card_bl", "card_br"],
                    "shape": ["card_tl", "card_tr", "card_bl", "card_br"]},
        ai_guide="title→header, boxes auto-distributed across 4 card slots by insertion order",
    ),

    # ── Visual / Image-driven ──
    "image_hero": SlideArchetype(
        id="image_hero",
        name="Image Hero",
        description="Large image dominates — text is supporting narration",
        regions=[
            ("header", 60, 30, 840, 72, 1),
            ("hero", 60, 110, 840, 340, 2),
            ("overlay", 60, 470, 840, 40, 3),
        ],
        zone_map={"title": "header", "subtitle": "header",
                  "image": "hero", "shape": "hero",
                  "text": "overlay", "footer": "overlay", "box": "overlay"},
        ai_guide="title→header, image→hero (full bleed), text/caption→overlay",
    ),

    # ── Closing ──
    "conclusion": SlideArchetype(
        id="conclusion",
        name="Conclusion / CTA",
        description="Final slide — key takeaway + next step",
        regions=[
            ("center", 120, 120, 720, 260, 1),
            ("footer", 120, 420, 720, 80, 2),
        ],
        zone_map={"title": "center", "text": "center", "box": "center",
                  "bullet": "center", "shape": "center",
                  "footer": "footer", "subtitle": "footer"},
        ai_guide="title/text/box/bullet→center, footer→footer",
    ),
    "section": SlideArchetype(
        id="section",
        name="Section Divider",
        description="Chapter break — large number, section title, brief description",
        regions=[
            ("number", 60, 80, 200, 120, 1),
            ("title", 280, 80, 620, 80, 2),
            ("subtitle", 280, 180, 620, 240, 3),
        ],
        zone_map={"shape": "number", "image": "number",
                  "title": "title", "subtitle": "subtitle",
                  "text": "subtitle", "box": "subtitle", "bullet": "subtitle"},
        ai_guide="shape/image→number, title→title, subtitle/text/box→subtitle",
    ),

    # ── Emotional / Social ──
    "quote": SlideArchetype(
        id="quote",
        name="Quote / Testimonial",
        description="Large quote + attribution — minimal, high impact",
        regions=[
            ("quote", 120, 120, 720, 260, 1),
            ("attribution", 480, 400, 400, 60, 2),
        ],
        zone_map={"title": "quote", "text": "quote", "box": "quote",
                  "subtitle": "attribution", "footer": "attribution",
                  "shape": "quote"},
        ai_guide="title/text→quote, subtitle/footer→attribution",
    ),
    "timeline": SlideArchetype(
        id="timeline",
        name="Timeline / Roadmap",
        description="Horizontal timeline with milestone nodes",
        regions=[
            ("header", 60, 30, 840, 72, 1),
            ("track", 60, 240, 840, 60, 2),
            ("nodes", 60, 130, 840, 90, 3),
            ("labels", 60, 320, 840, 180, 4),
        ],
        zone_map={"title": "header", "subtitle": "header",
                  "shape": "track", "box": "labels", "text": "labels",
                  "bullet": "labels", "image": "nodes"},
        ai_guide="title→header, shape→track, box/text/bullet→labels, image→nodes",
    ),

    # ── Escape hatch ──
    "blank": SlideArchetype(
        id="blank",
        name="Blank Canvas",
        description="Single full-page region — you place everything",
        regions=[
            ("main", 60, 60, 840, 420, 1),
        ],
        zone_map={},
        ai_guide="everything→main, you control placement",
    ),
}


def get_archetype(archetype_id: str) -> SlideArchetype:
    if archetype_id not in ARCHETYPES:
        raise KeyError(f"Unknown archetype: {archetype_id}. Valid: {sorted(ARCHETYPES.keys())}")
    return ARCHETYPES[archetype_id]


_BUILTIN_IDS = frozenset(ARCHETYPES)


def register_archetype(archetype: SlideArchetype) -> None:
    """Register a runtime archetype (e.g. a layout extracted from a reference
    PPTX). Registered archetypes are visible to get_archetype() and
    list_archetypes() exactly like built-ins."""
    ARCHETYPES[archetype.id] = archetype


def unregister_archetype(archetype_id: str) -> None:
    """Remove a runtime-registered archetype. Built-ins are not removable."""
    if archetype_id in ARCHETYPES and archetype_id not in _BUILTIN_IDS:
        del ARCHETYPES[archetype_id]


def list_archetypes() -> list[dict]:
    """Lightweight list for AI agent to pick an archetype."""
    return [
        {"id": aid, "name": a.name, "description": a.description, "guide": a.ai_guide}
        for aid, a in ARCHETYPES.items()
    ]


# ═══════════════════════════════════════════════════════════
# Parameterized resolution — columns / gap / density
# ═══════════════════════════════════════════════════════════

_CANVAS_W = 960
_CANVAS_H = 540
_PAGE_MARGIN = 60                    # left/right margin preserved in grid layouts
_GRID_CONTENT_W = _CANVAS_W - 2 * _PAGE_MARGIN   # 840pt content width
_GRID_TOP = 110                      # card area top (below the fixed header)
_GRID_HEIGHT = 380                   # default card area height (y 110..490)
_DEFAULT_GAP = 40                    # default column gutter (matches original grid_cards)
_MIN_BOTTOM_MARGIN = 20              # floor kept when density grows the card area
_N_CARDS = 4                         # grid_cards is "four equal cards"

# density → scale applied to gap and to the card-area height
_DENSITY_SCALE = {
    "compact": 0.75,
    "normal": 1.0,
    "airy": 1.25,
}

_GRID_PARAMS = ("columns", "gap", "density")
_GRID_ARCHETYPES = frozenset({"grid_cards"})


def _copy_archetype(base: SlideArchetype) -> SlideArchetype:
    """Deep-enough copy so the returned instance never shares mutable state
    with the registry's instance."""
    return replace(
        base,
        regions=list(base.regions),
        zone_map=dict(base.zone_map),
        distribute={k: list(v) for k, v in base.distribute.items()},
    )


def resolve_archetype(archetype_id: str, params: dict | None = None) -> SlideArchetype:
    """Resolve an archetype with optional layout parameters.

    Returns a NEW SlideArchetype instance; the global ARCHETYPES registry is
    never mutated. With no params (or {}), the returned instance is a copy of
    the built-in layout.

    Parameters (all optional — omit to keep the built-in layout):
      - columns: int 1..4            (grid_cards only) number of columns for the
                                      four cards.
      - gap:     positive number     (grid_cards only) gutter between cards, pt.
      - density: "compact"|"normal"|"airy"
                                     (grid_cards only) scales gap and card-area
                                      height proportionally.
    """
    base = get_archetype(archetype_id)

    if not params:
        return _copy_archetype(base)

    unknown = set(params) - set(_GRID_PARAMS)
    if unknown:
        raise ValueError(
            f"Unsupported parameter(s) {sorted(unknown)} for archetype "
            f"{archetype_id!r}; supported: {list(_GRID_PARAMS)}"
        )

    if archetype_id not in _GRID_ARCHETYPES:
        raise ValueError(
            f"Archetype {archetype_id!r} does not accept layout parameters "
            f"(columns/gap/density); supported archetypes: "
            f"{sorted(_GRID_ARCHETYPES)}"
        )

    # ── validate values ──
    columns = params.get("columns", 2)
    if isinstance(columns, bool) or not isinstance(columns, int) \
            or not (1 <= columns <= 4):
        raise ValueError(f"columns must be an int in 1..4, got {columns!r}")

    gap = params.get("gap", _DEFAULT_GAP)
    if isinstance(gap, bool) or not isinstance(gap, (int, float)) or gap <= 0:
        raise ValueError(f"gap must be a positive number (pt), got {gap!r}")

    density = normalize_density(params.get("density", "normal"))
    if density not in _DENSITY_SCALE:
        raise ValueError(
            f"density must be one of {sorted(_DENSITY_SCALE)}, got {density!r}"
        )

    # ── compute card grid ──
    s = _DENSITY_SCALE[density]
    col_gap = gap * s                     # horizontal gutter
    row_gap = col_gap / 2                 # vertical rhythm = half the gutter
    # card-area height scales with density, clamped to keep a bottom margin
    grid_h = min(_GRID_HEIGHT * s, _CANVAS_H - _GRID_TOP - _MIN_BOTTOM_MARGIN)

    n_rows = (_N_CARDS + columns - 1) // columns

    col_w = (_GRID_CONTENT_W - (columns - 1) * col_gap) / columns
    if col_w <= 0:
        raise ValueError(
            f"gap {gap!r} is too large for {columns} column(s) within "
            f"{_GRID_CONTENT_W}pt content width"
        )
    row_h = (grid_h - (n_rows - 1) * row_gap) / n_rows
    if row_h <= 0:
        raise ValueError(
            f"gap {gap!r} with density {density!r} is too large for "
            f"{n_rows} row(s) within {grid_h:g}pt content height"
        )

    regions = [("header", 60, 30, 840, 72, 1)]
    card_names = []
    for i in range(_N_CARDS):
        r = i // columns
        c = i % columns
        x = _PAGE_MARGIN + c * (col_w + col_gap)
        y = _GRID_TOP + r * (row_h + row_gap)
        name = f"card_{i}"
        regions.append((name, round(x, 2), round(y, 2),
                        round(col_w, 2), round(row_h, 2), 2))
        card_names.append(name)

    zone_map = {"title": "header", "subtitle": "header",
                "box": "card_0", "image": "card_0", "shape": "card_0",
                "text": "card_0", "bullet": "card_0"}
    distribute = {"box": list(card_names),
                  "image": list(card_names),
                  "shape": list(card_names)}
    ai_guide = (f"title→header, boxes auto-distributed across {_N_CARDS} card "
                f"slots ({columns}×{n_rows}) by insertion order")

    return replace(
        base,
        regions=regions,
        zone_map=zone_map,
        distribute=distribute,
        ai_guide=ai_guide,
    )


# ═══════════════════════════════════════════════════════════
# Layout policy — per-template archetype overrides
# ═══════════════════════════════════════════════════════════

@dataclass
class LayoutPolicy:
    """Template-level layout tuning — spacing, alignment, preferred archetypes."""
    title_align: str = "center"       # LEFT | CENTER — how titles sit in header
    content_inset: int = 12           # pt inset from region edge for text
    card_gap: int = 20                # pt gap between cards in grid layouts
    preferred_archetypes: list[str] = field(default_factory=list)  # first picks
    avoid_archetypes: list[str] = field(default_factory=list)      # never suggest


# Default layout policies per template
LAYOUT_POLICIES: dict[str, LayoutPolicy] = {
    "academic": LayoutPolicy(
        title_align="LEFT", content_inset=16, card_gap=16,
        preferred_archetypes=["content", "data_showcase", "two_column", "conclusion"],
        avoid_archetypes=["quote", "image_hero"],
    ),
    "business": LayoutPolicy(
        title_align="LEFT", content_inset=14, card_gap=18,
        preferred_archetypes=["content", "comparison", "data_showcase", "conclusion"],
        avoid_archetypes=["quote"],
    ),
    "minimal": LayoutPolicy(
        title_align="CENTER", content_inset=20, card_gap=24,
        preferred_archetypes=["title_cover", "content", "image_hero", "quote", "conclusion"],
        avoid_archetypes=["grid_cards", "data_showcase"],
    ),
    "data_report": LayoutPolicy(
        title_align="LEFT", content_inset=10, card_gap=12,
        preferred_archetypes=["data_showcase", "comparison", "grid_cards", "content"],
        avoid_archetypes=["quote", "image_hero"],
    ),
    "teaching": LayoutPolicy(
        title_align="LEFT", content_inset=18, card_gap=22,
        preferred_archetypes=["content", "two_column", "comparison", "section", "timeline"],
        avoid_archetypes=[],
    ),
    "product": LayoutPolicy(
        title_align="CENTER", content_inset=16, card_gap=20,
        preferred_archetypes=["title_cover", "image_hero", "grid_cards", "quote", "conclusion"],
        avoid_archetypes=["data_showcase"],
    ),
}


def get_layout_policy(template_id: str) -> LayoutPolicy:
    return LAYOUT_POLICIES.get(template_id, LayoutPolicy())
