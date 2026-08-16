"""T1: OKLCH color math — sRGB↔OKLCH, hue_distance, chroma, lightness.

Cross-check: colour-science is not a hard dependency. When it IS installed we run
a live comparison against it (tolerance 1e-4); otherwise we assert against Ottosson's
canonical OKLab reference values for the sRGB primaries (the same values
colour-science reproduces).
"""
import pytest

from ppt_reflex.grid.oklch import (
    srgb_to_oklch, oklch_to_srgb, hue_distance, chroma, lightness,
)


# Ottosson (2020) canonical OKLab values for the sRGB primaries.
_CANONICAL_OKLAB = {
    (255, 0, 0):   (0.6279553606, 0.2248630611, 0.1258462985),
    (0, 255, 0):   (0.8664396115, -0.2338874192, 0.1794983757),
    (0, 0, 255):   (0.4520137183, -0.0324569840, -0.3115281470),
    (255, 255, 255): (1.0, 0.0, 0.0),
    (0, 0, 0):       (0.0, 0.0, 0.0),
}


def _C(a, b):
    return (a * a + b * b) ** 0.5


def test_canonical_primaries_match_reference():
    """sRGB primaries → OKLab L/a/b matches Ottosson's canonical values (1e-4)."""
    for rgb, (L, a, b) in _CANONICAL_OKLAB.items():
        got = srgb_to_oklch(rgb)
        # OKLCH packs a,b into C (chroma) — recover via chroma + hue
        import math
        a_got = got["C"] * math.cos(math.radians(got["h"]))
        b_got = got["C"] * math.sin(math.radians(got["h"]))
        assert got["L"] == pytest.approx(L, abs=1e-4), rgb
        assert a_got == pytest.approx(a, abs=1e-4), rgb
        assert b_got == pytest.approx(b, abs=1e-4), rgb


def test_roundtrip_srgb_oklch():
    """sRGB → OKLCH → sRGB is the identity within rounding noise."""
    for rgb in [(10, 20, 30), (255, 0, 0), (0, 128, 255), (240, 240, 240),
                (123, 45, 67), (0, 0, 0), (255, 255, 255)]:
        back = oklch_to_srgb(srgb_to_oklch(rgb))
        for a, b in zip(rgb, back):
            assert abs(a - b) <= 2, (rgb, back)


def test_hue_distance_shortest_arc():
    assert hue_distance(10, 20) == pytest.approx(10, abs=1e-9)
    assert hue_distance(350, 10) == pytest.approx(20, abs=1e-9)
    assert hue_distance(0, 180) == pytest.approx(180, abs=1e-9)
    assert hue_distance(0, 200) == pytest.approx(160, abs=1e-9)
    assert hue_distance(30, 30) == pytest.approx(0, abs=1e-9)


def test_chroma_lightness_accessors():
    c = srgb_to_oklch((255, 0, 0))
    assert chroma(c) == pytest.approx(_C(0.2248630611, 0.1258462985), abs=1e-4)
    assert lightness(c) == pytest.approx(0.6279553606, abs=1e-4)
    # tuple form
    assert chroma((0.5, 0.2, 90)) == pytest.approx(0.2)
    assert lightness((0.5, 0.2, 90)) == pytest.approx(0.5)


def test_live_colour_science_crosscheck():
    """If colour-science is installed, cross-check 1e-4. Otherwise skip (documented)."""
    colour = pytest.importorskip("colour")
    from colour.models import RGB_to_OKLab
    from colour.utilities import to_domain_1
    samples = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (128, 128, 128), (255, 255, 255)]
    for rgb in samples:
        ref = RGB_to_OKLab(to_domain_1([rgb[0] / 255, rgb[1] / 255, rgb[2] / 255]))
        got = srgb_to_oklch(rgb)
        import math
        a_got = got["C"] * math.cos(math.radians(got["h"]))
        b_got = got["C"] * math.sin(math.radians(got["h"]))
        assert got["L"] == pytest.approx(float(ref[0]), abs=1e-4)
        assert a_got == pytest.approx(float(ref[1]), abs=1e-4)
        assert b_got == pytest.approx(float(ref[2]), abs=1e-4)


if __name__ == "__main__":
    test_canonical_primaries_match_reference()
    test_roundtrip_srgb_oklch()
    test_hue_distance_shortest_arc()
    test_chroma_lightness_accessors()
    print("\n✓ All OKLCH tests PASSED")
