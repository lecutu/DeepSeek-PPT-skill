"""
grid/agent_vocabulary.py — CSS-isomorphic vocabulary → internal enum, single source.

The no-vision LLM's deepest muscle memory is CSS/HTML, so the agent-facing surface
accepts the CSS-flavored word for a thing alongside the internal enum. This module is
the ONE place that owns the mapping, so:
  - builder factory kwargs double-accept both spellings (aliases are ~zero-cost), and
  - the 10-prompt vocabulary section AND the interface-docs table are generated from
    the tables here (never hand-synced in three places).

Internal enums stay stable — nothing here renames density / primitives / styles.
"""

from __future__ import annotations

# ── fit_mode: CSS object-fit → internal fit/fill/crop_center ──
FIT_MODE_ALIASES = {
    "contain": "fit",           # object-fit: contain → no crop, letterboxed
    "cover": "fill",            # object-fit: cover → crop to fill the box
    "fit": "fit",
    "fill": "fill",
    "crop_center": "crop_center",
    "crop": "crop_center",
}

# ── density: CSS-ish spacing vocabulary → internal compact/normal/airy ──
DENSITY_ALIASES = {
    "comfortable": "normal",
    "spacious": "airy",
    "cozy": "compact",
    "compact": "compact",
    "normal": "normal",
    "airy": "airy",
}

# ── box() kwargs: CSS-ish spelling → internal _Spec field ──
BOX_KWARG_ALIASES = {
    "radius": "corner_radius",
}

# ── CSS hallucinations to REJECT (with an alternative) ──
FORBIDDEN_KWARGS = {
    "margin": "margins are engine-solved — use params density (comfortable/normal/airy) "
              "or an archetype's preset regions",
    "spacing": "spacing vocabulary lives in the params density tier "
               "(comfortable/normal/airy), not on an element",
    "padding": "internal padding comes from a recipe (card/kpi/quote) or tokens",
    "gap": "gap is an archetype param — grid_cards params={'gap': <pt>}",
    "z_index": "z-order is engine-solved from semantic role — use role='emphasis'/'backdrop'",
    "zindex": "z-order is engine-solved from semantic role — use role='emphasis'/'backdrop'",
    "position": "position is engine-solved from archetype regions",
    "float": "float is engine-solved from archetype regions",
    "display": "display is engine-solved — use an archetype",
    "border": "borders are engine-solved — use a recipe or the template contract",
    "box_shadow": "shadows come from the style preset / recipe, not a raw value",
    "opacity": "opacity is not an agent token — pick a style tier instead",
    "line_height": "line height is the template contract (line_spacing)",
    "text_align": "alignment is the 'align_h' kwarg (left/center/right)",
}


def normalize_fit_mode(value: str) -> str:
    """Map CSS object-fit vocabulary to the internal fit/fill/crop_center. Unknown
    values are returned unchanged (the renderer's own validation handles them)."""
    return FIT_MODE_ALIASES.get((value or "").lower(), value)


def normalize_density(value: str) -> str:
    """Map CSS-ish density vocabulary to compact/normal/airy."""
    return DENSITY_ALIASES.get((value or "").lower(), value)


def reject_unknown_kwargs(factory: str, kwargs: dict) -> None:
    """Strict mode: reject any remaining unknown kwarg. CSS hallucinations (margin:
    auto / percentage / rem / z-index …) get an explicit alternative; anything else
    gets a generic unknown_parameter error. Raises ValueError."""
    if not kwargs:
        return
    for k in sorted(kwargs):
        alt = FORBIDDEN_KWARGS.get(k)
        if alt:
            raise ValueError(
                f"unknown_parameter: '{factory}({k}=...)' is a CSS/HTML hallucination "
                f"the engine does not accept. Alternative: {alt}"
            )
        raise ValueError(
            f"unknown_parameter: '{factory}({k}=...)' is not a recognized kwarg. "
            f"Check the vocabulary table (grid/agent_vocabulary.py) for the accepted spelling."
        )


def vocabulary_table() -> list[dict]:
    """The single generated source for the prompt vocabulary section + interface docs."""
    rows = []
    for css, internal in sorted(FIT_MODE_ALIASES.items()):
        rows.append({"domain": "image.fit_mode", "css_vocab": css, "internal": internal})
    for css, internal in sorted(DENSITY_ALIASES.items()):
        rows.append({"domain": "params.density", "css_vocab": css, "internal": internal})
    for css, internal in sorted(BOX_KWARG_ALIASES.items()):
        rows.append({"domain": "box()", "css_vocab": css, "internal": internal})
    for css, hint in sorted(FORBIDDEN_KWARGS.items()):
        rows.append({"domain": "forbidden", "css_vocab": css, "internal": "REJECT", "hint": hint})
    return rows
