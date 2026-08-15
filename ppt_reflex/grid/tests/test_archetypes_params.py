"""grid/tests/test_archetypes_params.py — resolve_archetype 参数化解析测试

覆盖：
  1. grid_cards columns=3 的列坐标正确性（三列 x 位置、总宽 ≤ 画布、边距保持）
  2. density 三档（compact/normal/airy）按比例缩放间距与卡片内容区高度
  3. 非法参数 / 非法组合 → ValueError
  4. 原实例不被污染（返回新实例；缺省 = 原样）
"""
import pytest

from ppt_reflex.grid.archetypes import (
    ARCHETYPES,
    SlideArchetype,
    get_archetype,
    resolve_archetype,
)


def _cards(arch: SlideArchetype):
    return [r for r in arch.regions if r[0] != "header"]


# ═══════════════════════════════════════════════════════════
# 1. columns
# ═══════════════════════════════════════════════════════════

def test_grid_cards_columns3_positions():
    arch = resolve_archetype("grid_cards", {"columns": 3})
    cards = _cards(arch)
    assert len(cards) == 4

    # 三列 x 位置：60 / 353.33 / 646.67（行 0 的 card_0/1/2）
    xs = sorted({c[1] for c in cards})
    assert xs == pytest.approx([60.0, 353.33, 646.67], abs=0.01)

    # 每列宽度一致，总宽不超画布，右缘回到 60pt 边距
    widths = {c[3] for c in cards}
    assert len(widths) == 1
    assert list(widths)[0] == pytest.approx(253.33, abs=0.01)
    right_edge = max(c[1] + c[3] for c in cards)
    assert right_edge <= 960
    assert right_edge == pytest.approx(900.0, abs=0.01)

    # header 保持不变（72pt 高：容纳 28pt 标题 + content_inset，2026-08 真测量后加高）
    header = next(r for r in arch.regions if r[0] == "header")
    assert header == ("header", 60, 30, 840, 72, 1)


def test_grid_cards_columns4_fits():
    arch = resolve_archetype("grid_cards", {"columns": 4})
    cards = _cards(arch)
    xs = sorted({c[1] for c in cards})
    assert len(xs) == 4                      # 4 列
    assert max(c[1] + c[3] for c in cards) <= 960


# ═══════════════════════════════════════════════════════════
# 2. density
# ═══════════════════════════════════════════════════════════

def test_density_tiers_scale():
    compact = _cards(resolve_archetype("grid_cards", {"density": "compact"}))
    normal = _cards(resolve_archetype("grid_cards", {"density": "normal"}))
    airy = _cards(resolve_archetype("grid_cards", {"density": "airy"}))

    def col_gap(cards):
        s = sorted(cards, key=lambda r: r[1])   # sort by x
        return s[1][1] - s[0][1] - s[0][3]      # card1.x - card0.x - card0.w

    def card_h(cards):
        return cards[0][4]

    # 间距与内容区高度随 density 单调放大
    assert col_gap(compact) < col_gap(normal) < col_gap(airy)
    assert card_h(compact) < card_h(normal) < card_h(airy)


# ═══════════════════════════════════════════════════════════
# 3. 非法参数 / 非法组合
# ═══════════════════════════════════════════════════════════

def test_columns_on_non_grid_raises():
    with pytest.raises(ValueError, match="does not accept layout parameters"):
        resolve_archetype("content", {"columns": 2})
    with pytest.raises(ValueError, match="does not accept layout parameters"):
        resolve_archetype("two_column", {"gap": 20})


def test_invalid_values_raise():
    with pytest.raises(ValueError, match="columns must be an int in 1..4"):
        resolve_archetype("grid_cards", {"columns": 5})
    with pytest.raises(ValueError, match="columns must be an int in 1..4"):
        resolve_archetype("grid_cards", {"columns": 0})
    with pytest.raises(ValueError, match="density must be one of"):
        resolve_archetype("grid_cards", {"density": "tight"})
    with pytest.raises(ValueError, match="gap must be a positive number"):
        resolve_archetype("grid_cards", {"gap": -1})


def test_unknown_param_raises():
    with pytest.raises(ValueError, match="Unsupported parameter"):
        resolve_archetype("grid_cards", {"columns": 2, "bogus": 1})


# ═══════════════════════════════════════════════════════════
# 4. 原实例不被污染
# ═══════════════════════════════════════════════════════════

def test_original_not_polluted():
    orig = get_archetype("grid_cards")
    orig_regions = list(orig.regions)

    resolved = resolve_archetype("grid_cards", {"columns": 3})

    assert resolved is not orig
    assert resolved.regions is not orig.regions
    assert orig.regions == orig_regions
    assert ARCHETYPES["grid_cards"].regions == orig_regions


def test_no_params_returns_new_copy():
    orig = get_archetype("grid_cards")
    resolved = resolve_archetype("grid_cards")

    assert resolved is not orig
    assert resolved.regions == orig.regions
    assert resolved.regions is not orig.regions
    assert resolved.distribute == orig.distribute
    assert resolved.distribute is not orig.distribute


if __name__ == "__main__":
    test_grid_cards_columns3_positions()
    test_grid_cards_columns4_fits()
    test_density_tiers_scale()
    test_columns_on_non_grid_raises()
    test_invalid_values_raise()
    test_unknown_param_raises()
    test_original_not_polluted()
    test_no_params_returns_new_copy()
    print("\n✓ All archetype-params tests PASSED")
