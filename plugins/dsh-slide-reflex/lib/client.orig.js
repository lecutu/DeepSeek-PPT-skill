// dsh-slide-reflex — Client half: per-page live preview panel with
// click/box-select feedback, recolor requests, palette picker, i18n.
import { z } from 'zod'

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
    btnOpen: '▸ PPT 预览', title: 'PPT 预览',
    waitBuild: '等待构建（在对话里说需求，助手自动生成）',
    building: '构建中… ', elems: ' 个元素',
    done: '完成 ✓ ', fail: '失败 ✗', loaded: '已加载 ', page: '第 ', pageOf: ' / ', pageUnit: ' 页',
    selPrefix: ' · 已选 ', rebuild: '重建',
    hint: '点选元素 / 拖拽框选区域，然后改色或提问题',
    feedbackTitle: '反馈请求', recolor: '改色', addRecolor: '+ 改色',
    question: '问题', qPlaceholder: '如：这个太大了 / 这块太挤 / 换两列', addQuestion: '+ 提问题',
    applyRebuild: '应用并重建', paletteAdvanced: '配色 & 高级', accent: '主色', background: '背景', clear: '清除', quick: '快捷',
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
    btnOpen: '▸ PPT Preview', title: 'PPT Preview',
    waitBuild: 'Waiting for build (state your need in chat, agent auto-generates)',
    building: 'Building… ', elems: ' elements',
    done: 'Done ✓ ', fail: 'Failed ✗', loaded: 'Loaded ', page: 'Page ', pageOf: ' / ', pageUnit: '',
    selPrefix: ' · selected ', rebuild: 'Rebuild',
    hint: 'Click element / drag to box-select, then recolor or ask',
    feedbackTitle: 'Feedback requests', recolor: 'Recolor', addRecolor: '+ Recolor',
    question: 'Question', qPlaceholder: 'e.g. too big / too crowded / two columns', addQuestion: '+ Ask',
    applyRebuild: 'Apply & Rebuild', paletteAdvanced: 'Palette & Advanced', accent: 'Accent', background: 'Background', clear: 'Clear', quick: 'Quick',
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

export default {
  inject: ['timer', 'remote'],
  async apply(ctx) {
    const slots = ctx.get('slots')
    if (slots === undefined) return
    const disposeRemote = await ctx.remote.$mount(TYPERT_REMOTE)
    ctx.effect(() => disposeRemote, 'dsh-slide-reflex: remote')
    const svc = () => {
      const s = ctx.remote.namespaces?.get(SERVICE)?.service
      if (s === void 0) throw new Error('slideReflex remote namespace is not mounted')
      return s
    }

    function Panel() {
      const [open, setOpen] = React.useState(false)
      const [lang, setLang] = React.useState(() => {
        try { return String(navigator.language || '').toLowerCase().startsWith('zh') ? 'zh' : 'en' } catch { return 'zh' }
      })
      const t = I18N[lang] || I18N.zh
      const [status, setStatus] = React.useState(t.waitBuild)
      const [viewSlide, setViewSlide] = React.useState(0)
      const [totalSlides, setTotalSlides] = React.useState(0)
      const [selElem, setSelElem] = React.useState('')
      const [selArea, setSelArea] = React.useState(null)
      const [reqColor, setReqColor] = React.useState('#C0392B')
      const [question, setQuestion] = React.useState('')
      const [requests, setRequests] = React.useState([])
      const [dragRect, setDragRect] = React.useState(null)
      const canvasRef = React.useRef(null)
      const framesBySlideRef = React.useRef(new Map())
      const sinceRef = React.useRef(0)
      const dragStartRef = React.useRef(null)
      const [deckText, setDeckText] = React.useState('')
      const [pal, setPal] = React.useState({ accent_hex: '', bg_hex: '', swatches: [] })

      React.useEffect(() => {
        if (!open) return
        svc().loadPalette().then((r) => { if (r && r.palette) setPal({ accent_hex: r.palette.accent_hex || '', bg_hex: r.palette.bg_hex || '', swatches: r.palette.swatches || [] }) }).catch(() => {})
        const draw = () => {
          const cv = canvasRef.current
          if (!cv) return
          const g = cv.getContext('2d')
          g.clearRect(0, 0, 960, 540)
          const page = framesBySlideRef.current.get(viewSlide) || new Map()
          for (const f of page.values()) {
            if (f.kind === 'region') {
              g.setLineDash([4, 4]); g.strokeStyle = '#94a3b8'; g.lineWidth = 1
              g.strokeRect(f.x, f.y, f.w, f.h); g.setLineDash([])
              g.fillStyle = 'rgba(148,163,184,0.06)'; g.fillRect(f.x, f.y, f.w, f.h)
              continue
            }
            if (f.fill) {
              g.fillStyle = f.fill
              const r = Math.min(8, f.w / 2, f.h / 2)
              g.beginPath(); g.moveTo(f.x + r, f.y)
              g.arcTo(f.x + f.w, f.y, f.x + f.w, f.y + f.h, r)
              g.arcTo(f.x + f.w, f.y + f.h, f.x, f.y + f.h, r)
              g.arcTo(f.x, f.y + f.h, f.x, f.y, r)
              g.arcTo(f.x, f.y, f.x + f.w, f.y, r)
              g.closePath(); g.fill()
            }
            if (f.text) {
              g.fillStyle = f.fill && parseInt(f.fill.slice(1), 16) < 0x888888 ? '#ffffff' : '#0f172a'
              g.font = (f.font_size || 16) + 'px Segoe UI, Microsoft YaHei, sans-serif'
              g.textBaseline = 'top'
              String(f.text).split('\n').slice(0, 6).forEach((ln, i) => {
                g.fillText(ln.slice(0, 40), f.x + 8, f.y + 8 + i * ((f.font_size || 16) + 4), f.w - 16)
              })
            }
            if (selElem && f.elem_id === selElem) {
              g.strokeStyle = '#3b82f6'; g.lineWidth = 3
              g.strokeRect(f.x - 2, f.y - 2, f.w + 4, f.h + 4)
            }
          }
          if (dragRect) {
            g.setLineDash([6, 4]); g.strokeStyle = '#3b82f6'; g.lineWidth = 2
            g.strokeRect(dragRect.x, dragRect.y, dragRect.w, dragRect.h); g.setLineDash([])
            g.fillStyle = 'rgba(59,130,246,0.12)'; g.fillRect(dragRect.x, dragRect.y, dragRect.w, dragRect.h)
          }
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
              if (r.frames.length > 0) draw()
              if (r.building) setStatus(t.building + sinceRef.current + t.elems)
              else if (r.result) setStatus(r.result.ok ? t.done + (r.result.summary || '') : t.fail)
              else if (sinceRef.current === 0) setStatus(t.waitBuild)
              else setStatus(t.loaded + sinceRef.current + t.elems)
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
      const sel = { background: '#0f172a', color: '#cbd5e1', border: '1px solid #334155', borderRadius: 5, padding: '3px 6px', fontSize: 12, fontFamily: 'inherit' }

      if (!open) {
        return React.createElement('button', {
          onClick: () => setOpen(true),
          style: { position: 'fixed', right: 14, bottom: 14, zIndex: 9999, border: '1px solid #475569',
            background: '#1e2430', color: '#cbd5e1', borderRadius: 8, padding: '8px 14px',
            cursor: 'pointer', fontFamily: 'inherit', fontSize: 13 },
        }, t.btnOpen)
      }
      return React.createElement('div', {
        style: { position: 'fixed', right: 14, bottom: 14, zIndex: 9999, background: '#1e2430',
          border: '1px solid #475569', borderRadius: 10, padding: 12, color: '#cbd5e1',
          width: 520, fontFamily: 'inherit', fontSize: 13, boxShadow: '0 12px 32px rgba(0,0,0,.45)',
          maxHeight: '88vh', overflowY: 'auto' },
      },
        React.createElement('div', { style: { display: 'flex', justifyContent: 'space-between', marginBottom: 8, gap: 8 } },
          React.createElement('span', { style: { flex: 1 } }, t.title + ' — ', status),
          React.createElement('button', { onClick: () => setLang(lang === 'zh' ? 'en' : 'zh'), style: { background: 'transparent', color: '#94a3b8', border: '1px solid #475569', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', fontSize: 11 } }, lang === 'zh' ? 'EN' : '中文'),
          React.createElement('button', { onClick: rebuildFromDeck, style: { background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, padding: '4px 12px', cursor: 'pointer', fontWeight: 600 } }, t.rebuild),
          React.createElement('button', { onClick: () => setOpen(false), style: { background: 'transparent', color: '#94a3b8', border: 'none', cursor: 'pointer' } }, '✕'),
        ),
        React.createElement('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 } },
          React.createElement('button', { onClick: () => goto(-1), style: { background: '#334155', color: '#e2e8f0', border: 'none', borderRadius: 5, padding: '2px 10px', cursor: 'pointer' } }, '◀'),
          React.createElement('span', { style: { fontSize: 12, color: '#cbd5e1' } },
            t.page + (viewSlide + 1) + t.pageOf + (totalSlides || '—') + t.pageUnit + (selElem ? t.selPrefix + selElem : '')),
          React.createElement('button', { onClick: () => goto(1), style: { background: '#334155', color: '#e2e8f0', border: 'none', borderRadius: 5, padding: '2px 10px', cursor: 'pointer' } }, '▶'),
        ),
        React.createElement('canvas', { ref: canvasRef, width: 960, height: 540,
          onMouseDown: onMouseDown, onMouseMove: onMouseMove, onMouseUp: onMouseUp,
          style: { width: '100%', background: '#fff', borderRadius: 6, display: 'block', cursor: 'crosshair' } }),
        React.createElement('div', { style: { marginTop: 6, fontSize: 11, color: '#64748b' } }, t.hint),
        React.createElement('div', { style: { marginTop: 8, padding: 8, background: '#161d29', borderRadius: 8 } },
          React.createElement('div', { style: { fontSize: 12, fontWeight: 600, color: '#e2e8f0', marginBottom: 6 } }, t.feedbackTitle),
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' } },
            React.createElement('span', { style: { fontSize: 11, color: '#94a3b8' } }, t.recolor),
            React.createElement('input', { type: 'color', value: /^#[0-9a-fA-F]{6}$/.test(reqColor) ? reqColor : '#C0392B', onChange: (e) => setReqColor(e.target.value), style: { width: 26, height: 22, border: 'none', background: 'transparent', cursor: 'pointer', padding: 0 } }),
            React.createElement('input', { style: { ...sel, width: 84 }, value: reqColor, onChange: (e) => setReqColor(e.target.value) }),
            React.createElement('button', { onClick: addColorRequest, style: { background: '#0d9488', color: '#fff', border: 'none', borderRadius: 6, padding: '3px 10px', cursor: 'pointer' } }, t.addRecolor),
          ),
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginTop: 6, flexWrap: 'wrap' } },
            React.createElement('span', { style: { fontSize: 11, color: '#94a3b8' } }, t.question),
            React.createElement('input', { style: { ...sel, flex: 1, minWidth: 180 }, value: question, placeholder: t.qPlaceholder, onChange: (e) => setQuestion(e.target.value) }),
            React.createElement('button', { onClick: addQuestion, style: { background: '#334155', color: '#e2e8f0', border: 'none', borderRadius: 6, padding: '3px 10px', cursor: 'pointer' } }, t.addQuestion),
          ),
          requests.length > 0 ? React.createElement('div', { style: { marginTop: 6, fontSize: 11, color: '#94a3b8' } },
            requests.map((rq, i) => React.createElement('div', { key: i, style: { display: 'flex', alignItems: 'center', gap: 8, marginTop: 3 } },
              rq.type === 'color' ? React.createElement('span', { style: { width: 12, height: 12, borderRadius: 3, background: rq.color_hex, display: 'inline-block' } }) : null,
              React.createElement('span', null,
                rq.type === 'color' ? t.colorPage + (rq.slide + 1) + t.colorPage2 + (rq.label || rq.elem_id) + ' → ' + rq.color_hex
                : rq.type === 'question' ? t.questionPage + (rq.slide + 1) + t.questionPage2 + rq.elem_id + '：' + rq.question
                : t.areaPage + (rq.slide + 1) + t.pageUnit + t.pageArea + (rq.elems || []).length + t.pageArea2 + rq.question),
              React.createElement('button', { onClick: () => { const nx = requests.filter((_, j) => j !== i); setRequests(nx); svc().saveFeedback({ requests: nx }).catch(() => {}) }, style: { background: 'transparent', color: '#f87171', border: 'none', cursor: 'pointer', fontSize: 11 } }, '✕'),
            )),
            React.createElement('button', { onClick: applyAndRebuild, style: { marginTop: 6, background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, padding: '4px 14px', cursor: 'pointer', fontWeight: 600 } }, t.applyRebuild),
          ) : null,
        ),
        React.createElement('details', { style: { marginTop: 8, fontSize: 11, color: '#94a3b8' } },
          React.createElement('summary', { style: { cursor: 'pointer' } }, t.paletteAdvanced),
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginTop: 6, flexWrap: 'wrap' } },
            React.createElement('span', null, t.accent),
            React.createElement('input', { type: 'color', value: /^#[0-9a-fA-F]{6}$/.test(pal.accent_hex || '') ? pal.accent_hex : '#1D4ED8', onChange: (e) => savePal({ ...pal, accent_hex: e.target.value }), style: { width: 26, height: 22, border: 'none', background: 'transparent', cursor: 'pointer', padding: 0 } }),
            React.createElement('input', { style: { ...sel, width: 80 }, value: pal.accent_hex, placeholder: '#1D4ED8', onChange: (e) => savePal({ ...pal, accent_hex: e.target.value }) }),
            React.createElement('span', null, t.background),
            React.createElement('input', { type: 'color', value: /^#[0-9a-fA-F]{6}$/.test(pal.bg_hex || '') ? pal.bg_hex : '#FFFFFF', onChange: (e) => savePal({ ...pal, bg_hex: e.target.value }), style: { width: 26, height: 22, border: 'none', background: 'transparent', cursor: 'pointer', padding: 0 } }),
            React.createElement('input', { style: { ...sel, width: 80 }, value: pal.bg_hex, placeholder: '#FFFFFF', onChange: (e) => savePal({ ...pal, bg_hex: e.target.value }) }),
            React.createElement('button', { onClick: () => savePal({ accent_hex: '', bg_hex: '', swatches: pal.swatches }), style: { background: 'transparent', color: '#94a3b8', border: '1px solid #475569', borderRadius: 5, padding: '2px 8px', cursor: 'pointer' } }, t.clear),
          ),
          React.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: 6, marginTop: 6 } },
            React.createElement('span', null, t.quick),
            swatches.map((c) => React.createElement('button', { key: c, onClick: () => savePal({ ...pal, accent_hex: c }), title: c,
              style: { width: 20, height: 20, borderRadius: 4, border: pal.accent_hex === c ? '2px solid #fff' : '1px solid #475569', background: c, cursor: 'pointer', padding: 0 } })),
            React.createElement('button', { onClick: () => { const c = prompt('hex e.g. #8C97A3'); if (c && /^#[0-9a-fA-F]{6}$/.test(c)) savePal({ ...pal, swatches: [...swatches, c], accent_hex: pal.accent_hex || c }) }, title: 'add custom',
              style: { width: 20, height: 20, borderRadius: 4, border: '1px dashed #64748b', background: 'transparent', color: '#94a3b8', cursor: 'pointer', padding: 0, fontSize: 12, lineHeight: '18px' } }, '+'),
          ),
          React.createElement('textarea', { value: deckText, onChange: (e) => setDeckText(e.target.value), rows: 3,
            placeholder: t.deckPlaceholder,
            style: { width: '100%', marginTop: 6, background: '#0f172a', color: '#cbd5e1', border: '1px solid #334155', borderRadius: 6, padding: 6, fontFamily: 'monospace', fontSize: 11, boxSizing: 'border-box' } }),
          React.createElement('div', { style: { marginTop: 6, display: 'flex', gap: 6 } },
            React.createElement('button', { onClick: () => svc().loadDeck().then((r) => { if (r && r.deck) setDeckText(JSON.stringify(r.deck, null, 2)) }).catch(() => {}), style: { background: 'transparent', color: '#94a3b8', border: '1px solid #475569', borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontSize: 11 } }, t.loadDeck),
          ),
        ),
      )
    }

    slots.inject('shell.overlay', () => slots.register(
      { name: 'shell.overlay', id: 'ppt-live', order: 10, label: 'PPT Preview' },
      () => React.createElement(Panel, null),
    ))
  },
}
