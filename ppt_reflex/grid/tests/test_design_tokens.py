"""grid/tests/test_design_tokens.py — 设计 token 资产层（档位 + 配方）验证"""
import pytest

from ppt_reflex.grid.design_tokens import (
    load_tokens,
    get_token,
    load_recipes,
    resolve_recipe,
)


def test_load_tokens_categories():
    """tokens.json 应含五个档位类别，且值符合约定。"""
    tokens = load_tokens()
    assert set(tokens) == {"spacing", "radius", "shadow", "type_scale", "color"}
    assert tokens["spacing"] == {"sm": 8, "md": 16, "lg": 24, "xl": 40}
    assert tokens["radius"]["none"] == 0
    assert tokens["type_scale"]["xxl"] == 36


def test_get_token_values():
    """get_token 返回档位的具体数值。"""
    assert get_token("spacing", "md") == 16
    assert get_token("spacing", "xl") == 40
    assert get_token("radius", "lg") == 16
    assert get_token("type_scale", "lg") == 20
    assert get_token("color", "accent") == "#1D4ED8"
    shadow = get_token("shadow", "sm")
    assert isinstance(shadow, dict)
    assert shadow == {"blur_pt": 4, "dist_pt": 2, "opacity": 0.12}


def test_get_token_invalid_level_lists_valid():
    """无效档位抛 KeyError 并列出合法档位。"""
    with pytest.raises(KeyError) as ei:
        get_token("spacing", "huge")
    msg = str(ei.value)
    assert "spacing" in msg
    assert "huge" in msg
    assert "Valid" in msg
    for valid in ("sm", "md", "lg", "xl"):
        assert valid in msg


def test_get_token_invalid_category_lists_valid():
    """无效类别抛 KeyError 并列出合法类别。"""
    with pytest.raises(KeyError) as ei:
        get_token("nonexistent", "md")
    msg = str(ei.value)
    assert "nonexistent" in msg
    assert "Valid" in msg
    assert "spacing" in msg
    assert "color" in msg


def test_load_recipes_has_three():
    """card / kpi / quote 三个配方都存在，且引用档位名而非裸数值。"""
    recipes = load_recipes()
    for name in ("card", "kpi", "quote"):
        assert name in recipes, f"missing recipe '{name}'"
    # 配方引用档位名（字符串），不写裸数值
    assert recipes["card"]["radius"] == "md"
    assert recipes["card"]["padding"] == "md"
    assert recipes["card"]["shadow"] == "sm"
    assert recipes["card"]["fill"] == "surface"
    assert recipes["kpi"]["value_size"] == "xl"
    assert recipes["quote"]["fill"] == "accent_soft"


def test_resolve_recipe_card():
    """card 配方展开后 token 名全部替换为数值。"""
    r = resolve_recipe("card")
    assert r["shape"] == "rounded_rectangle"
    assert r["radius"] == 8
    assert r["padding"] == 16
    assert r["shadow"] == {"blur_pt": 4, "dist_pt": 2, "opacity": 0.12}
    assert r["fill"] == "#F4F6F9"
    assert r["stroke"] == "#E2E8F0"
    assert r["text_color"] == "#0F172A"
    assert r["title_size"] == 20
    assert r["body_size"] == 16


def test_resolve_recipe_kpi():
    """kpi 配方展开正确。"""
    r = resolve_recipe("kpi")
    assert r["shape"] == "rounded_rectangle"
    assert r["value_size"] == 28
    assert r["value_color"] == "#1D4ED8"
    assert r["label_size"] == 12
    assert r["shadow"] == {"blur_pt": 8, "dist_pt": 4, "opacity": 0.18}
    assert r["accent_bar"] == "#1D4ED8"


def test_resolve_recipe_quote():
    """quote 配方展开正确。"""
    r = resolve_recipe("quote")
    assert r["shape"] == "rounded_rectangle"
    assert r["radius"] == 4
    assert r["padding"] == 40
    assert r["fill"] == "#E8EEFC"
    assert r["body_size"] == 20
    assert r["attribution_size"] == 12


def test_resolve_recipe_no_residual_token_names():
    """所有配方展开后不得残留任何 token 档位名。"""
    tokens = load_tokens()
    level_names = set()
    for tier in tokens.values():
        level_names.update(tier.keys())

    def collect_strings(v):
        out = set()
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for x in v.values():
                out |= collect_strings(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                out |= collect_strings(x)
        return out

    for name in load_recipes():
        resolved = resolve_recipe(name)
        residual = collect_strings(resolved) & level_names
        assert not residual, f"recipe '{name}' residual token names: {residual}"


def test_resolve_recipe_unknown_name():
    """未知配方抛 KeyError。"""
    with pytest.raises(KeyError):
        resolve_recipe("not_a_recipe")


def test_resolve_recipe_unknown_level(monkeypatch):
    """配方引用未知档位时 resolve_recipe 抛 KeyError。"""
    import ppt_reflex.grid.design_tokens as dt

    monkeypatch.setattr(dt, "load_recipes", lambda: {"bad": {"radius": "huge"}})
    with pytest.raises(KeyError) as ei:
        dt.resolve_recipe("bad")
    assert "huge" in str(ei.value)


if __name__ == "__main__":
    test_load_tokens_categories()
    test_get_token_values()
    test_load_recipes_has_three()
    test_resolve_recipe_card()
    test_resolve_recipe_kpi()
    test_resolve_recipe_quote()
    test_resolve_recipe_no_residual_token_names()
    print("\nAll design_tokens tests PASSED")
