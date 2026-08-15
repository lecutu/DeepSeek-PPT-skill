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
import sys, json, io, traceback, contextlib

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


def main() -> None:
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
                       page_w=req.get("page_w", 960), page_h=req.get("page_h", 540))
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
                _build_streaming(b, req.get("output"))
                return  # result already emitted as a {"result": ...} JSONL line
            r = b.build(req.get("output"))
        _attach_ascii(b, r)
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
    L2 numeric text table) to a build result."""
    from ppt_reflex.grid.ascii_map import render_slide_ascii
    from ppt_reflex.grid import GridCanvas, GridConfig, execute_phase1

    pages = []
    try:
        for i, spec in enumerate(b._slides):
            plan = b._plan(spec)
            c = GridCanvas(GridConfig())
            c.checkpoint()
            execute_phase1(plan, c)
            pages.append(render_slide_ascii(plan, c, i))
    except Exception as ex:
        pages.append({"error": str(ex)})
    result["ascii"] = pages


def _build_streaming(b, output: str) -> dict:
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
