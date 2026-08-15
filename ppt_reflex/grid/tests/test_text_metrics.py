"""Tests for real PIL glyph measurement in grid.text_metrics.

Verifies the swap from em-based estimation to PIL FreeType advance widths:
  1. concrete width value for CJK (real metric, not heuristic)
  2. real Latin width differs from the old per-char estimate
  3. LRU cache is effective (repeat measurement hits cache)
  4. fallback path (font missing) does not crash
"""
import sys

import pytest

from ppt_reflex.grid import text_metrics as tm


def test_font_resolves_to_yahei_on_windows():
    if sys.platform != "win32":
        pytest.skip("Microsoft YaHei is a Windows font")
    path = tm._resolve_font_path()
    assert path is not None
    assert "msyh" in path.lower()


def test_cjk_width_concrete_value():
    # 10 CJK chars: YaHei advance = exactly 1.0em/char → 20pt × 10 = 200pt
    w = tm._line_width("一二三四五六七八九十", 20)
    assert w == pytest.approx(200.0, abs=0.6)


def test_latin_real_differs_from_old_estimate():
    text = "HelloWorld"
    real = tm._line_width(text, 20)
    old_estimate = sum(tm._char_width_em(ch) for ch in text) * 20
    assert real > 0
    # real glyph advances must not equal the heuristic per-char estimate
    assert real != pytest.approx(old_estimate, abs=0.5)


def test_measurement_cache_effective():
    tm._measure_width.cache_clear()
    text = "缓存命中测试文本"
    a = tm._line_width(text, 18)
    before = tm._measure_width.cache_info()
    b = tm._line_width(text, 18)
    after = tm._measure_width.cache_info()

    assert a == b
    assert after.hits == before.hits + 1
    assert after.currsize >= 1


def test_control_chars_stripped():
    # tab/zero-width/newline contribute no advance (mirrors old semantics)
    plain = tm._line_width("AB", 20)
    with_controls = tm._line_width("A\tB\u200b", 20)
    assert with_controls == pytest.approx(plain, abs=0.01)


def test_empty_line_zero_width():
    assert tm._line_width("", 20) == 0.0


def test_fallback_does_not_crash(monkeypatch):
    # Simulate Microsoft YaHei missing → resolve to PIL default font.
    monkeypatch.setattr(tm, "_find_font_path", lambda: None)
    tm._resolved_font_path = None
    tm._resolved_font_ready = False
    tm._font_object_cache.clear()
    tm._measure_width.cache_clear()
    try:
        w_cjk = tm._line_width("你好世界", 12)
        w_latin = tm._line_width("Hello", 12)
        w_empty = tm._line_width("", 12)
        assert isinstance(w_cjk, float) and w_cjk >= 0.0
        assert isinstance(w_latin, float) and w_latin >= 0.0
        assert w_empty == 0.0
    finally:
        # Re-resolve the real font on the next call and drop polluted caches.
        tm._resolved_font_path = None
        tm._resolved_font_ready = False
        tm._font_object_cache.clear()
        tm._measure_width.cache_clear()
