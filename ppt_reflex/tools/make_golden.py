"""`make golden` — run the harmony golden-set and diff against baseline.

Usage:
    python -m ppt_reflex.tools.make_golden
    python ppt_reflex/tools/make_golden.py

Exit code 1 when pass_rate or block_rate drops below baseline (a regression).
"""

from __future__ import annotations

import json
import sys

from ppt_reflex.tests.golden.runner import compare_baseline


def main() -> int:
    report = compare_baseline()
    print(json.dumps({k: v for k, v in report.items() if k != "results"},
                     ensure_ascii=False, indent=2))
    print("\nPer-case:")
    for r in report["results"]:
        status = "PASS" if r["passed"] else "FAIL"
        extra = r.get("error") or ", ".join(r["fired"]) or ("(no harmony rule fired)" if not r["blocked"] else "")
        print(f"  [{status}] {r['id']}  blocked={r['blocked']}  "
              f"expect={r.get('expect_block')}  fired={extra}")

    failed = [r for r in report["results"] if not r["passed"]]
    if report["regression"]:
        print("\nREGRESSION: pass/block rate dropped below baseline.")
        return 1
    if failed:
        print(f"\n{len(failed)} case(s) failed.")
        return 1
    print("\nOK: golden-set green, no regression.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
