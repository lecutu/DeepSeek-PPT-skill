"""Golden-set deck/slide definitions for the harmony floor regression (T6).

Each case is ONE slide: `positive=True` cases must produce harmony_ok=True; `positive=False`
cases must be blocked (harmony_ok=False) by at least one harmony rule. `expect_block`
names the primary rule expected to fire (documented + asserted by the runner).

Beautiful cases are built in strict agent mode (recipes + archetypes, no raw color);
ugly cases use strict_tokens=False because raw fills are exactly the escape hatch the
harmony floor is meant to catch.
"""

from __future__ import annotations


def _fill(rgb):
    return tuple(rgb)


GOLDEN_CASES = [
    # ── Beautiful (positive) — must all pass harmony_ok ──
    {
        "id": "beautiful_title_cover",
        "positive": True, "expect_block": None, "strict": True,
        "build": lambda b: b.add_slide("Cover", archetype="title_cover",
            elements=[b.title("Project Title"), b.subtitle("A one-line tagline")]),
    },
    {
        "id": "beautiful_content_bullets",
        "positive": True, "expect_block": None, "strict": True,
        "build": lambda b: b.add_slide("Content", archetype="content",
            elements=[b.title("Agenda"),
                      b.bullet("First point"), b.bullet("Second point"),
                      b.bullet("Third point")]),
    },
    {
        "id": "beautiful_two_column",
        "positive": True, "expect_block": None, "strict": True,
        "build": lambda b: b.add_slide("Two Col", archetype="two_column",
            elements=[b.title("Comparison"),
                      b.box("Left card", recipe="card"),
                      b.box("Right card", recipe="card")]),
    },
    {
        "id": "beautiful_grid_cards",
        "positive": True, "expect_block": None, "strict": True,
        "build": lambda b: b.add_slide("Grid", archetype="grid_cards",
            elements=[b.title("Features"),
                      b.box("A", recipe="card"), b.box("B", recipe="card"),
                      b.box("C", recipe="card"), b.box("D", recipe="card")]),
    },
    {
        "id": "beautiful_data_showcase",
        "positive": True, "expect_block": None, "strict": True,
        "build": lambda b: b.add_slide("Data", archetype="data_showcase",
            elements=[b.title("Results"),
                      b.table(["A", "B"], [["1", "2"], ["3", "4"]])]),
    },
    {
        "id": "beautiful_comparison",
        "positive": True, "expect_block": None, "strict": True,
        "build": lambda b: b.add_slide("A vs B", archetype="comparison",
            elements=[b.title("Options"),
                      b.box("Option A", recipe="card"),
                      b.box("Option B", recipe="card")]),
    },
    {
        "id": "beautiful_section_divider",
        "positive": True, "expect_block": None, "strict": True,
        "build": lambda b: b.add_slide("Section", archetype="section",
            elements=[b.title("Chapter 2"), b.text("What comes next")]),
    },
    {
        "id": "beautiful_quote",
        "positive": True, "expect_block": None, "strict": True,
        "build": lambda b: b.add_slide("Quote", archetype="quote",
            elements=[b.title("A memorable line"), b.subtitle("— author")]),
    },
    {
        "id": "beautiful_conclusion",
        "positive": True, "expect_block": None, "strict": True,
        "build": lambda b: b.add_slide("Close", archetype="conclusion",
            elements=[b.title("Thank you"), b.text("Questions?")]),
    },
    {
        "id": "beautiful_timeline",
        "positive": True, "expect_block": None, "strict": True,
        "build": lambda b: b.add_slide("Roadmap", archetype="timeline",
            elements=[b.title("Milestones"), b.box("Phase 1", recipe="card")]),
    },
    {
        "id": "beautiful_blank_single_accent",
        "positive": True, "expect_block": None, "strict": True,
        "build": lambda b: b.add_slide("Accent", archetype="blank",
            elements=[b.title("One message"), b.box("Supporting card", recipe="kpi")]),
    },

    # ── Ugly (negative) — each blocked by at least one harmony rule ──
    {
        "id": "ugly_color_ratio_complementary_1to1",
        "positive": False, "expect_block": "color_ratio", "strict": False,
        "build": lambda b: b.add_slide("T", archetype="two_column",
            elements=[b.box("A", fill_color=_fill((0, 229, 255)), region="left"),
                      b.box("B", fill_color=_fill((255, 109, 0)), region="right")]),
    },
    {
        "id": "ugly_color_ratio_three_even",
        "positive": False, "expect_block": "color_ratio", "strict": False,
        "build": lambda b: b.add_slide("T", archetype="blank",
            elements=[b.box("a", fill_color=_fill((255, 0, 0)), region="main"),
                      b.box("b", fill_color=_fill((0, 255, 0)), region="main"),
                      b.box("c", fill_color=_fill((0, 0, 255)), region="main")]),
    },
    {
        "id": "ugly_color_ratio_no_dominant",
        "positive": False, "expect_block": "color_ratio", "strict": False,
        "build": lambda b: b.add_slide("T", archetype="two_column",
            elements=[b.box("A", fill_color=_fill((255, 0, 0)), region="left"),
                      b.box("B", fill_color=_fill((0, 0, 255)), region="right")]),
    },
    {
        "id": "ugly_focal_ambiguous_two_titles",
        "positive": False, "expect_block": "focal_point", "strict": False,
        "build": lambda b: b.add_slide("T", archetype="blank",
            elements=[b.title("Title A"), b.title("Title B")]),
    },
    {
        "id": "ugly_focal_ambiguous_equal_bullets",
        "positive": False, "expect_block": "focal_point", "strict": False,
        "build": lambda b: b.add_slide("T", archetype="blank",
            elements=[b.text("one"), b.text("two"), b.text("three")]),
    },
    {
        "id": "ugly_hue_clash_red_magenta",
        "positive": False, "expect_block": "hue_harmony", "strict": False,
        "build": lambda b: b.add_slide("T", archetype="blank",
            elements=[b.box("r", fill_color=_fill((255, 0, 0)), region="main"),
                      b.box("m", fill_color=_fill((255, 0, 255)), region="main")]),
    },
    {
        "id": "ugly_hue_clash_green_cyan",
        "positive": False, "expect_block": "hue_harmony", "strict": False,
        "build": lambda b: b.add_slide("T", archetype="blank",
            elements=[b.box("g", fill_color=_fill((0, 255, 0)), region="main"),
                      b.box("c", fill_color=_fill((0, 229, 255)), region="main")]),
    },
    {
        "id": "ugly_chroma_three_primaries",
        "positive": False, "expect_block": "chroma_families", "strict": False,
        "build": lambda b: b.add_slide("T", archetype="blank",
            elements=[b.box("r", fill_color=_fill((255, 0, 0)), region="main"),
                      b.box("g", fill_color=_fill((0, 255, 0)), region="main"),
                      b.box("b", fill_color=_fill((0, 0, 255)), region="main")]),
    },
    {
        "id": "ugly_chroma_three_saturated_accents",
        "positive": False, "expect_block": "chroma_families", "strict": False,
        "build": lambda b: b.add_slide("T", archetype="blank",
            elements=[b.box("r", fill_color=_fill((255, 60, 0)), region="main"),
                      b.box("g", fill_color=_fill((0, 200, 100)), region="main"),
                      b.box("y", fill_color=_fill((255, 200, 0)), region="main")]),
    },
    {
        "id": "ugly_color_ratio_hue_clash_combo",
        "positive": False, "expect_block": "color_ratio", "strict": False,
        "build": lambda b: b.add_slide("T", archetype="blank",
            elements=[b.box("a", fill_color=_fill((255, 0, 0)), region="main"),
                      b.box("b", fill_color=_fill((255, 0, 255)), region="main"),
                      b.box("c", fill_color=_fill((255, 255, 0)), region="main")]),
    },
]
