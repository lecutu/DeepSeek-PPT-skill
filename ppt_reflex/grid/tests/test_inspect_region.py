"""T9: region-scoped inspect_slide — no render, T5-consistent output schema."""
from ppt_reflex.builder import PPTBuilder


def _builder():
    b = PPTBuilder(template="business", style="corporate_minimal")
    b.add_slide("Cover", archetype="title_cover",
                elements=[b.title("Title"), b.subtitle("Sub"), b.box("Card", recipe="card")])
    return b


def test_inspect_slide_full_scope_has_t5_channels():
    r = _builder().inspect_slide(0)
    assert r["ok"] is True
    assert r["scope"] == "slide"
    assert "violations" in r and "signals" in r


def test_inspect_slide_region_scope():
    b = _builder()
    ids = [e.elem_id for e in b._slides[0].elements]
    r = b.inspect_slide(0, elem_ids=[ids[-1]])
    assert r["scope"] == "region"
    assert "region" in r
    for key in ("local_density", "page_density", "font_size_levels",
                "pairwise_contrast", "local_color_ratio", "alignment_residual_pt",
                "gap_sequence_std_pt"):
        assert key in r["region"], key
    assert ids[-1] in r["elem_ids"]


def test_inspect_slide_bad_index():
    r = _builder().inspect_slide(99)
    assert r["ok"] is False


if __name__ == "__main__":
    test_inspect_slide_full_scope_has_t5_channels()
    test_inspect_slide_region_scope()
    test_inspect_slide_bad_index()
    print("\n✓ All inspect-region tests PASSED")
