// dsh-slide-reflex — Client half: per-page live preview panel with
// click/box-select feedback, recolor requests, palette picker, i18n.
// Wrapped for the dsh ClientModuleLoader — every client bundle must register
// via window.__ModuleLoader__.load({ id, factory }).
window.__ModuleLoader__.load({
  id: "dsh-slide-reflex",
  factory: (require) => {
    var module = { exports: {} };
    var exports = module.exports;
    const React = require("react");
    const z = { any: () => ({ parse: (v) => v, _zod: { def: { shape: {} } }, safeParse: (v) => ({ success: true, data: v }) }) };

const PACKAGE = 'dsh-slide-reflex'
const SERVICE = 'slideReflex'
const anySchema = z.any()
const oneArg = () => [{ name: 'request', wire: 'request', source: 'json', codec: { mode: 'strict', typeSymbol: 'json', schema: anySchema } }]
const result = () => ({ mode: 'strict', typeSymbol: 'json', schema: anySchema })
const loc = { file: 'lib/index.js', line: 1, column: 1 }
const METHODS_WITH_ARG = ['build', 'framesFile', 'applyFeedbackBuild', 'savePalette', 'saveFeedback', 'saveSelection']
const METHODS_NO_ARG = ['loadPalette', 'loadDeck']

const TYPERT_REMOTE = {
  package: PACKAGE,
  descriptors: [
    ...METHODS_WITH_ARG.map((m) => ({
      id: `${PACKAGE}#${SERVICE}/${m}`, service: SERVICE, namespace: SERVICE, method: m,
      invocation: { kind: 'direct' }, parameters: oneArg(), result: result(), sourceLocation: loc,
    })),
    ...METHODS_NO_ARG.map((m) => ({
      id: `${PACKAGE}#${SERVICE}/${m}`, service: SERVICE, namespace: SERVICE, method: m,
      invocation: { kind: 'direct' }, parameters: [], result: result(), sourceLocation: loc,
    })),
  ],
}

const I18N = {
  zh: {
    entry: 'PPT 预览', btnOpen: '▸ PPT 预览', title: 'PPT 预览', foot: 'PPT',
    waitBuild: '等待构建（在对话里说需求，助手自动生成）',
    building: '构建中… ', elems: ' 个元素',
    done: '完成 ✓ ', fail: '失败 ✗', loaded: '已加载 ', page: '第 ', pageOf: ' / ', pageUnit: ' 页',
    selPrefix: ' · 已选 ', rebuild: '重建',
    hint: '点选元素 / 拖拽框选区域，然后改色或提问题',
    feedbackTitle: '反馈请求', recolor: '改色', addRecolor: '+ 改色',
    question: '问题', qPlaceholder: '如：这个太大了 / 这块太挤 / 换两列', addQuestion: '+ 提问题',
    applyRebuild: '应用并重建', paletteAdvanced: '配色 & 高级', paletteTitle: '配色', advancedTitle: '高级',
    accent: '主色', background: '背景', clear: '清除', quick: '快捷', custom: '+ 自定义',
    loadDeck: '载入助手 deck', deckPlaceholder: 'deck JSON（正常不用碰——助手在对话里生成）',
    selectedElem: '已选中：', canEdit: '（可改色或提问题）',
    boxSelected: '已框选区域（', boxSelected2: ' 个元素）——可提问题',
    colorAdded: '已添加改色：', rebuildStarted: '重建已发起', applyRecolor: '应用改色并重建…',
    noColorReq: '没有改色请求（问题类由助手在对话里处理）',
    questionNoted: '问题已记录——在对话里说「处理我的反馈」，助手会改',
    needSelect: '先点一个元素或框选一片区域', needElem: '先点一个元素',
    questionEmpty: '问题不能为空', applyFailed: '失败: ', error: '出错: ', rebuildInit: '重建中…',
    pageArea: '区域(', pageArea2: '元素)：',
    colorPage: '第', colorPage2: '页 · ', questionPage: '❓ 第', questionPage2: '页 · ', areaPage: '▭ 第',
    rebuildDone: '构建请求已发', jsonInvalid: 'JSON 无效',
  },
  en: {
    entry: 'PPT Preview', btnOpen: '▸ PPT Preview', title: 'PPT Preview', foot: 'PPT',
    waitBuild: 'Waiting for build (state your need in chat, agent auto-generates)',
    building: 'Building… ', elems: ' elements',
    done: 'Done ✓ ', fail: 'Failed ✗', loaded: 'Loaded ', page: 'Page ', pageOf: ' / ', pageUnit: '',
    selPrefix: ' · selected ', rebuild: 'Rebuild',
    hint: 'Click element / drag to box-select, then recolor or ask',
    feedbackTitle: 'Feedback requests', recolor: 'Recolor', addRecolor: '+ Recolor',
    question: 'Question', qPlaceholder: 'e.g. too big / too crowded / two columns', addQuestion: '+ Ask',
    applyRebuild: 'Apply & Rebuild', paletteAdvanced: 'Palette & Advanced', paletteTitle: 'Palette', advancedTitle: 'Advanced',
    accent: 'Accent', background: 'Background', clear: 'Clear', quick: 'Quick', custom: '+ Custom',
    loadDeck: 'Load agent deck', deckPlaceholder: 'deck JSON (normally untouched — agent generates it in chat)',
    selectedElem: 'Selected: ', canEdit: ' (recolor or ask)',
    boxSelected: 'Box-selected ', boxSelected2: ' elements — can ask',
    colorAdded: 'Recolor added: ', rebuildStarted: 'Rebuild started', applyRecolor: 'Applying recolor & rebuilding…',
    noColorReq: 'No recolor requests (questions are handled by the agent in chat)',
    questionNoted: 'Question noted — say "process my feedback" in chat',
    needSelect: 'Click an element or box-select an area first', needElem: 'Click an element first',
    questionEmpty: 'Question cannot be empty', applyFailed: 'Failed: ', error: 'Error: ', rebuildInit: 'Rebuilding…',
    pageArea: 'area (', pageArea2: ' elements): ',
    colorPage: 'Page ', colorPage2: ' · ', questionPage: '❓ Page ', questionPage2: ' · ', areaPage: '▭ Page ',
    rebuildDone: 'Build requested', jsonInvalid: 'Invalid JSON',
  },
}

// Renders one slide's frames into a 2d context. Coordinates are in the native
// 960×540 space, scaled by W/960 so the same logic serves the full preview and
// the 44×25 thumbnails. Rendering steps are identical to the original draw().
function paint(g, page, selElemId, dragRect, W, H) {
  const s = W / 960
  g.clearRect(0, 0, W, H)
  for (const f of page.values()) {
    if (f.kind === 'region') {
      g.setLineDash([4, 4]); g.strokeStyle = '#94a3b8'; g.lineWidth = 1
      g.strokeRect(f.x * s, f.y * s, f.w * s, f.h * s); g.setLineDash([])
      g.fillStyle = 'rgba(148,163,184,0.06)'; g.fillRect(f.x * s, f.y * s, f.w * s, f.h * s)
      continue
    }
    if (f.fill) {
      g.fillStyle = f.fill
      const r = Math.min(8, f.w / 2, f.h / 2) * s
      g.beginPath(); g.moveTo(f.x * s + r, f.y * s)
      g.arcTo(f.x * s + f.w * s, f.y * s, f.x * s + f.w * s, f.y * s + f.h * s, r)
      g.arcTo(f.x * s + f.w * s, f.y * s + f.h * s, f.x * s, f.y * s + f.h * s, r)
      g.arcTo(f.x * s, f.y * s + f.h * s, f.x * s, f.y * s, r)
      g.arcTo(f.x * s, f.y * s, f.x * s + f.w * s, f.y * s, r)
      g.closePath(); g.fill()
    }
    if (f.text) {
      g.fillStyle = f.fill && parseInt(f.fill.slice(1), 16) < 0x888888 ? '#ffffff' : '#0f172a'
      g.font = ((f.font_size || 16) * s) + 'px Segoe UI, Microsoft YaHei, sans-serif'
      g.textBaseline = 'top'
      String(f.text).split('\n').slice(0, 6).forEach((ln, i) => {
        g.fillText(ln.slice(0, 40), f.x * s + 8 * s, f.y * s + 8 * s + i * ((f.font_size || 16) + 4) * s, (f.w - 16) * s)
      })
    }
    if (selElemId && f.elem_id === selElemId) {
      g.strokeStyle = '#3b82f6'; g.lineWidth = 3
      g.strokeRect(f.x * s - 2, f.y * s - 2, f.w * s + 4, f.h * s + 4)
    }
  }
  if (dragRect) {
    g.setLineDash([6, 4]); g.strokeStyle = '#3b82f6'; g.lineWidth = 2
    g.strokeRect(dragRect.x * s, dragRect.y * s, dragRect.w * s, dragRect.h * s); g.setLineDash([])
    g.fillStyle = 'rgba(59,130,246,0.12)'; g.fillRect(dragRect.x * s, dragRect.y * s, dragRect.w * s, dragRect.h * s)
  }
}

// Mini thumbnail: repaints a single slide into a 44×25 canvas using the same
// paint() routine (mini-canvas redraw path — no dataURL cache needed).
function Thumb({ slide, active, onClick, framesRef, version }) {
  const ref = React.useRef(null)
  React.useEffect(() => {
    const cv = ref.current
    if (!cv) return
    paint(cv.getContext('2d'), framesRef.current.get(slide) || new Map(), null, null, 44, 25)
  }, [slide, version, framesRef])
  return React.createElement('canvas', {
    ref,
    width: 44,
    height: 25,
    onClick,
    className: 'dsr-thumb',
    style: {
      width: 44, height: 25, flex: '0 0 auto', cursor: 'pointer', display: 'block',
      background: '#fff', borderRadius: 6, boxSizing: 'border-box',
      border: active ? '2px solid #3b82f6' : '1px solid rgba(90,100,130,0.45)',
    },
  })
}

const UI_STYLE_ID = 'dsh-slide-reflex-ui'
const UI_CSS = [
  '@keyframes dsrFadeIn { from { opacity: 0; transform: translateY(8px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }',
  '@keyframes dsrPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.35 } }',
  '.dsr-win { animation: dsrFadeIn 180ms ease; }',
  '.dsr-dot-pulse { animation: dsrPulse 1.1s ease-in-out infinite; }',
  '.dsr-foot { transition: background .15s ease, color .15s ease; }',
  '.dsr-foot:hover { background: rgba(59,130,246,.18) !important; color: #fff !important; }',
  '.dsr-primary { transition: filter .15s ease; }',
  '.dsr-primary:hover { filter: brightness(1.1) !important; }',
  '.dsr-btn2 { transition: background .15s ease, border-color .15s ease; }',
  '.dsr-btn2:hover { background: rgba(90,100,130,.28) !important; border-color: rgba(120,140,180,.55) !important; }',
  '.dsr-sw { transition: transform .12s ease; }',
  '.dsr-sw:hover { transform: scale(1.12); }',
  '.dsr-thumb { transition: border-color .12s ease, box-shadow .12s ease; }',
  '.dsr-thumb:hover { border-color: #3b82f6 !important; }',
  '.dsr-win input:not([type="color"]), .dsr-win textarea { transition: border-color .15s ease; }',
  '.dsr-win input:not([type="color"]):focus, .dsr-win textarea:focus { border-color: #3b82f6 !important; outline: none; }',
].join('\n')
function ensureStyle() {
  if (document.getElementById(UI_STYLE_ID)) return
  const el = document.createElement('style')
  el.id = UI_STYLE_ID
  el.textContent = UI_CSS
  document.head.appendChild(el)
}

    module.exports = {
      inject: ['timer', 'remote'],
      async apply(ctx) {
    const slots = ctx.get('slots')
    if (slots === undefined) return
    ensureStyle()
    const disposeRemote = await ctx.remote.$mount(TYPERT_REMOTE)
    ctx.effect(() => disposeRemote, 'dsh-slide-reflex: remote')
    ctx.effect(() => () => { const el = document.getElementById(UI_STYLE_ID); if (el) el.remove() }, 'dsh-slide-reflex: styles')
    const svc = () => {
      const s = ctx.remote.namespaces?.get(SERVICE)?.service
      if (s === void 0) throw new Error('slideReflex remote namespace is not mounted')
      return s
    }

    function Panel(props) {
      const [open, setOpen] = React.useState(false)
      const [lang, setLang] = React.useState(() => {
        try { return String(navigator.language || '').toLowerCase().startsWith('zh') ? 'zh' : 'en' } catch { return 'zh' }
      })
      const t = I18N[lang] || I18N.zh
      const [status, setStatus] = React.useState(t.waitBuild)
      const [statusKind, setStatusKind] = React.useState('wait')
      const [viewSlide, setViewSlide] = React.useState(0)
      const [totalSlides, setTotalSlides] = React.useState(0)
      const [selElem, setSelElem] = React.useState('')
      const [selArea, setSelArea] = React.useState(null)
      const [reqColor, setReqColor] = React.useState('#C0392B')
      const [question, setQuestion] = React.useState('')
      const [requests, setRequests] = React.useState([])
      const [dragRect, setDragRect] = React.useState(null)
      const [thumbRev, setThumbRev] = React.useState(0)
      const canvasRef = React.useRef(null)
      const framesBySlideRef = React.useRef(new Map())
      const sinceRef = React.useRef(0)
      const dragStartRef = React.useRef(null)
      const winRef = React.useRef(null)
      const winDragRef = React.useRef(null)
      const [pos, setPos] = React.useState(null)
      const [dragging, setDragging] = React.useState(false)
      const [deckText, setDeckText] = React.useState('')
      const [pal, setPal] = React.useState({ accent_hex: '', bg_hex: '', swatches: [] })

      React.useEffect(() => {
        if (!open) return
        svc().loadPalette().then((r) => { if (r && r.palette) setPal({ accent_hex: r.palette.accent_hex || '', bg_hex: r.palette.bg_hex || '', swatches: r.palette.swatches || [] }) }).catch(() => {})
        const draw = () => {
          const cv = canvasRef.current
          if (!cv) return
          paint(cv.getContext('2d'), framesBySlideRef.current.get(viewSlide) || new Map(), selElem, dragRect, 960, 540)
        }
        const iv = ctx.interval(async () => {
          try {
            const r = await svc().framesFile({ since: sinceRef.current })
            if (r && Array.isArray(r.frames)) {
              for (const f of r.frames) {
                sinceRef.current = (f.seq || 0) + 1
                if (f.clear_slide) {
                  if (r.building) setViewSlide(f.slide || 0)
                  continue
                }
                let page = framesBySlideRef.current.get(f.slide)
                if (!page) { page = new Map(); framesBySlideRef.current.set(f.slide, page) }
                page.set(f.seq, f)
              }
              const slides = framesBySlideRef.current.size
              if (slides > 0) setTotalSlides(slides)
              if (r.frames.length > 0) { draw(); setThumbRev((v) => v + 1) }
              if (r.building) { setStatus(t.building + sinceRef.current + t.elems); setStatusKind('building') }
              else if (r.result) { if (r.result.ok) { setStatus(t.done + (r.result.summary || '')); setStatusKind('done') } else { setStatus(t.fail); setStatusKind('fail') } }
              else if (sinceRef.current === 0) { setStatus(t.waitBuild); setStatusKind('wait') }
              else { setStatus(t.loaded + sinceRef.current + t.elems); setStatusKind('loaded') }
            }
          } catch { /* remote not ready */ }
        }, 400)
        return () => { iv() }
      }, [open, viewSlide, selElem, dragRect, lang])

      const goto = (d) => setViewSlide(Math.max(0, Math.min(totalSlides - 1, viewSlide + d)))
      const savePal = (next) => {
        setPal(next)
        svc().savePalette({ palette: next }).catch(() => {})
      }
      const toCanvas = (e) => {
        const cv = canvasRef.current
        const rect = cv.getBoundingClientRect()
        return { x: (e.clientX - rect.left) * (960 / rect.width), y: (e.clientY - rect.top) * (540 / rect.height) }
      }
      const onMouseDown = (e) => { dragStartRef.current = toCanvas(e); setDragRect(null) }
      const onMouseMove = (e) => {
        if (!dragStartRef.current) return
        const p = toCanvas(e)
        const s = dragStartRef.current
        setDragRect({ x: Math.min(s.x, p.x), y: Math.min(s.y, p.y), w: Math.abs(p.x - s.x), h: Math.abs(p.y - s.y) })
      }
      const onMouseUp = (e) => {
        const s = dragStartRef.current
        dragStartRef.current = null
        setDragRect(null)
        if (!s) return
        const p = toCanvas(e)
        const dx = p.x - s.x, dy = p.y - s.y
        if (Math.abs(dx) < 6 && Math.abs(dy) < 6) {
          const page = framesBySlideRef.current.get(viewSlide) || new Map()
          let hit = null
          for (const f of [...page.values()].reverse()) {
            if (f.elem_id && f.x <= p.x && p.x <= f.x + f.w && f.y <= p.y && p.y <= f.y + f.h) { hit = f; break }
          }
          if (hit) {
            setSelElem(hit.elem_id)
            setSelArea(null)
            svc().saveSelection({ elem_id: hit.elem_id, kind: hit.kind, slide: viewSlide, text: hit.text ? String(hit.text).slice(0, 30) : '' }).catch(() => {})
            setStatus(t.selectedElem + hit.elem_id + t.canEdit)
          } else {
            setSelElem(''); setSelArea(null)
          }
          return
        }
        const rect = { x: Math.min(s.x, p.x), y: Math.min(s.y, p.y), w: Math.abs(p.x - s.x), h: Math.abs(p.y - s.y) }
        if (rect.w < 10 && rect.h < 10) return
        const page = framesBySlideRef.current.get(viewSlide) || new Map()
        const elems = [...page.values()].filter((f) => f.elem_id && f.x < rect.x + rect.w && f.x + f.w > rect.x && f.y < rect.y + rect.h && f.y + f.h > rect.y)
        setSelArea({ ...rect, elems: elems.map((f) => f.elem_id) })
        setSelElem('')
        svc().saveSelection({ slide: viewSlide, area: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.w), h: Math.round(rect.h) }, elems: elems.map((f) => f.elem_id) }).catch(() => {})
        setStatus(t.boxSelected + elems.length + t.boxSelected2)
      }
      const addColorRequest = () => {
        if (!selElem) { setStatus(t.needElem); return }
        const page = framesBySlideRef.current.get(viewSlide) || new Map()
        const f = [...page.values()].find((x) => x.elem_id === selElem)
        const label = f && f.text ? String(f.text).slice(0, 14) : selElem
        const next = [...requests, { type: 'color', slide: viewSlide, elem_id: selElem, color_hex: reqColor, label }]
        setRequests(next)
        svc().saveFeedback({ requests: next }).catch(() => {})
        setStatus(t.colorAdded + label + ' → ' + reqColor)
      }
      const addQuestion = () => {
        if (!question.trim()) { setStatus(t.questionEmpty); return }
        let next
        if (selArea) {
          next = [...requests, { type: 'area', slide: viewSlide, area: { x: Math.round(selArea.x), y: Math.round(selArea.y), w: Math.round(selArea.w), h: Math.round(selArea.h) }, elems: selArea.elems, question: question.trim() }]
        } else if (selElem) {
          next = [...requests, { type: 'question', slide: viewSlide, elem_id: selElem, question: question.trim() }]
        } else {
          setStatus(t.needSelect)
          return
        }
        setRequests(next)
        setQuestion('')
        svc().saveFeedback({ requests: next }).catch(() => {})
        setStatus(t.questionNoted)
      }
      const applyAndRebuild = () => {
        const colors = requests.filter((r) => r.type === 'color')
        if (colors.length === 0) { setStatus(t.noColorReq); return }
        setStatus(t.applyRecolor)
        svc().applyFeedbackBuild({ requests }).then((r) => {
          if (r && r.error) setStatus(t.applyFailed + String(r.error).slice(-200))
          else setStatus(t.rebuildStarted)
        }).catch((e) => setStatus(t.error + String(e)))
      }
      const rebuildFromDeck = () => {
        try {
          const d = JSON.parse(deckText)
          framesBySlideRef.current = new Map(); sinceRef.current = 0; setViewSlide(0); setTotalSlides(0)
          setStatus(t.rebuildInit)
          svc().build(Object.assign({ action: 'build' }, d)).then(() => setStatus(t.rebuildDone)).catch((e) => setStatus(t.error + String(e)))
        } catch { setStatus(t.jsonInvalid) }
      }
      const DEFAULT_SWATCHES = ['#1D4ED8', '#0F172A', '#1B3A5C', '#0052D9', '#C0392B', '#0D9488']
      const swatches = pal.swatches && pal.swatches.length ? pal.swatches : DEFAULT_SWATCHES

      const C = { bg: 'rgba(15,17,26,0.97)', section: 'rgba(30,34,48,0.8)', border: '1px solid rgba(90,100,130,0.35)', primary: '#2563eb', sub: '#8b93a7', input: '#0f172a' }
      const inputStyle = { background: C.input, color: '#cbd5e1', border: C.border, borderRadius: 8, padding: '7px 8px', fontSize: 12, fontFamily: 'inherit', boxSizing: 'border-box' }
      const colorInputStyle = { width: 30, height: 30, border: C.border, borderRadius: 8, background: 'transparent', cursor: 'pointer', padding: 0, flex: '0 0 auto' }
      const btnPrimary = { background: 'linear-gradient(135deg,#3b82f6,#2563eb)', color: '#fff', border: 'none', borderRadius: 8, padding: '7px 14px', cursor: 'pointer', fontWeight: 600, fontFamily: 'inherit', fontSize: 12 }
      const btn2 = { background: 'rgba(30,34,48,0.6)', color: '#cbd5e1', border: C.border, borderRadius: 8, padding: '7px 11px', cursor: 'pointer', fontFamily: 'inherit', fontSize: 12 }
      const sectTitle = { fontSize: 11, fontWeight: 700, color: C.sub, textTransform: 'uppercase', letterSpacing: '0.5px' }

      const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v))
      const onWinDown = (e) => {
        if (e.button !== 0) return
        if (e.target && e.target.closest && e.target.closest('button, input, textarea, select, summary, a')) return
        const el = winRef.current
        if (!el) return
        const r = el.getBoundingClientRect()
        winDragRef.current = { sx: e.clientX, sy: e.clientY, lx: r.left, ly: r.top }
        setDragging(true)
        e.preventDefault()
      }
      React.useEffect(() => {
        if (!dragging) return
        const mv = (e) => {
          const d = winDragRef.current
          if (!d) return
          const w = Math.min(560, window.innerWidth - 16)
          const left = clamp(d.lx + e.clientX - d.sx, 8, Math.max(8, window.innerWidth - w - 8))
          const top = clamp(d.ly + e.clientY - d.sy, 8, Math.max(8, window.innerHeight - 60))
          setPos({ left, top })
          e.preventDefault()
        }
        const up = () => setDragging(false)
        document.addEventListener('mousemove', mv)
        document.addEventListener('mouseup', up)
        return () => { document.removeEventListener('mousemove', mv); document.removeEventListener('mouseup', up) }
      }, [dragging])

      const dotColor = { wait: '#64748b', building: '#f59e0b', done: '#22c55e', fail: '#ef4444', loaded: '#3b82f6' }[statusKind] || '#64748b'
      const wide = !!(props && props.wide)
      const footBtn = React.createElement('button', {
        className: 'dsr-foot',
        onClick: () => setOpen(true),
        title: t.title,
        style: { display: 'inline-flex', alignItems: 'center', gap: 6, cursor: 'pointer',
          border: '1px solid rgba(90,100,130,0.35)', background: 'rgba(30,34,48,0.6)', color: '#cbd5e1',
          borderRadius: 8, padding: wide ? '6px 11px' : '6px 9px', fontFamily: 'inherit', fontSize: 12,
          fontWeight: 600, whiteSpace: 'nowrap', userSelect: 'none' },
      },
        React.createElement('span', { style: { fontSize: 13, lineHeight: 1 } }, '▦'),
        wide ? React.createElement('span', null, t.foot) : null,
      )
      if (!open) return footBtn
      const winEl = React.createElement('div', {
        ref: winRef,
        className: 'dsr-win',
        style: { position: 'fixed', zIndex: 10000,
          left: pos ? pos.left + 'px' : 'calc(50vw - 120px)',
          top: pos ? pos.top + 'px' : '12vh',
          width: 560, maxWidth: 'calc(100vw - 16px)', maxHeight: '82vh',
          display: 'flex', flexDirection: 'column', background: 'rgba(13,15,23,0.98)', color: '#e2e8f0',
          border: '1px solid rgba(120,130,160,0.4)', borderRadius: 14, boxShadow: '0 24px 64px rgba(0,0,0,0.65)',
          overflow: 'hidden', fontFamily: 'inherit', fontSize: 13,
          userSelect: dragging ? 'none' : 'auto', backdropFilter: 'blur(14px)', WebkitBackdropFilter: 'blur(14px)' },
      },
        React.createElement('div', {
          onMouseDown: onWinDown,
          style: { display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px',
            borderBottom: '1px solid rgba(120,130,160,0.2)', background: 'rgba(15,17,26,0.6)',
            flex: '0 0 auto', cursor: dragging ? 'grabbing' : 'grab', userSelect: 'none' },
        },
          React.createElement('span', { className: statusKind === 'building' ? 'dsr-dot-pulse' : undefined,
            style: { width: 8, height: 8, borderRadius: '50%', background: dotColor, flex: '0 0 auto', display: 'inline-block' } }),
          React.createElement('div', { style: { flex: '0 0 auto', minWidth: 0 } },
            React.createElement('div', { style: { fontSize: 13, fontWeight: 700, color: '#f1f5f9', whiteSpace: 'nowrap' } }, t.title),
            React.createElement('div', { style: { fontSize: 11, color: C.sub, marginTop: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 250 } }, status),
          ),
          React.createElement('div', { style: { flex: 1, minWidth: 8 } }),
          React.createElement('button', { onClick: () => setLang(lang === 'zh' ? 'en' : 'zh'), className: 'dsr-btn2', style: { ...btn2, padding: '6px 10px', fontSize: 11 } }, lang === 'zh' ? 'EN' : '中文'),
          React.createElement('button', { onClick: rebuildFromDeck, className: 'dsr-primary', style: { ...btnPrimary, padding: '6px 12px' } }, '⟳ ' + t.rebuild),
          React.createElement('button', { onClick: () => { setOpen(false); setPos(null) }, className: 'dsr-btn2', style: { ...btn2, padding: '6px 9px' } }, '✕'),
        ),
        React.createElement('div', { style: { flex: '1 1 auto', minHeight: 0, overflowY: 'auto', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 12 } },
          React.createElement('div', { style: { background: C.section, border: C.border, borderRadius: 12, padding: 10, flex: '0 0 auto' } },
            React.createElement('canvas', { ref: canvasRef, width: 960, height: 540,
              onMouseDown: onMouseDown, onMouseMove: onMouseMove, onMouseUp: onMouseUp, title: t.hint,
              style: { width: '100%', height: 'auto', background: '#fff', borderRadius: 8, display: 'block', cursor: 'crosshair', border: '1px solid rgba(90,100,130,0.35)' } }),
          ),
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, flex: '0 0 auto' } },
            React.createElement('button', { onClick: () => goto(-1), className: 'dsr-btn2', style: { ...btn2, padding: '6px 10px' } }, '◀'),
            React.createElement('div', { style: { flex: 1, display: 'flex', gap: 6, overflowX: 'auto', padding: '3px 2px', alignItems: 'center' } },
              Array.from({ length: totalSlides }, (_, i) =>
                React.createElement(Thumb, { key: i, slide: i, active: i === viewSlide, onClick: () => setViewSlide(i), framesRef: framesBySlideRef, version: thumbRev })),
            ),
            React.createElement('span', { style: { fontSize: 11, color: C.sub, whiteSpace: 'nowrap' } },
              t.page + (viewSlide + 1) + t.pageOf + (totalSlides || '—') + t.pageUnit),
            React.createElement('button', { onClick: () => goto(1), className: 'dsr-btn2', style: { ...btn2, padding: '6px 10px' } }, '▶'),
          ),
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, padding: 10, background: C.section, border: C.border, borderRadius: 12, flexWrap: 'wrap', flex: '0 0 auto' } },
            React.createElement('input', { type: 'color', value: /^#[0-9a-fA-F]{6}$/.test(reqColor) ? reqColor : '#C0392B', onChange: (e) => setReqColor(e.target.value), title: t.recolor, style: colorInputStyle }),
            React.createElement('input', { style: { ...inputStyle, width: 76, flex: '0 0 auto' }, value: reqColor, onChange: (e) => setReqColor(e.target.value), title: t.recolor }),
            React.createElement('button', { onClick: addColorRequest, className: 'dsr-primary', style: { ...btnPrimary, padding: '7px 12px' }, title: t.recolor },
              React.createElement('span', { style: { display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: reqColor, marginRight: 6, border: '1px solid rgba(255,255,255,0.4)' } }),
              t.addRecolor),
            React.createElement('input', { style: { ...inputStyle, flex: 1, minWidth: 140 }, value: question, placeholder: t.qPlaceholder, onChange: (e) => setQuestion(e.target.value) }),
            React.createElement('button', { onClick: addQuestion, className: 'dsr-btn2', style: { ...btn2, padding: '7px 12px' }, title: t.question }, '❓ ' + t.addQuestion),
          ),
          requests.length > 0 ? React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 6, flex: '0 0 auto' } },
            React.createElement('div', { style: sectTitle }, t.feedbackTitle + ' · ' + requests.length),
            React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 176, overflowY: 'auto', paddingRight: 2 } },
              requests.map((rq, i) => {
                const icon = rq.type === 'color'
                  ? React.createElement('span', { style: { width: 14, height: 14, borderRadius: 4, background: rq.color_hex, border: '1px solid rgba(255,255,255,0.35)', flex: '0 0 auto' } })
                  : React.createElement('span', { style: { fontSize: 13, flex: '0 0 auto', width: 16, textAlign: 'center' } }, rq.type === 'question' ? '❓' : '▭')
                const label = rq.type === 'color' ? t.colorPage + (rq.slide + 1) + t.colorPage2 + (rq.label || rq.elem_id) + ' → ' + rq.color_hex
                  : rq.type === 'question' ? t.questionPage + (rq.slide + 1) + t.questionPage2 + rq.elem_id + '：' + rq.question
                  : t.areaPage + (rq.slide + 1) + t.pageUnit + t.pageArea + (rq.elems || []).length + t.pageArea2 + rq.question
                const barColor = rq.type === 'color' ? rq.color_hex : rq.type === 'question' ? '#f59e0b' : '#3b82f6'
                return React.createElement('div', { key: i, style: { display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', background: C.section, border: C.border, borderRadius: 8, borderLeft: '3px solid ' + barColor } },
                  icon,
                  React.createElement('span', { style: { flex: 1, fontSize: 11, color: '#cbd5e1', wordBreak: 'break-word', minWidth: 0 } }, label),
                  React.createElement('button', { onClick: () => { const nx = requests.filter((_, j) => j !== i); setRequests(nx); svc().saveFeedback({ requests: nx }).catch(() => {}) }, className: 'dsr-btn2', style: { background: 'transparent', color: '#f87171', border: 'none', cursor: 'pointer', fontSize: 13, padding: '2px 7px', borderRadius: 6, flex: '0 0 auto' } }, '✕'),
                )
              }),
            ),
          ) : null,
          requests.length > 0 ? React.createElement('button', { onClick: applyAndRebuild, className: 'dsr-primary', style: { ...btnPrimary, width: '100%', padding: '11px 16px', fontSize: 13, borderRadius: 10 } },
            '⟳ ' + t.applyRebuild) : null,
          React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 8, borderTop: C.border, paddingTop: 12, marginTop: 2, flex: '0 0 auto' } },
            React.createElement('details', { style: { fontSize: 12, color: '#cbd5e1' } },
              React.createElement('summary', { style: { cursor: 'pointer', ...sectTitle } }, t.paletteTitle),
              React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, flexWrap: 'wrap' } },
                React.createElement('span', { style: { fontSize: 11, color: C.sub } }, t.accent),
                React.createElement('input', { type: 'color', value: /^#[0-9a-fA-F]{6}$/.test(pal.accent_hex || '') ? pal.accent_hex : '#1D4ED8', onChange: (e) => savePal({ ...pal, accent_hex: e.target.value }), style: colorInputStyle }),
                React.createElement('input', { style: { ...inputStyle, width: 84, flex: '0 0 auto' }, value: pal.accent_hex, placeholder: '#1D4ED8', onChange: (e) => savePal({ ...pal, accent_hex: e.target.value }) }),
                React.createElement('span', { style: { fontSize: 11, color: C.sub } }, t.background),
                React.createElement('input', { type: 'color', value: /^#[0-9a-fA-F]{6}$/.test(pal.bg_hex || '') ? pal.bg_hex : '#FFFFFF', onChange: (e) => savePal({ ...pal, bg_hex: e.target.value }), style: colorInputStyle }),
                React.createElement('input', { style: { ...inputStyle, width: 84, flex: '0 0 auto' }, value: pal.bg_hex, placeholder: '#FFFFFF', onChange: (e) => savePal({ ...pal, bg_hex: e.target.value }) }),
                React.createElement('button', { onClick: () => savePal({ accent_hex: '', bg_hex: '', swatches: pal.swatches }), className: 'dsr-btn2', style: { ...btn2, padding: '7px 10px' } }, t.clear),
              ),
              React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 6, marginTop: 10, flexWrap: 'wrap' } },
                React.createElement('span', { style: { fontSize: 11, color: C.sub } }, t.quick),
                swatches.map((c) => React.createElement('button', { key: c, onClick: () => savePal({ ...pal, accent_hex: c }), title: c, className: 'dsr-sw',
                  style: { width: 22, height: 22, borderRadius: 6, border: pal.accent_hex === c ? '2px solid #fff' : '1px solid rgba(90,100,130,0.5)', background: c, cursor: 'pointer', padding: 0 } })),
                React.createElement('button', { onClick: () => { const c = prompt('hex e.g. #8C97A3'); if (c && /^#[0-9a-fA-F]{6}$/.test(c)) savePal({ ...pal, swatches: [...swatches, c], accent_hex: pal.accent_hex || c }) }, className: 'dsr-btn2', style: { ...btn2, padding: '6px 10px' } }, t.custom),
              ),
            ),
            React.createElement('details', { style: { fontSize: 12, color: '#cbd5e1' } },
              React.createElement('summary', { style: { cursor: 'pointer', ...sectTitle } }, t.advancedTitle),
              React.createElement('textarea', { value: deckText, onChange: (e) => setDeckText(e.target.value), rows: 3, placeholder: t.deckPlaceholder,
                style: { width: '100%', marginTop: 10, background: C.input, color: '#cbd5e1', border: C.border, borderRadius: 8, padding: 8, fontFamily: 'monospace', fontSize: 11, boxSizing: 'border-box', resize: 'vertical' } }),
              React.createElement('div', { style: { marginTop: 8, display: 'flex', gap: 6 } },
                React.createElement('button', { onClick: () => svc().loadDeck().then((r) => { if (r && r.deck) setDeckText(JSON.stringify(r.deck, null, 2)) }).catch(() => {}), className: 'dsr-btn2', style: { ...btn2 } }, t.loadDeck),
              ),
            ),
          ),
        ),
      )
      return React.createElement(React.Fragment, null, footBtn, winEl)
    }

    slots.inject('sidebar.footer.action', () => slots.register(
      { name: 'sidebar.footer.action', id: 'ppt-reflex', order: 5, label: 'PPT' },
      () => React.createElement(Panel, null),
    ))
  },
};

return module.exports;
  }
});
