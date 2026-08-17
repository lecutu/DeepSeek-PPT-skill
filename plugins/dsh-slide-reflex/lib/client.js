// dsh-slide-reflex — Client half (v3: PNG-based preview browser)
// v3 与 v2 的差异（架构变更）：
//   - 视觉层：不再用帧流 canvas 重绘，改为展示引擎真实渲染的 PNG
//     （watcher 构建自动带 render_png，输出到 cwd/_render_vision）。
//   - 数据通道：轮询 previewState（PNG 列表 + 每页元素几何），单张图用
//     slideImage 拉 base64。帧文件退役为"元素几何数据源"（框选命中用）。
//   - 交互保留：点选元素 / 框选区域 → 改色 / 提问（反馈链路不变）。
//   - 通信：直接 fetch 宿主 RPC（信封协议与网关一致），原生 setInterval。
window.__ModuleLoader__.load({
  id: "dsh-slide-reflex",
  factory: (require) => {
    var module = { exports: {} };
    var exports = module.exports;
    const React = require("react");

const SERVICE = 'slideReflex'
const POLL_MS = 400
const PAGE_W = 960
const PAGE_H = 540

// ---------------------------------------------------------------------------
// RPC helper — direct fetch to the host gateway.
// ---------------------------------------------------------------------------
function rpc(method, args) {
  const rpcId = (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : 'r' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10)
  return fetch('/api/' + SERVICE + '/' + method, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      type: 'client-request',
      rpcId,
      method: SERVICE + '/' + method,
      payload: { args: args || {} },
    }),
  }).then((resp) => {
    if (!resp.ok) throw new Error('HTTP ' + resp.status)
    return resp.json()
  }).then((env) => {
    if (!env || env.type !== 'server-response') throw new Error('bad server envelope')
    if (!env.result || env.result.ok !== true) {
      const e = env.result && env.result.error
      throw new Error((e && (e.message || e.code)) || 'rpc failed')
    }
    return env.result.value
  })
}

const previewState = () => rpc('previewState')
const slideImage = (slide) => rpc('slideImage', { request: { slide } })
const loadPalette = () => rpc('loadPalette')
const loadDeck = () => rpc('loadDeck')
const saveSelection = (req) => rpc('saveSelection', { request: req })
const saveFeedback = (req) => rpc('saveFeedback', { request: req })
const savePalette = (req) => rpc('savePalette', { request: req })
const applyFeedbackBuild = (req) => rpc('applyFeedbackBuild', { request: req })
const buildDeck = (deck) => rpc('build', Object.assign({ action: 'build' }, deck))

const I18N = {
  zh: {
    entry: 'PPT 预览', btnOpen: '▸ PPT 预览', title: 'PPT 预览', foot: 'PPT 制作',
    waitBuild: '等待构建（在对话里说需求，助手自动生成）',
    building: '构建中… ', elems: ' 个元素',
    done: '完成 ✓ ', fail: '失败 ✗', loaded: '已渲染 ', page: '第 ', pageOf: ' / ', pageUnit: ' 页',
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
    entry: 'PPT Preview', btnOpen: '▸ PPT Preview', title: 'PPT Preview', foot: 'PPT Maker',
    waitBuild: 'Waiting for build (state your need in chat, agent auto-generates)',
    building: 'Building… ', elems: ' elements',
    done: 'Done ✓ ', fail: 'Failed ✗', loaded: 'Rendered ', page: 'Page ', pageOf: ' / ', pageUnit: '',
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

const UI_STYLE_ID = 'dsh-slide-reflex-ui'
const UI_CSS = [
  '@keyframes dsrSlideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }',
  '@keyframes dsrFadeIn { from { opacity: 0 } to { opacity: 1 } }',
  '@keyframes dsrPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.35 } }',
  '.dsr-win { animation: dsrSlideIn 260ms ease; }',
  '.dsr-mask { animation: dsrFadeIn 200ms ease; }',
  '.dsr-dot-pulse { animation: dsrPulse 1.1s ease-in-out infinite; }',
  '.dsr-entry { display: inline-flex; align-items: center; justify-content: center; min-width: 48px; height: 28px; padding: 0 12px; border-radius: 999px; border: 1.5px solid var(--dsw-alias-border-strong); background: var(--dsw-alias-bg-layer-2); color: var(--dsw-alias-label-primary); cursor: pointer; font-size: 12px; font-weight: 700; letter-spacing: 0.5px; line-height: 1; flex: 0 0 auto; transition: background .15s ease, border-color .15s ease, color .15s ease; box-sizing: border-box; }',
  '.dsr-entry:hover { background: var(--dsw-alias-interactive-bg-hover); color: var(--dsw-alias-label-primary); }',
  '.dsr-primary { transition: filter .15s ease; }',
  '.dsr-primary:hover { filter: brightness(1.1) !important; }',
  '.dsr-btn2 { transition: background .15s ease, border-color .15s ease; }',
  '.dsr-btn2:hover { background: color-mix(in srgb, var(--dsw-alias-bg-layer-2) 85%, var(--dsw-alias-brand-primary)) !important; border-color: var(--dsw-alias-border-l2) !important; }',
  '.dsr-sw { transition: transform .12s ease; }',
  '.dsr-sw:hover { transform: scale(1.12); }',
  '.dsr-thumb { transition: border-color .12s ease, box-shadow .12s ease; cursor: pointer; }',
  '.dsr-thumb:hover { border-color: var(--dsw-alias-brand-primary) !important; }',
  '.dsr-win input:not([type="color"]), .dsr-win textarea { transition: border-color .15s ease; }',
  '.dsr-win input:not([type="color"]):focus, .dsr-win textarea:focus { border-color: var(--dsw-alias-brand-primary) !important; outline: none; }',
].join('\n')
function ensureStyle() {
  if (document.getElementById(UI_STYLE_ID)) return
  const el = document.createElement('style')
  el.id = UI_STYLE_ID
  el.textContent = UI_CSS
  document.head.appendChild(el)
}

    module.exports = {
      inject: [],
      async apply(ctx) {
    const slots = ctx.get('slots')
    if (slots === undefined) return
    ensureStyle()

    function Panel(props) {
      const [open, setOpen] = React.useState(true)
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
      const [imgTick, setImgTick] = React.useState(0)
      const [pal, setPal] = React.useState({ accent_hex: '', bg_hex: '', swatches: [] })
      const [deckText, setDeckText] = React.useState('')
      const imgRef = React.useRef(null)
      const wrapRef = React.useRef(null)
      const previewRef = React.useRef({ epoch: null, building: false, rendered: [], elements: {}, images: {} })
      const epochRef = React.useRef(null)
      const autoOpenedRef = React.useRef(false)
      const dragStartRef = React.useRef(null)

      // 预取一页 PNG 到缓存
      const loadImage = (slide) => {
        if (previewRef.current.images[slide] !== undefined) return
        slideImage(slide).then((r) => {
          if (r && r.ok && r.data) {
            previewRef.current.images[slide] = 'data:image/png;base64,' + r.data
            setImgTick((v) => v + 1)
          }
        }).catch(() => {})
      }

      // 预取所有已渲染页
      const prefetchAll = () => {
        for (const r of previewRef.current.rendered) loadImage(r.slide)
      }

      React.useEffect(() => {
        if (open) {
          loadPalette().then((r) => { if (r && r.palette) setPal({ accent_hex: r.palette.accent_hex || '', bg_hex: r.palette.bg_hex || '', swatches: r.palette.swatches || [] }) }).catch(() => {})
        }
        let alive = true
        const tick = async () => {
          try {
            const r = await previewState()
            if (!alive) return
            if (r && Array.isArray(r.rendered)) {
              const epochChanged = typeof r.epoch === 'number' && r.epoch !== epochRef.current
              if (epochChanged) {
                epochRef.current = r.epoch
                previewRef.current.images = {}
                setViewSlide(0)
                setSelElem(''); setSelArea(null)
              }
              const prev = previewRef.current
              prev.epoch = r.epoch
              prev.building = !!r.building
              prev.rendered = r.rendered
              prev.elements = r.elements || {}
              const slides = r.rendered.length
              setTotalSlides(slides)
              if (slides > 0) {
                if (viewSlide >= slides) setViewSlide(slides - 1)
                prefetchAll()
              }
              if (r.building) { setStatus(t.building + t.elems.trim()); setStatusKind('building') }
              else if (slides === 0) { setStatus(t.waitBuild); setStatusKind('wait') }
              else if (epochChanged) { setStatus(t.loaded + slides + t.pageUnit); setStatusKind('done') }
            } else {
              setStatus(t.error + 'bad payload'); setStatusKind('fail')
            }
          } catch (e) {
            if (!alive) return
            setStatus(t.error + (e && e.message ? e.message : String(e))); setStatusKind('fail')
          }
        }
        tick()
        const iv = setInterval(tick, POLL_MS)
        return () => { alive = false; clearInterval(iv) }
      }, [open, viewSlide, lang])

      // 当前页图就绪后确保缓存命中
      React.useEffect(() => {
        if (open && totalSlides > 0) loadImage(viewSlide)
      }, [open, viewSlide, totalSlides, imgTick])

      const goto = (d) => setViewSlide(Math.max(0, Math.min(totalSlides - 1, viewSlide + d)))

      // 坐标换算：显示尺寸 ↔ 960×540 页面坐标
      const toCanvas = (e) => {
        const img = imgRef.current
        if (!img) return { x: 0, y: 0 }
        const rect = img.getBoundingClientRect()
        return {
          x: (e.clientX - rect.left) * (PAGE_W / rect.width),
          y: (e.clientY - rect.top) * (PAGE_H / rect.height),
        }
      }
      const scale = () => {
        const img = imgRef.current
        if (!img) return 1
        const rect = img.getBoundingClientRect()
        return { sx: rect.width / PAGE_W, sy: rect.height / PAGE_H }
      }
      const hitElements = (p) => {
        const list = previewRef.current.elements[viewSlide] || []
        const hit = []
        for (const el of list) {
          if (el.x <= p.x && p.x <= el.x + el.w && el.y <= p.y && p.y <= el.y + el.h) hit.push(el)
        }
        return hit
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
          const hit = hitElements(p)
          if (hit.length > 0) {
            const el = hit[hit.length - 1]
            setSelElem(el.elem_id)
            setSelArea(null)
            saveSelection({ elem_id: el.elem_id, kind: 'text', slide: viewSlide, text: el.text ? String(el.text).slice(0, 30) : '' }).catch(() => {})
            setStatus(t.selectedElem + el.elem_id + t.canEdit)
          } else {
            setSelElem(''); setSelArea(null)
          }
          return
        }
        const rect = { x: Math.min(s.x, p.x), y: Math.min(s.y, p.y), w: Math.abs(p.x - s.x), h: Math.abs(p.y - s.y) }
        if (rect.w < 10 && rect.h < 10) return
        const elems = hitElements({ x: rect.x, y: rect.y }).concat(
          previewRef.current.elements[viewSlide] || []).filter((el, i, arr) =>
            arr.indexOf(el) === i && el.x < rect.x + rect.w && el.x + el.w > rect.x && el.y < rect.y + rect.h && el.y + el.h > rect.y)
        setSelArea({ ...rect, elems: elems.map((el) => el.elem_id) })
        setSelElem('')
        saveSelection({ slide: viewSlide, area: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.w), h: Math.round(rect.h) }, elems: elems.map((el) => el.elem_id) }).catch(() => {})
        setStatus(t.boxSelected + elems.length + t.boxSelected2)
      }

      const addColorRequest = () => {
        if (!selElem) { setStatus(t.needElem); return }
        const el = (previewRef.current.elements[viewSlide] || []).find((x) => x.elem_id === selElem)
        const label = el && el.text ? String(el.text).slice(0, 14) : selElem
        const next = [...requests, { type: 'color', slide: viewSlide, elem_id: selElem, color_hex: reqColor, label }]
        setRequests(next)
        saveFeedback({ requests: next }).catch(() => {})
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
        saveFeedback({ requests: next }).catch(() => {})
        setStatus(t.questionNoted)
      }
      const applyAndRebuild = () => {
        const colors = requests.filter((r) => r.type === 'color')
        if (colors.length === 0) { setStatus(t.noColorReq); return }
        setStatus(t.applyRecolor)
        applyFeedbackBuild({ requests }).then((r) => {
          if (r && (r.hostError || r.ok === false)) setStatus(t.applyFailed + String(r.hostError || 'build failed').slice(-200))
          else setStatus(t.rebuildStarted)
        }).catch((e) => setStatus(t.error + String(e)))
      }
      const rebuildFromDeck = () => {
        try {
          const d = JSON.parse(deckText)
          previewRef.current.images = {}
          setViewSlide(0); setTotalSlides(0)
          setStatus(t.rebuildInit)
          buildDeck(d).then(() => setStatus(t.rebuildDone)).catch((e) => setStatus(t.error + String(e)))
        } catch { setStatus(t.jsonInvalid) }
      }
      const DEFAULT_SWATCHES = ['#1D4ED8', '#0F172A', '#1B3A5C', '#0052D9', '#C0392B', '#0D9486']
      const swatches = pal.swatches && pal.swatches.length ? pal.swatches : DEFAULT_SWATCHES

      const C = { bg: 'var(--dsw-alias-bg-base)', section: 'var(--dsw-alias-bg-layer-2)', layer2: 'var(--dsw-alias-bg-layer-2)', border: '1px solid var(--dsw-alias-border-l1)', borderStrong: 'var(--dsw-alias-border-l2)', primary: 'var(--dsw-alias-brand-primary)', text: 'var(--dsw-alias-label-primary)', sub: 'var(--dsw-alias-label-secondary)', input: 'var(--dsw-alias-bg-layer-3)', warn: 'var(--dsw-alias-state-warn-primary)', err: 'var(--dsw-alias-state-error-primary)' }
      const inputStyle = { background: C.input, color: C.text, border: C.border, borderRadius: 8, padding: '7px 8px', fontSize: 12, fontFamily: 'inherit', boxSizing: 'border-box' }
      const colorInputStyle = { width: 30, height: 30, border: C.border, borderRadius: 8, background: 'transparent', cursor: 'pointer', padding: 0, flex: '0 0 auto' }
      const btnPrimary = { background: C.primary, color: 'var(--dsw-alias-label-primary-foreground)', border: 'none', borderRadius: 8, padding: '7px 14px', cursor: 'pointer', fontWeight: 600, fontFamily: 'inherit', fontSize: 12 }
      const btn2 = { background: C.layer2, color: C.text, border: C.border, borderRadius: 8, padding: '7px 11px', cursor: 'pointer', fontFamily: 'inherit', fontSize: 12 }
      const sectTitle = { fontSize: 11, fontWeight: 700, color: C.sub, textTransform: 'uppercase', letterSpacing: '0.5px' }

      const dotColor = { wait: 'var(--dsw-alias-label-secondary)', building: 'var(--dsw-alias-state-warn-primary)', done: 'var(--dsw-alias-state-success-primary)', fail: 'var(--dsw-alias-state-error-primary)', loaded: 'var(--dsw-alias-brand-primary)' }[statusKind] || 'var(--dsw-alias-label-secondary)'
      const closePanel = () => { autoOpenedRef.current = true; setOpen(false) }
      const entryBtn = React.createElement('button', {
        className: 'dsr-entry',
        type: 'button',
        onClick: () => { if (open) autoOpenedRef.current = true; setOpen(!open) },
        title: t.title,
        'aria-label': t.title,
      }, 'PPT')
      if (!open) return entryBtn

      // 选中/框选/拖拽高亮（显示坐标 = 页面坐标 × 显示缩放）
      const sc = scale()
      const overlays = []
      const pushBox = (r, style) => {
        if (!r) return
        overlays.push(React.createElement('div', { key: overlays.length, style: {
          position: 'absolute', pointerEvents: 'none', boxSizing: 'border-box',
          left: r.x * sc.sx, top: r.y * sc.sy, width: r.w * sc.sx, height: r.h * sc.sy,
          ...style,
        } }))
      }
      if (selArea) pushBox(selArea, { border: '2px dashed #3b82f6', background: 'rgba(59,130,246,0.12)' })
      if (selElem) {
        const el = (previewRef.current.elements[viewSlide] || []).find((x) => x.elem_id === selElem)
        if (el) pushBox(el, { border: '3px solid #3b82f6' })
      }
      if (dragRect) pushBox(dragRect, { border: '2px dashed #3b82f6', background: 'rgba(59,130,246,0.12)' })

      const currentImg = previewRef.current.images[viewSlide]

      const maskEl = React.createElement('div', {
        className: 'dsr-mask',
        onClick: closePanel,
        style: { position: 'fixed', inset: 0, zIndex: 9999, background: 'color-mix(in srgb, var(--dsw-alias-bg-overlay) 50%, transparent)' },
      })
      const winEl = React.createElement('div', {
        className: 'dsr-win',
        style: { position: 'fixed', zIndex: 10000,
          right: 0, top: 0, height: '100vh', width: 480, maxWidth: '92vw',
          display: 'flex', flexDirection: 'column', background: 'var(--dsw-alias-bg-layer-1)', color: 'var(--dsw-alias-label-primary)',
          borderLeft: '1px solid var(--dsw-alias-border-l2)', boxShadow: '-16px 0 48px rgba(0,0,0,0.45)',
          overflow: 'hidden', fontFamily: 'inherit', fontSize: 13 },
      },
        React.createElement('div', {
          style: { display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px',
            borderBottom: '1px solid var(--dsw-alias-border-l1)', background: 'var(--dsw-alias-bg-layer-2)',
            flex: '0 0 auto', userSelect: 'none' },
        },
          React.createElement('span', { className: statusKind === 'building' ? 'dsr-dot-pulse' : undefined,
            style: { width: 8, height: 8, borderRadius: '50%', background: dotColor, flex: '0 0 auto', display: 'inline-block' } }),
          React.createElement('div', { style: { flex: '0 0 auto', minWidth: 0 } },
            React.createElement('div', { style: { fontSize: 13, fontWeight: 700, color: 'var(--dsw-alias-label-primary)', whiteSpace: 'nowrap' } }, t.title),
            React.createElement('div', { style: { fontSize: 11, color: C.sub, marginTop: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 230 } }, status),
          ),
          React.createElement('div', { style: { flex: 1, minWidth: 8 } }),
          React.createElement('button', { onClick: () => setLang(lang === 'zh' ? 'en' : 'zh'), className: 'dsr-btn2', style: { ...btn2, padding: '6px 10px', fontSize: 11 } }, lang === 'zh' ? 'EN' : '中文'),
          React.createElement('button', { onClick: rebuildFromDeck, className: 'dsr-primary', style: { ...btnPrimary, padding: '6px 12px' } }, '⟳ ' + t.rebuild),
          React.createElement('button', { onClick: closePanel, className: 'dsr-btn2', style: { ...btn2, padding: '6px 9px' } }, '✕'),
        ),
        React.createElement('div', { style: { flex: '1 1 auto', minHeight: 0, overflowY: 'auto', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 12 } },
          React.createElement('div', { style: { background: C.section, border: C.border, borderRadius: 12, padding: 10, flex: '0 0 auto' } },
            React.createElement('div', { ref: wrapRef, style: { position: 'relative', lineHeight: 0 } },
              currentImg
                ? React.createElement('img', { ref: imgRef, src: currentImg, width: 960, height: 540,
                    onMouseDown: onMouseDown, onMouseMove: onMouseMove, onMouseUp: onMouseUp, title: t.hint, draggable: false,
                    style: { width: '100%', height: 'auto', background: '#fff', borderRadius: 8, display: 'block', cursor: 'crosshair', border: '1px solid var(--dsw-alias-border-l1)', userSelect: 'none' } })
                : React.createElement('div', { ref: imgRef, style: { width: '100%', aspectRatio: '960 / 540', background: '#fff', borderRadius: 8, border: '1px solid var(--dsw-alias-border-l1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8', fontSize: 12, lineHeight: '1.5' } }, statusKind === 'wait' ? t.waitBuild : status),
              ...overlays,
            ),
          ),
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, flex: '0 0 auto' } },
            React.createElement('button', { onClick: () => goto(-1), className: 'dsr-btn2', style: { ...btn2, padding: '6px 10px' } }, '◀'),
            React.createElement('div', { style: { flex: 1, display: 'flex', gap: 6, overflowX: 'auto', padding: '3px 2px', alignItems: 'center' } },
              previewRef.current.rendered.map((r) =>
                React.createElement('img', { key: r.slide, src: previewRef.current.images[r.slide], width: 44, height: 25,
                  onClick: () => setViewSlide(r.slide), className: 'dsr-thumb', title: t.page + (r.slide + 1),
                  style: { width: 44, height: 25, flex: '0 0 auto', display: 'block', background: '#fff', borderRadius: 6, boxSizing: 'border-box', objectFit: 'cover', border: viewSlide === r.slide ? '2px solid var(--dsw-alias-brand-primary)' : '1px solid var(--dsw-alias-border-l1)' } })),
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
                const barColor = rq.type === 'color' ? rq.color_hex : rq.type === 'question' ? 'var(--dsw-alias-state-warn-primary)' : 'var(--dsw-alias-brand-primary)'
                return React.createElement('div', { key: i, style: { display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', background: C.section, border: C.border, borderRadius: 8, borderLeft: '3px solid ' + barColor } },
                  icon,
                  React.createElement('span', { style: { flex: 1, fontSize: 11, color: 'var(--dsw-alias-label-primary)', wordBreak: 'break-word', minWidth: 0 } }, label),
                  React.createElement('button', { onClick: () => { const nx = requests.filter((_, j) => j !== i); setRequests(nx); saveFeedback({ requests: nx }).catch(() => {}) }, className: 'dsr-btn2', style: { background: 'transparent', color: 'var(--dsw-alias-state-error-primary)', border: 'none', cursor: 'pointer', fontSize: 13, padding: '2px 7px', borderRadius: 6, flex: '0 0 auto' } }, '✕'),
                )
              }),
            ),
          ) : null,
          requests.length > 0 ? React.createElement('button', { onClick: applyAndRebuild, className: 'dsr-primary', style: { ...btnPrimary, width: '100%', padding: '11px 16px', fontSize: 13, borderRadius: 10 } },
            '⟳ ' + t.applyRebuild) : null,
          React.createElement('div', { style: { display: 'flex', flexDirection: 'column', gap: 8, borderTop: C.border, paddingTop: 12, marginTop: 2, flex: '0 0 auto' } },
            React.createElement('details', { style: { fontSize: 12, color: 'var(--dsw-alias-label-primary)' } },
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
                  style: { width: 22, height: 22, borderRadius: 6, border: pal.accent_hex === c ? '2px solid var(--dsw-alias-brand-primary)' : '1px solid var(--dsw-alias-border-l2)', background: c, cursor: 'pointer', padding: 0 } })),
                React.createElement('button', { onClick: () => { const c = prompt('hex e.g. #8C97A3'); if (c && /^#[0-9a-fA-F]{6}$/.test(c)) savePal({ ...pal, swatches: [...swatches, c], accent_hex: pal.accent_hex || c }) }, className: 'dsr-btn2', style: { ...btn2, padding: '6px 10px' } }, t.custom),
              ),
            ),
            React.createElement('details', { style: { fontSize: 12, color: 'var(--dsw-alias-label-primary)' } },
              React.createElement('summary', { style: { cursor: 'pointer', ...sectTitle } }, t.advancedTitle),
              React.createElement('textarea', { value: deckText, onChange: (e) => setDeckText(e.target.value), rows: 3, placeholder: t.deckPlaceholder,
                style: { width: '100%', marginTop: 10, background: C.input, color: 'var(--dsw-alias-label-primary)', border: C.border, borderRadius: 8, padding: 8, fontFamily: 'monospace', fontSize: 11, boxSizing: 'border-box', resize: 'vertical' } }),
              React.createElement('div', { style: { marginTop: 8, display: 'flex', gap: 6 } },
                React.createElement('button', { onClick: () => loadDeck().then((r) => { if (r && r.deck) setDeckText(JSON.stringify(r.deck, null, 2)) }).catch(() => {}), className: 'dsr-btn2', style: { ...btn2 } }, t.loadDeck),
              ),
            ),
          ),
        ),
      )
      return React.createElement(React.Fragment, null, entryBtn, maskEl, winEl)
    }

    // The client bundle is loaded globally (window.__DSH_BOOT__), so the entry
    // button would otherwise appear in every preset. The session summary's
    // agentPreset tells us which preset composed this session: render nothing
    // unless it is ppt-maker.
    function Gate(props) {
      const useSessions = props && props.useSessions
      const sessionId = props && (props.sessionId || (props.session && props.session.sessionId))
      const agentPreset = useSessions
        ? useSessions((state) => {
            if (!state || !state.byId || !sessionId) return undefined
            const summary = state.byId[sessionId]
            return summary ? summary.agentPreset : undefined
          })
        : undefined
      if (agentPreset !== 'ppt-maker') return null
      return React.createElement(Panel, props)
    }

    slots.inject('conversation.input.left', () => slots.register(
      { name: 'conversation.input.left', id: 'ppt-reflex', order: 10, label: 'PPT 预览' },
      (props) => React.createElement(Gate, props),
    ))
  },
};

return module.exports;
  }
});
