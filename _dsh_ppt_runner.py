"""DSH ppt-engine runner — stdin JSON → ppt_reflex engine → stdout JSON.

Request shape:
  {"action":"catalog"}
  {"action":"build","template":"academic","style":"academic_rigorous",
   "page_w":960,"page_h":540,"output":"D:/out.pptx",
   "slides":[{"title":"...","archetype":"content","regions":[["r1",60,100,840,360]],
              "elements":[{"id":"t1","type":"title","text":"..."},
                          {"id":"b1","type":"box","text":"...","fill_color":[27,58,92],
                           "shape_id":"rounded_rectangle"},
                          {"id":"img1","type":"image","image_path":"D:/a.png",
                           "layout_mode":"hero_right"}],
              "arrows":[{"from":"t1","to":"b1","text":"flow"}]}]}
"""
import sys, json, io, os, traceback, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
try:
    sys.stdin.reconfigure(encoding="utf-8")
except Exception:
    pass
sys.path.insert(0, r"D:\ppt")
# Raw stdout buffer captured ONCE — survives redirect_stdout contexts, so
# streaming frames always reach the consumer even while engine prints are
# being diverted to stderr.
_RAW_OUT = sys.stdout.buffer
_FRAMES_OUT = None  # optional frames bridge file (panel preview)


def _color(c):
    if isinstance(c, list) and len(c) == 3:
        return tuple(int(v) for v in c)
    return None


def _element(b, e):
    t = e.get("type", "text")
    text = e.get("text", "") or ""
    region = e.get("region", "main")
    if t == "title":
        return b.title(text, region=region)
    if t == "subtitle":
        return b.subtitle(text, region=region)
    if t == "text":
        return b.text(text, style=e.get("style", "Body"), region=region)
    if t == "bullet":
        return b.bullet(text, region=region)
    if t == "footer":
        return b.footer(text)
    if t == "box":
        return b.box(text, style=e.get("style", "Body"), region=region,
                     fill_color=_color(e.get("fill_color")),
                     shape_id=e.get("shape_id", "rounded_rectangle"),
                     ph=e.get("ph"), align_h=e.get("align_h", "left"),
                     recipe=e.get("recipe"))
    if t == "shape":
        return b.shape(e.get("shape_id", "star"), region=region,
                       fill_color=_color(e.get("fill_color")),
                       pw=e.get("pw"), ph=e.get("ph"), text=text)
    if t == "image":
        return b.image(e.get("image_path", ""), region=region, pw=e.get("pw"),
                       ph=e.get("ph"), fit_mode=e.get("fit_mode", "fit"),
                       layout_mode=e.get("layout_mode", ""), caption=e.get("caption", ""))
    if t == "table":
        return b.table(e.get("headers", []), e.get("rows", []), region=region,
                       font_size=e.get("font_size", 12.0),
                       header_bg=_color(e.get("header_bg")))
    if t == "divider":
        return b.divider(region=region, color=_color(e.get("color")))
    raise ValueError(f"unknown element type: {t}")


# ── T9: region-scoped inspection protocol (read-only, no render, no write) ──
# Dialogue layer contract for the agent (quote in the prompt):
#   When the panel writes area/question feedback to _feedback_auto.json, the agent
#   first runs  `python _dsh_ppt_runner.py --inspect <deck> <slide> [elem_id ...]`
#   to cross the fuzzy word with region evidence BEFORE generating options:
#     "挤" (cramped)  → read region.local_density / gap_sequence_std_pt
#     "乱" (messy)    → read region.font_size_levels / alignment_residual_pt / focal_point
#     "丑" (ugly)     → read region.local_color_ratio / pairwise_contrast / hue_harmony
#   Option verbs MUST reuse declare_direction()'s 17 directions (increase_box_height,
#   reduce_text, switch_style, …) — never invent new words. After the user accepts a
#   fix, tag the (inspect output + accepted solution) pair with "region" and feed it
#   to tools/golden_harvest.py.
def _run_inspect(argv: list) -> None:
    """python _dsh_ppt_runner.py --inspect <deck.json> <slide_idx> [elem_id ...]"""
    import contextlib
    try:
        i = argv.index("--inspect")
        deck_path = argv[i + 1]
        slide_idx = int(argv[i + 2])
        elem_ids = argv[i + 3:] or None
    except (ValueError, IndexError):
        print(json.dumps({"ok": False, "runner_error":
                          "usage: --inspect <deck.json> <slide_idx> [elem_id ...]"}, ensure_ascii=False))
        return

    try:
        with open(deck_path, "r", encoding="utf-8") as f:
            req = json.load(f)
        from ppt_reflex.builder import PPTBuilder
        b = PPTBuilder(template=req.get("template", "academic"),
                       style=req.get("style"),
                       overrides=req.get("overrides"),
                       page_w=req.get("page_w", 960), page_h=req.get("page_h", 540),
                       strict_tokens=req.get("strict_tokens", True))
        with contextlib.redirect_stdout(sys.stderr):
            for s in req.get("slides", []):
                by_id = {}
                elements = []
                for e in s.get("elements", []):
                    spec = _element(b, e)
                    elements.append(spec)
                    if e.get("id"):
                        by_id[e["id"]] = spec
                arrows = []
                for a in s.get("arrows", []):
                    frm, to = a.get("from"), a.get("to")
                    if frm in by_id and to in by_id:
                        arrows.append(b.arrow(by_id[frm], by_id[to], text=a.get("text", "")))
                b.add_slide(s.get("title", ""), archetype=s.get("archetype"),
                            params=s.get("params"), regions=s.get("regions"),
                            elements=elements, arrows=arrows,
                            frame=s.get("frame", ""), rail=s.get("rail", ""),
                            corner_mark=s.get("corner_mark", ""))
        result = b.inspect_slide(slide_idx, elem_ids)
        print(json.dumps(result, ensure_ascii=False, default=str))
    except Exception:
        print(json.dumps({"ok": False, "runner_error": traceback.format_exc(limit=5)},
                         ensure_ascii=False))


def _safe_render_dir(req):
    """Resolve a render output directory that stays inside the engine workspace."""
    base = os.path.realpath(req.get("cwd") or r"D:\ppt")
    requested = req.get("render_dir") or ""
    if requested and not os.path.isabs(requested):
        requested = os.path.join(base, requested)
    if not requested:
        requested = os.path.join(base, "_render_vision")
    try:
        target = os.path.realpath(requested)
        if os.path.commonpath([base, target]) != base:
            return os.path.join(base, "_render_vision")
        return target
    except Exception:
        return os.path.join(base, "_render_vision")



def _render_pngs(b, render_dir):
    """Render each solved slide to PNG for vision-capable models/plugins."""
    import os
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return []
    os.makedirs(render_dir, exist_ok=True)
    from ppt_reflex.grid import GridCanvas, GridConfig, execute_phase1
    paths = []
    for i, spec in enumerate(b._slides):
        try:
            plan = b._plan(spec)
            c = GridCanvas(GridConfig())
            c.checkpoint()
            execute_phase1(plan, c)
            img = Image.new("RGB", (960, 540), "white")
            d = ImageDraw.Draw(img)
            for reg in plan.regions:
                d.rectangle([reg.x, reg.y, reg.x + reg.w, reg.y + reg.h],
                            outline="#94a3b8", width=1)
            for pe in plan.elements:
                p = pe.payload
                x, y, w, h = pe.x, pe.y, pe.w, pe.h
                if p is not None and getattr(p, "fill_color", None):
                    d.rectangle([x, y, x + w, y + h],
                                fill=tuple(int(v) for v in p.fill_color))
                elif p is not None and getattr(p, "shape_id", ""):
                    d.rectangle([x, y, x + w, y + h], outline="#334155", width=1)
                if p is not None and getattr(p, "text", ""):
                    text = str(p.text)
                    font = None
                    try:
                        font = ImageFont.truetype("msyh.ttc",
                                                  max(10, int(getattr(p, "font_size", 14) or 14)))
                    except Exception:
                        font = ImageFont.load_default()
                    color = tuple(int(v) for v in p.font_color) if getattr(p, "font_color", None) else (15, 23, 42)
                    d.multiline_text((x + 6, y + 6), text, fill=color, font=font)
            path = os.path.join(render_dir, "slide_%02d.png" % i)
            img.save(path)
            paths.append({"slide": i, "path": path, "width": 960, "height": 540})
        except Exception:
            continue
    return paths



def main() -> None:
    if "--inspect" in sys.argv:
        _run_inspect(sys.argv)
        return
    try:
        req = json.load(sys.stdin)
    except Exception as ex:
        print(json.dumps({"ok": False, "runner_error": f"bad stdin JSON: {ex}"}, ensure_ascii=False))
        return

    action = req.get("action", "build")
    global _CUR_FRAMES_OUT
    _CUR_FRAMES_OUT = req.get("frames_out")
    if _CUR_FRAMES_OUT:
        try:
            open(_CUR_FRAMES_OUT, "w", encoding="utf-8").close()  # fresh frame file per build
        except Exception:
            pass
    try:
        if action == "catalog":
            from ppt_reflex.grid.templates import list_templates
            from ppt_reflex.builder import load_style_presets, list_archetypes
            presets = load_style_presets()
            styles = []
            for pid, p in presets.get("presets", {}).items():
                c = p.get("color_override", {})
                styles.append({
                    "id": pid, "display_name": p["display_name"], "mood": p["mood"],
                    "theme": p["theme"],
                    "accent": c.get("accent", ""), "bg": c.get("bg", ""),
                })
            print(json.dumps({"ok": True,
                              "templates": list_templates(),
                              "styles": styles,
                              "archetypes": list_archetypes()}, ensure_ascii=False))
            return

        from ppt_reflex.builder import PPTBuilder
        b = PPTBuilder(template=req.get("template", "academic"),
                       style=req.get("style"),
                       overrides=req.get("overrides"),
                       page_w=req.get("page_w", 960), page_h=req.get("page_h", 540),
                       strict_tokens=req.get("strict_tokens", True))
        # Engine prints (warnings) go to stderr — stdout carries ONLY the result JSON.
        with contextlib.redirect_stdout(sys.stderr):
            for s in req.get("slides", []):
                regions = s.get("regions")
                by_id = {}
                elements = []
                for e in s.get("elements", []):
                    spec = _element(b, e)
                    elements.append(spec)
                    if e.get("id"):
                        by_id[e["id"]] = spec
                arrows = []
                for a in s.get("arrows", []):
                    frm, to = a.get("from"), a.get("to")
                    if frm in by_id and to in by_id:
                        arrows.append(b.arrow(by_id[frm], by_id[to], text=a.get("text", "")))
                b.add_slide(s.get("title", ""), archetype=s.get("archetype"),
                            params=s.get("params"),
                            regions=regions, elements=elements, arrows=arrows,
                            frame=s.get("frame", ""), rail=s.get("rail", ""),
                            corner_mark=s.get("corner_mark", ""))
            live_url = req.get("live")
            if live_url:
                _push_preview(b, live_url)
            if req.get("stream"):
                _build_streaming(b, req.get("output"),
                                 _safe_render_dir(req) if req.get("render_png") else None)
                return  # result already emitted as a {"result": ...} JSONL line
            r = b.build(req.get("output"))
        _attach_ascii(b, r)
        if req.get("render_png") or req.get("render_dir"):
            r["rendered_slides"] = _render_pngs(b, _safe_render_dir(req))
        print(json.dumps(r, ensure_ascii=False, default=str))
    except Exception:
        print(json.dumps({"ok": False, "runner_error": traceback.format_exc(limit=5)},
                         ensure_ascii=False))


def _emit_line(obj) -> None:
    """Write one JSONL record to raw stdout and flush — the streaming channel.
    Also appends to the optional frames_out file (panel bridge: the agent builds
    in the conversation; the panel polls the file for its preview)."""
    line = json.dumps(obj, ensure_ascii=False, default=str) + "\n"
    _RAW_OUT.write(line.encode("utf-8"))
    _RAW_OUT.flush()
    if _FRAMES_OUT is not None:
        try:
            with open(_FRAMES_OUT, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass


def _attach_ascii(b, result: dict) -> None:
    """Append per-slide three-tier ASCII feedback (L0 structure / L1 elements /
    L2 numeric text table) to a build result. Signal elements are marked '?' in L1."""
    from ppt_reflex.grid.ascii_map import render_slide_ascii
    from ppt_reflex.grid import GridCanvas, GridConfig, execute_phase1
    from ppt_reflex.grid.composition import global_composition_check

    pages = []
    try:
        for i, spec in enumerate(b._slides):
            plan = b._plan(spec)
            c = GridCanvas(GridConfig())
            c.checkpoint()
            execute_phase1(plan, c)
            ctx = b._composition_context() if hasattr(b, "_composition_context") else None
            diags = global_composition_check(plan, ctx)
            pages.append(render_slide_ascii(plan, c, i, diagnostics=diags))
    except Exception as ex:
        pages.append({"error": str(ex)})
    result["ascii"] = pages


def _build_streaming(b, output: str, render_dir: str | None = None) -> dict:
    """Build one slide at a time, emitting per-element frames to stdout as JSONL
    ({"frame": {...}} lines), then a final {"result": {...}} line. True
    streaming: the consumer paints elements while the build is still running."""
    global _FRAMES_OUT
    from ppt_reflex.builder import set_render_frame_hook
    from pptx import Presentation
    from pptx.util import Pt

    _FRAMES_OUT = _CUR_FRAMES_OUT

    def _hex(c):
        return "#%02X%02X%02X" % tuple(int(v) for v in c) if c else None

    def emit(elem_id, ct, payload, x, y, w, h):
        _emit_line({"frame": {
            "slide": _state["slide"], "kind": ct.name.lower(),
            "elem_id": elem_id, "text": (payload.text if payload else "") or "",
            "x": round(x, 1), "y": round(y, 1), "w": round(w, 1), "h": round(h, 1),
            "fill": _hex(payload.fill_color) if payload else None,
            "font_size": (payload.font_size if payload else None) or 0,
        }})

    _state = {"slide": 0}
    set_render_frame_hook(emit)
    try:
        prs = Presentation()
        prs.slide_width = Pt(b.pw)
        prs.slide_height = Pt(b.ph)
        with contextlib.redirect_stdout(sys.stderr):
            for i in range(len(b._slides)):
                _state["slide"] = i
                _emit_line({"frame": {"clear_slide": True, "slide": i}})
                b.build_single_slide(i, prs=prs)
    finally:
        set_render_frame_hook(None)
    # Second pass off-hook: authoritative build + full diagnostics (frames dedup'd
    # by the consumer because the final result replaces the preview anyway).
    with contextlib.redirect_stdout(sys.stderr):
        r = b.build(output)
    _attach_ascii(b, r)
    if render_dir:
        r["rendered_slides"] = _render_pngs(b, render_dir)
    _emit_line({"result": r})
    return r


def _push_preview(b, live_url: str) -> None:
    """Solve one slide's layout, push per-element frames to the live server, then
    proceed to the real build. Preview coordinates == final PPTX coordinates
    (same deterministic pipeline)."""
    import urllib.request
    from ppt_reflex.grid import GridCanvas, GridConfig, execute_phase1

    def _hex(c):
        if not c:
            return None
        return "#%02X%02X%02X" % tuple(int(v) for v in c)

    for i, spec in enumerate(b._slides):
        plan = b._plan(spec)
        c = GridCanvas(GridConfig())
        c.checkpoint()
        execute_phase1(plan, c)
        frames = [{"clear_slide": True, "slide": i}]
        for reg in plan.regions:
            frames.append({"slide": i, "kind": "region", "text": reg.region_id,
                           "x": reg.x, "y": reg.y, "w": reg.w, "h": reg.h})
        for pe in plan.elements:
            p = pe.payload
            frames.append({
                "slide": i, "kind": pe.content_type.name.lower(),
                "elem_id": pe.elem_id,
                "text": (p.text if p else "") or "",
                "x": pe.x, "y": pe.y, "w": pe.w, "h": pe.h,
                "fill": _hex(p.fill_color) if p else None,
                "font_size": (p.font_size if p else None) or 0,
            })
        data = json.dumps(frames).encode("utf-8")
        req = urllib.request.Request(live_url.rstrip("/") + "/push",
                                     data=data, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=3)
        except Exception as ex:
            print(f"[runner] live push failed: {ex}", file=sys.stderr)
            return


if __name__ == "__main__":
    main()
