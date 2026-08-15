"""ppt_reflex live.py — real-time build preview.

Standalone: `python live.py` → http://127.0.0.1:8765
The runner pushes one frame per element during the build; the browser canvas
redraws at the same 960×540 coordinates the PPTX will use. You watch elements
being placed one by one — same data, two render targets (preview + pptx).

Frames (JSON):
  {"clear_slide": true}                                  — next slide begins
  {"seq": n, "slide": i, "elem_id": "...", "kind": "...",
   "text": "...", "x": 60, "y": 110, "w": 400, "h": 180,
   "fill": "#1D4ED8", "font_size": 20}

Endpoints:
  GET  /                      preview page
  GET  /frames?since=N        frames with seq > N (polled by the page)
  POST /push                  accept one frame or a list (runner → server)
  POST /reset                 clear all frames (new build)
"""
from __future__ import annotations
import json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_frames: list[dict] = []
_lock = threading.Lock()
_seq = 0

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>ppt_reflex live</title>
<style>body{margin:0;background:#1e2430;display:flex;flex-direction:column;align-items:center;
font-family:Segoe UI,Microsoft YaHei,sans-serif;color:#cbd5e1;padding:12px}
#bar{width:960px;margin:4px 0;font-size:13px;display:flex;justify-content:space-between}
canvas{background:#fff;border-radius:4px;box-shadow:0 8px 24px rgba(0,0,0,.4)}</style></head>
<body><div id="bar"><span id="status">waiting…</span><span id="count"></span></div>
<canvas id="cv" width="960" height="540"></canvas>
<script>
const cv=document.getElementById('cv'),ctx=cv.getContext('2d');
const st=document.getElementById('status'),cnt=document.getElementById('count');
let since=0,alpha=new Map(),start=performance.now(),interval=setInterval(poll,200);
function draw(){
  ctx.clearRect(0,0,960,540);
  const t=performance.now();
  for(const [k,f] of frames){
    const a=alpha.get(k)||0;
    ctx.save();ctx.globalAlpha=Math.min(1,a);
    if(f.kind==='region'){
      ctx.setLineDash([4,4]);ctx.strokeStyle='#94a3b8';ctx.lineWidth=1;
      ctx.strokeRect(f.x,f.y,f.w,f.h);ctx.setLineDash([]);
      ctx.fillStyle='rgba(148,163,184,0.06)';ctx.fillRect(f.x,f.y,f.w,f.h);
    }else{
      if(f.fill){ctx.fillStyle=f.fill;roundRect(ctx,f.x,f.y,f.w,f.h,8);ctx.fill();}
      if(f.text){ctx.fillStyle=f.fill&&isDark(f.fill)?'#ffffff':'#0f172a';
        ctx.font=(f.font_size||16)+'px Segoe UI,Microsoft YaHei';
        ctx.textBaseline='top';
        const lines=String(f.text).split('\\n').slice(0,6);
        lines.forEach((ln,i)=>{ctx.fillText(ln.slice(0,40),f.x+8,f.y+8+i*((f.font_size||16)+4),f.w-16);});}
    }
    ctx.restore();
  }
}
function roundRect(c,x,y,w,h,r){r=Math.min(r,w/2,h/2);c.beginPath();
 c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+h,r);c.arcTo(x+w,y+h,x,y+h,r);
 c.arcTo(x,y+h,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath();}
function isDark(hex){const n=parseInt(hex.slice(1),16);
 const l=(0.2126*((n>>16)&255)+0.7152*((n>>8)&255)+0.0722*(n&255))/255;return l<0.45;}
const frames=new Map();
async function poll(){
  try{
    const r=await fetch('/frames?since='+since);const d=await r.json();
    for(const f of d.frames){
      if(f.clear_slide){frames.clear();alpha.clear();start=performance.now();
        st.textContent='slide '+(f.slide+1);continue;}
      since=Math.max(since,f.seq+1);frames.set(f.seq,f);
      const k=f.seq;(function(k){setTimeout(()=>alpha.set(k,1),80);})(k);
    }
    cnt.textContent=frames.size+' elements';
    if(alpha.size)draw();
  }catch(e){}
}
requestAnimationFrame(function loop(){draw();requestAnimationFrame(loop);});
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        global _seq
        if self.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/frames"):
            import urllib.parse as up
            q = up.parse_qs(up.urlparse(self.path).query)
            since = int(q.get("since", [0])[0])
            with _lock:
                out = [f for f in _frames if f["seq"] > since]
            self._json(200, {"frames": out})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        global _seq
        if self.path == "/reset":
            with _lock:
                _frames.clear(); _seq = 0
            self._json(200, {"ok": True})
            return
        if self.path == "/push":
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n).decode("utf-8"))
            items = data if isinstance(data, list) else [data]
            with _lock:
                for it in items:
                    _seq += 1
                    it["seq"] = _seq
                    _frames.append(it)
            self._json(200, {"ok": True, "seq": _seq})
            return
        self._json(404, {"error": "not found"})

    def log_message(self, *a):
        pass


def serve(port: int = 8765) -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"[live] preview at http://127.0.0.1:{port}")
    srv.serve_forever()


if __name__ == "__main__":
    serve()
