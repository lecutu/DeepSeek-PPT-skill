"""T6: golden-set regression — beautiful decks 100% pass, ugly decks 100% blocked,
and pass/block rates never drop below baseline."""
import json
import os
import tempfile

from ppt_reflex.tests.golden.runner import compare_baseline
from ppt_reflex.tools import golden_harvest


def test_golden_set_no_regression():
    report = compare_baseline()
    assert report["pass_rate"] == 1.0, f"beautiful decks must all pass: {report}"
    assert report["block_rate"] == 1.0, f"ugly decks must all be blocked: {report}"
    assert report["regression"] is False


def test_golden_harvest_classifies():
    assert golden_harvest.classify_verdict("ugly") == "negative"
    assert golden_harvest.classify_verdict("丑") == "negative"
    assert golden_harvest.classify_verdict("accepted") == "positive"
    assert golden_harvest.classify_verdict("验收通过") == "positive"
    assert golden_harvest.classify_verdict("???") is None


def test_golden_harvest_writes_cases():
    fb = os.path.join(tempfile.gettempdir(), "fb_test.json")
    out = os.path.join(tempfile.gettempdir(), "harvested_test.json")
    with open(fb, "w", encoding="utf-8") as f:
        json.dump([
            {"verdict": "ugly", "expect_block": "color_ratio",
             "deck": {"template": "academic", "slides": [
                 {"title": "T", "archetype": "blank",
                  "elements": [{"id": "a", "type": "box", "text": "A",
                                "fill_color": [255, 0, 0]}]}]}},
            {"verdict": "accepted",
             "deck": {"template": "academic", "slides": [
                 {"title": "T", "archetype": "content",
                  "elements": [{"id": "t", "type": "title", "text": "Hi"}]}]}},
        ], f)
    summary = golden_harvest.harvest(fb, out)
    assert summary["positive"] == 1
    assert summary["negative"] == 1
    with open(out, "r", encoding="utf-8") as f:
        cases = json.load(f)
    assert len(cases) == 2
    assert cases[0]["positive"] is False and cases[0]["expect_block"] == "color_ratio"
    assert cases[1]["positive"] is True


if __name__ == "__main__":
    test_golden_set_no_regression()
    test_golden_harvest_classifies()
    test_golden_harvest_writes_cases()
    print("\n✓ All golden tests PASSED")
