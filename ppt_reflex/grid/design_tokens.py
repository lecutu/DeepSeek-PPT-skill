"""
grid/design_tokens.py — Design token asset layer (tiered + component recipes).

Discipline: AI references level names (get_token) and recipe names (resolve_recipe)
ONLY — never raw numbers. Humans own the raw values in tokens.json / recipes.json.

Public API:
    load_tokens()                    -> {category: {level: value}}
    get_token(category, level)       -> value
    load_recipes()                   -> {recipe_name: {field: level_name_or_literal}}
    resolve_recipe(name)             -> recipe with every level name replaced by its value

JSON assets are re-read on every call so a human edit takes effect immediately
(no stale cache; builder.py wires this in later).
"""
from __future__ import annotations

import json
import os

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))   # ppt_reflex/grid/
_ASSET_DIR = os.path.dirname(_PKG_DIR)                  # ppt_reflex/
_TOKENS_PATH = os.path.join(_ASSET_DIR, "tokens.json")
_RECIPES_PATH = os.path.join(_ASSET_DIR, "recipes.json")

# Recipe field -> token category. A missing entry means a literal passthrough
# (e.g. "shape": "rounded_rectangle"). To add a new token-reference field, add it
# here with its token category.
_TOKEN_KEY_CATEGORY: dict[str, str] = {
    "radius": "radius",
    "padding": "spacing",
    "gap": "spacing",
    "shadow": "shadow",
    "fill": "color",
    "stroke": "color",
    "text_color": "color",
    "title_color": "color",
    "body_color": "color",
    "value_color": "color",
    "label_color": "color",
    "attribution_color": "color",
    "accent_bar": "color",
    "title_size": "type_scale",
    "body_size": "type_scale",
    "value_size": "type_scale",
    "label_size": "type_scale",
    "attribution_size": "type_scale",
}


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _public(data: dict) -> dict:
    """Strip underscore-prefixed metadata keys (e.g. _meta) from an asset dict."""
    return {k: v for k, v in data.items() if not k.startswith("_")}


def load_tokens() -> dict:
    """Read tokens.json. Returns {category: {level: value}} (no metadata keys)."""
    return _public(_load(_TOKENS_PATH))


def load_recipes() -> dict:
    """Read recipes.json. Returns {recipe_name: {field: value}} (no metadata keys).
    Each value is either a token level name or a literal (e.g. "rounded_rectangle")."""
    return _public(_load(_RECIPES_PATH))


def get_token(category: str, level: str):
    """Return the concrete value of a design-token level.

    Examples:
        get_token("spacing", "md") == 16
        get_token("color", "accent") == "#1D4ED8"

    Raises KeyError on an unknown category or level; the message lists the valid
    choices so the caller (or an AI) can self-correct.
    """
    tokens = load_tokens()
    if category not in tokens:
        raise KeyError(
            f"Unknown token category '{category}'. Valid: {sorted(tokens)}"
        )
    tier = tokens[category]
    if level not in tier:
        raise KeyError(
            f"Unknown {category} level '{level}'. Valid: {sorted(tier)}"
        )
    return tier[level]


def resolve_recipe(name: str) -> dict:
    """Expand a recipe into final parameter values.

    Every field whose key is a known token reference is looked up in its token
    category, replacing the level name with the concrete value (number, hex string,
    or shadow dict). Literal fields (e.g. "shape") pass through unchanged.

    Raises KeyError on an unknown recipe name, or on a token reference that points
    at an unknown level.
    """
    recipes = load_recipes()
    if name not in recipes:
        raise KeyError(f"Unknown recipe '{name}'. Valid: {sorted(recipes)}")

    tokens = load_tokens()
    resolved: dict = {}
    for field, ref in recipes[name].items():
        category = _TOKEN_KEY_CATEGORY.get(field)
        if category is None:
            resolved[field] = ref  # literal passthrough (shape name etc.)
            continue
        tier = tokens[category]
        if ref not in tier:
            raise KeyError(
                f"Recipe '{name}' field '{field}' references unknown "
                f"{category} level '{ref}'. Valid: {sorted(tier)}"
            )
        resolved[field] = tier[ref]
    return resolved
