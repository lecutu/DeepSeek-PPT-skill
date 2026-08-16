"""
grid/oklch.py — sRGB ↔ OKLCH color conversion + hue/chroma/lightness helpers.

Perceptual color space used by the harmony floor (composition.py T2–T4). OKLCH is
hue-linear, so hue relationships (analogous / complementary / triadic) and chroma
thresholds behave predictably across the whole wheel — unlike HSV/RGB, where the
perceptual distance between two hues depends on where they sit.

Implementation is the hand-written OKLab matrix (Björn Ottosson, 2020). colour-science
is NOT a runtime dependency; the unit tests cross-check against Ottosson's canonical
reference values (the same values colour-science reproduces) to 1e-4, and additionally
run a live colour-science comparison when that package happens to be installed.

Conventions:
  - sRGB: tuple[int, int, int] in 0..255 (matches grid/color_utils.py hex_to_rgb).
  - OKLCH: {"L": 0..1, "C": 0..~0.32 (unnormalized OKLab chroma), "h": 0..360 degrees}
  - L is OKLab lightness (0 = black, 1 = white). C is the unnormalized OKLab chroma
    (sRGB max ≈ 0.32), so the T4 "high chroma" threshold C > 0.15 is meaningful.
"""

from __future__ import annotations

import math

# sRGB → linear sRGB → LMS → LMS' → OKLab (Ottosson 2020)
_LMS_FROM_LINEAR = (
    (0.4122214708, 0.5363325363, 0.0514459929),
    (0.2119034982, 0.6806995451, 0.1073969566),
    (0.0883024619, 0.2817188376, 0.6299787005),
)

_OKLAB_FROM_LMS = (
    (0.2104542553, 0.7936177850, -0.0040720468),
    (1.9779984951, -2.4285922050, 0.4505937099),
    (0.0259040371, 0.7827717662, -0.8086757660),
)

_LMS_FROM_OKLAB = (
    (1.0, 0.3963377774, 0.2158037573),
    (1.0, -0.1055613458, -0.0638541728),
    (1.0, -0.0894841775, -1.2914855480),
)

_LINEAR_FROM_LMS = (
    (4.0767416621, -3.3077115913, 0.2309699292),
    (-1.2684380046, 2.6097574011, -0.3413193965),
    (-0.0041960863, -0.7034186147, 1.7076147010),
)


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    if c <= 0.0031308:
        return c * 12.92
    return 1.055 * (c ** (1.0 / 2.4)) - 0.055


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def srgb_to_oklch(rgb: tuple) -> dict:
    """Convert an sRGB color (0..255 ints) to OKLCH {"L","C","h"}."""
    r, g, b = (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    r, g, b = _srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b)

    l = _LMS_FROM_LINEAR[0][0] * r + _LMS_FROM_LINEAR[0][1] * g + _LMS_FROM_LINEAR[0][2] * b
    m = _LMS_FROM_LINEAR[1][0] * r + _LMS_FROM_LINEAR[1][1] * g + _LMS_FROM_LINEAR[1][2] * b
    s = _LMS_FROM_LINEAR[2][0] * r + _LMS_FROM_LINEAR[2][1] * g + _LMS_FROM_LINEAR[2][2] * b

    l, m, s = math.cbrt(l), math.cbrt(m), math.cbrt(s)

    L = _OKLAB_FROM_LMS[0][0] * l + _OKLAB_FROM_LMS[0][1] * m + _OKLAB_FROM_LMS[0][2] * s
    a = _OKLAB_FROM_LMS[1][0] * l + _OKLAB_FROM_LMS[1][1] * m + _OKLAB_FROM_LMS[1][2] * s
    b = _OKLAB_FROM_LMS[2][0] * l + _OKLAB_FROM_LMS[2][1] * m + _OKLAB_FROM_LMS[2][2] * s

    C = math.hypot(a, b)
    h = math.degrees(math.atan2(b, a)) % 360.0
    return {"L": L, "C": C, "h": h}


def oklch_to_srgb(lch) -> tuple:
    """Convert OKLCH (dict or (L, C, h) tuple) to sRGB (0..255 ints, clamped)."""
    if isinstance(lch, dict):
        L, C, h = lch["L"], lch["C"], lch["h"]
    else:
        L, C, h = lch[0], lch[1], lch[2]

    hr = math.radians(h)
    a = C * math.cos(hr)
    b = C * math.sin(hr)

    l = _LMS_FROM_OKLAB[0][0] * L + _LMS_FROM_OKLAB[0][1] * a + _LMS_FROM_OKLAB[0][2] * b
    m = _LMS_FROM_OKLAB[1][0] * L + _LMS_FROM_OKLAB[1][1] * a + _LMS_FROM_OKLAB[1][2] * b
    s = _LMS_FROM_OKLAB[2][0] * L + _LMS_FROM_OKLAB[2][1] * a + _LMS_FROM_OKLAB[2][2] * b

    l, m, s = l ** 3, m ** 3, s ** 3

    r = _LINEAR_FROM_LMS[0][0] * l + _LINEAR_FROM_LMS[0][1] * m + _LINEAR_FROM_LMS[0][2] * s
    g = _LINEAR_FROM_LMS[1][0] * l + _LINEAR_FROM_LMS[1][1] * m + _LINEAR_FROM_LMS[1][2] * s
    b = _LINEAR_FROM_LMS[2][0] * l + _LINEAR_FROM_LMS[2][1] * m + _LINEAR_FROM_LMS[2][2] * s

    r, g, b = _linear_to_srgb(r), _linear_to_srgb(g), _linear_to_srgb(b)
    return (
        round(_clamp01(r) * 255),
        round(_clamp01(g) * 255),
        round(_clamp01(b) * 255),
    )


def hue_distance(h1: float, h2: float) -> float:
    """Shortest angular distance between two hues (degrees, in [0, 180])."""
    d = abs(h1 - h2) % 360.0
    return 360.0 - d if d > 180.0 else d


def chroma(c) -> float:
    """OKLCH chroma of a color (dict {"L","C","h"} or (L, C, h) tuple)."""
    return c["C"] if isinstance(c, dict) else c[1]


def lightness(c) -> float:
    """OKLab lightness of a color (dict {"L","C","h"} or (L, C, h) tuple)."""
    return c["L"] if isinstance(c, dict) else c[0]


def is_chromatic(c, threshold: float = 0.05) -> bool:
    """True when a color carries enough chroma to participate in hue logic."""
    return chroma(c) > threshold
