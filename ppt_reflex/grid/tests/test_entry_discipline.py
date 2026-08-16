"""T8: API entry discipline — raw color / type-scale-override tokens are rejected
in agent (strict) mode, and the human panel (strict_tokens=False) path stays open."""
import pytest

from ppt_reflex.builder import PPTBuilder


def _strict():
    return PPTBuilder(template="academic", style="academic_rigorous")


def test_box_fill_color_rejected():
    with pytest.raises(ValueError, match="raw_color_forbidden"):
        _strict().box("x", fill_color=(1, 2, 3))


def test_shape_font_color_rejected():
    with pytest.raises(ValueError, match="raw_color_forbidden"):
        _strict().shape("star", font_color=(1, 2, 3))


def test_shape_font_size_override_rejected():
    with pytest.raises(ValueError, match="raw_color_forbidden"):
        _strict().shape("star", font_size=40)


def test_divider_color_rejected():
    with pytest.raises(ValueError, match="raw_color_forbidden"):
        _strict().divider(color=(1, 2, 3))


def test_arrow_color_rejected():
    with pytest.raises(ValueError, match="raw_color_forbidden"):
        _strict().arrow("a", "b", color=(0x66, 0x66, 0x66))


def test_overrides_color_rejected():
    # bg_hex/accent_hex are T10 panel-palette relay (exempt); other raw color keys stay forbidden
    with pytest.raises(ValueError, match="raw_color_forbidden"):
        PPTBuilder(template="academic", overrides={"text_hex": "#000"})


def test_arrow_default_color_is_none():
    b = _strict()
    a = b.arrow("e_1", "e_2")
    assert a.color is None
    assert a.text_color is None


def test_recipe_color_allowed():
    # recipe is the sanctioned path — no raw color token
    spec = _strict().box("card", recipe="card")
    assert spec is not None


def test_human_panel_override_allowed():
    b = PPTBuilder(template="academic", overrides={"bg_hex": "#111111"}, strict_tokens=False)
    assert b._t.bg_hex == "#111111"


if __name__ == "__main__":
    test_box_fill_color_rejected()
    test_shape_font_color_rejected()
    test_shape_font_size_override_rejected()
    test_divider_color_rejected()
    test_arrow_color_rejected()
    test_overrides_color_rejected()
    test_arrow_default_color_is_none()
    test_recipe_color_allowed()
    test_human_panel_override_allowed()
    print("\n✓ All entry-discipline tests PASSED")
