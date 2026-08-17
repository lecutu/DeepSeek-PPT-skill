"""Temporary PPT artifact cleanup — the temp-deletion channel.

Deletes ONLY untracked build outputs, never git-tracked files and never the
workflow state bridge files (_deck_auto.json / _palette_auto.json /
_selection_auto.json / _feedback_auto.json / _frames_auto.jsonl /
_breaker_state.json are all KEPT — the panel and the watcher need them).

What gets removed:
  - every *.pptx NOT tracked by git (any depth, incl. output/), e.g.
    ppt_reflex_demo.pptx, whitecollar_v2_*.pptx, _smoke.pptx, glam_royal.pptx
  - stale render diagnostics: _stream_out.jsonl, _stream_err.txt,
    _ascii_out.json, _git_report.txt

What is KEPT (live preview data):
  - _render_vision/  — PNG previews rendered by the watcher; the PNG-based
    preview panel reads them. Deleting them blanks the panel.

Usage:
  python cleanup_tmp.py            # actually delete
  python cleanup_tmp.py --dry-run  # list what would be deleted, touch nothing
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {".git", "node_modules", "__pycache__", "ppt_reflex", ".dsh"}


def git_tracked() -> set:
    """Absolute normalized paths of every git-tracked file."""
    try:
        out = subprocess.check_output(
            ["git", "-C", ROOT, "ls-files"], text=True, errors="replace"
        )
        return {os.path.normpath(os.path.join(ROOT, p)) for p in out.splitlines() if p}
    except Exception:
        return set()


def walk(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def main() -> int:
    dry = "--dry-run" in sys.argv
    tracked = git_tracked()
    targets = []

    # 1) untracked .pptx anywhere under ROOT
    for p in walk(ROOT):
        if p.lower().endswith(".pptx") and os.path.normpath(p) not in tracked:
            targets.append(p)

    # 2) stale render diagnostics (NOT _render_vision — that is live preview
    #    data for the PNG-based panel; deleting it blanks the preview)
    for fn in ("_stream_out.jsonl", "_stream_err.txt", "_ascii_out.json", "_git_report.txt"):
        p = os.path.join(ROOT, fn)
        if os.path.isfile(p):
            targets.append(p)

    targets = sorted(set(targets))
    if not targets:
        print("nothing to clean")
        return 0

    print(f"{'would delete' if dry else 'deleting'} {len(targets)} item(s):")
    for t in targets:
        print("  " + os.path.relpath(t, ROOT))

    if dry:
        print("\n[dry-run] no files touched")
        return 0

    for t in targets:
        if t.endswith(os.sep):
            try:
                os.rmdir(t.rstrip(os.sep))
            except OSError:
                pass  # non-empty — files already removed individually
        else:
            try:
                os.remove(t)
            except OSError as e:
                print("  !! skip:", t, e)
    print("\ndone")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
