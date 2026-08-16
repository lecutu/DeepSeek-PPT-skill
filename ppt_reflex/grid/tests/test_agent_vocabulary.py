"""T7: agent vocabulary aliases + strict unknown_parameter rejection."""
import pytest

from ppt_reflex.builder import PPTBuilder
from ppt_reflex.grid.agent_vocabulary import (
    normalize_fit_mode, normalize_density, vocabulary_table,
)
from ppt_reflex.grid.archetypes import resolve_archetype


def test_fit_mode_contain_equals_fit():
    b = PPTBuilder(template="academic")
    a = b.image("nonexistent.png", fit_mode="contain")
    c = b.image("nonexistent.png", fit_mode="fit")
    assert a.fit_mode == c.fit_mode == "fit"


def test_fit_mode_cover_equals_fill():
    b = PPTBuilder(template="academic")
    a = b.image("nonexistent.png", fit_mode="cover")
    c = b.image("nonexistent.png", fit_mode="fill")
    assert a.fit_mode == c.fit_mode == "fill"


def test_box_radius_alias():
    b = PPTBuilder(template="academic")
    spec = b.box("card", radius=8)
    assert spec.corner_radius == 8


def test_box_margin_auto_rejected():
    b = PPTBuilder(template="academic")
    with pytest.raises(ValueError, match="unknown_parameter"):
        b.box("x", margin="auto")


def test_box_spacing_rejected():
    b = PPTBuilder(template="academic")
    with pytest.raises(ValueError, match="unknown_parameter"):
        b.box("x", spacing="comfortable")


def test_density_aliases():
    assert normalize_density("comfortable") == "normal"
    assert normalize_density("spacious") == "airy"
    assert normalize_density("compact") == "compact"


def test_density_alias_in_resolve_archetype():
    comf = resolve_archetype("grid_cards", {"density": "comfortable"})
    normal = resolve_archetype("grid_cards", {"density": "normal"})
    assert comf.regions == normal.regions


def test_vocabulary_table_generated():
    rows = vocabulary_table()
    domains = {r["domain"] for r in rows}
    assert "image.fit_mode" in domains
    assert "params.density" in domains
    assert any(r["css_vocab"] == "contain" for r in rows)
    assert any(r["css_vocab"] == "margin" and r["internal"] == "REJECT" for r in rows)


if __name__ == "__main__":
    test_fit_mode_contain_equals_fit()
    test_fit_mode_cover_equals_fill()
    test_box_radius_alias()
    test_box_margin_auto_rejected()
    test_box_spacing_rejected()
    test_density_aliases()
    test_density_alias_in_resolve_archetype()
    test_vocabulary_table_generated()
    print("\n✓ All agent-vocabulary tests PASSED")
