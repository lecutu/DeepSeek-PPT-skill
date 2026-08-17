// dsh-slide-reflex — Host half: Typert Remote gateway bridging the
// ppt-reflex python runner and the Client preview panel. Decorators are
// expanded by hand (the runtime does not enable decorator syntax); this
// mirrors exactly what the typert generator emits.
import { readFileSync, writeFileSync, renameSync, unlinkSync, realpathSync, existsSync, statSync, watchFile, unwatchFile, readdirSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { isAbsolute, resolve, dirname, basename, sep, join } from 'node:path'
import { Remote, TypertRemoteService } from '@deepseek-ai/dsh-typert-protocol'
import { defineTool } from '@deepseek-ai/dsh-tools'
import z from '@deepseek-ai/schemastery'

function __runInitializers(thisArg, initializers, value) {
  for (let i = 0; i < initializers.length; i++) {
    value = initializers[i].call(thisArg, value)
  }
  return value
}

function __esDecorate(ctor, descriptorIn, decorators, contextIn, initializers, extraInitializers) {
  function accept(f) {
    if (f !== void 0 && typeof f !== 'function') throw new TypeError('Function expected')
    return f
  }
  const kind = contextIn.kind
  const key = kind === 'getter' ? 'get' : kind === 'setter' ? 'set' : 'value'
  const target = !descriptorIn && ctor ? (contextIn.static ? ctor : ctor.prototype) : null
  const descriptor = descriptorIn || (target ? Object.getOwnPropertyDescriptor(target, contextIn.name) : {})
  let _, done = false
  for (const decorator of decorators) {
    const context = {}
    for (const p in contextIn) context[p] = p === 'access' ? {} : contextIn[p]
    for (const p in contextIn.access) context.access[p] = contextIn.access[p]
    context.addInitializer = (f) => {
      if (done) throw new TypeError('Cannot add initializers after decoration has completed')
      extraInitializers.push(accept(f || null))
    }
    const result = decorator(kind === 'accessor' ? { get: descriptor.get, set: descriptor.set } : descriptor[key], context)
    if (kind === 'accessor') {
      if (result === void 0) continue
      if (result === null || typeof result !== 'object') throw new TypeError('Object expected')
      if ((_ = accept(result.get))) descriptor.get = _
      if ((_ = accept(result.set))) descriptor.set = _
      if ((_ = accept(result.init))) initializers.unshift(_)
    } else if ((_ = accept(result))) {
      if (kind === 'field') initializers.unshift(_)
      else descriptor[key] = _
    }
  }
  if (target) Object.defineProperty(target, contextIn.name, descriptor)
  done = true
}

const DEFAULTS = {
  python: 'C:\\Users\\Lenovo\\AppData\\Local\\Programs\\Python\\Python312\\python.exe',
  cwd: 'D:\\ppt',
  framesFile: 'D:\\ppt\\_frames_auto.jsonl',
  deckFile: 'D:\\ppt\\_deck_auto.json',
  feedbackFile: 'D:\\ppt\\_feedback_auto.json',
  selectionFile: 'D:\\ppt\\_selection_auto.json',
  paletteFile: 'D:\\ppt\\_palette_auto.json',
}

const BUILD_TIMEOUT_MS = 120000
const CONFIG_FILE_KEYS = ['framesFile', 'deckFile', 'feedbackFile', 'selectionFile', 'paletteFile']
const WATCH_POLL_MS = 800
const WATCH_DEBOUNCE_MS = 400

function readJson(path, fallback = null) {
  try { return JSON.parse(readFileSync(path, 'utf-8')) } catch { return fallback }
}

function writeJson(path, value) {
  const tmp = path + '.tmp-' + Math.random().toString(36).slice(2)
  try {
    writeFileSync(tmp, JSON.stringify(value), 'utf-8')
    renameSync(tmp, path)
  } catch (e) {
    try { unlinkSync(tmp) } catch { /* tmp never created */ }
    console.warn('[dsh-slide-reflex] writeJson failed:', path, e && e.message ? e.message : e)
  }
}

function hexToRgb(hex) {
  const h = String(hex || '').replace('#', '')
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return null
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]
}

function normPath(s) {
  return process.platform === 'win32' ? String(s).toLowerCase() : String(s)
}

function isPathWithin(child, parent) {
  const c = normPath(child)
  const p = normPath(parent)
  return c === p || c.startsWith(p + sep)
}

// realpath of a path that may not exist yet: resolve the nearest existing
// ancestor instead (mirrors Python os.path.realpath used by the runner).
function realpathFlexible(p) {
  try { return realpathSync(p) } catch { /* keep walking */ }
  let cur = p
  const tail = []
  for (;;) {
    const parent = dirname(cur)
    if (parent === cur) return resolve(p)
    try {
      return resolve(realpathSync(parent), ...tail.reverse())
    } catch { /* walk further up */ }
    tail.push(basename(cur))
    cur = parent
  }
}

// Validate the merged loader config; any invalid field falls back to DEFAULTS
// so a hostile or broken plugin config can never point the runner elsewhere.
function isExistingFile(p) {
  try { return existsSync(p) && statSync(p).isFile() } catch { return false }
}

function isExistingDir(p) {
  try { return existsSync(p) && statSync(p).isDirectory() } catch { return false }
}

function sanitizeConfig(raw) {
  const out = { ...DEFAULTS, ...(raw || {}) }
  if (typeof out.python !== 'string' || !isAbsolute(out.python) || !isExistingFile(out.python)) {
    console.warn('[dsh-slide-reflex] config.python invalid, falling back to default:', out.python)
    out.python = DEFAULTS.python
  }
  if (typeof out.cwd !== 'string' || !isAbsolute(out.cwd) || !isExistingDir(out.cwd)) {
    console.warn('[dsh-slide-reflex] config.cwd invalid, falling back to default:', out.cwd)
    out.cwd = DEFAULTS.cwd
  }
  const cwdReal = realpathFlexible(out.cwd)
  for (const key of CONFIG_FILE_KEYS) {
    const v = out[key]
    if (typeof v !== 'string' || !isAbsolute(v) || !isPathWithin(realpathFlexible(v), cwdReal)) {
      console.warn('[dsh-slide-reflex] config.' + key + ' invalid (must be an absolute path inside cwd), falling back to default:', v)
      out[key] = DEFAULTS[key]
    }
  }
  return out
}

function hashText(text) {
  return createHash('sha1').update(String(text)).digest('hex')
}

const KIND_LABELS = { card: '卡片', kpi: 'kpi 布局', quote: '引用', title: '标题', subtitle: '副标题', bullet: '要点', text: '文本', box: '元素' }
const PARAM_LABELS = { density: '密度', columns: '列数' }

function kindOf(elem) {
  if (!elem || typeof elem !== 'object') return 'unknown'
  return elem.recipe || elem.type || 'unknown'
}

function kindLabel(k) {
  return KIND_LABELS[k] || k
}

// One-sentence Chinese summary of what changed between two decks. Compares
// slide count, per-slide archetype, per-element type/recipe, and top-level
// params (density/columns). Falls back to a fixed string when nothing moved.
function summarizeDeckChange(prev, cur) {
  const curSlides = (cur && Array.isArray(cur.slides)) ? cur.slides : []
  if (!prev) return curSlides.length ? '本次：初始构建 ' + curSlides.length + ' 页' : '本次：重新构建'
  const prevSlides = (prev && Array.isArray(prev.slides)) ? prev.slides : []
  const parts = []
  if (prevSlides.length !== curSlides.length) {
    parts.push('页面数从 ' + prevSlides.length + ' 页变为 ' + curSlides.length + ' 页')
  }
  const prevArch = prev.archetype
  const curArch = cur.archetype
  if (prevArch !== curArch) {
    parts.push('整体版式由「' + (prevArch || '默认') + '」换为「' + (curArch || '默认') + '」')
  }
  const maxLen = Math.min(prevSlides.length, curSlides.length)
  for (let i = 0; i < maxLen; i++) {
    const ps = prevSlides[i] || {}
    const cs = curSlides[i] || {}
    if (ps.archetype !== cs.archetype && cs.archetype) {
      parts.push('第 ' + (i + 1) + ' 页版式由「' + (ps.archetype || '默认') + '」换为「' + cs.archetype + '」')
    }
    const pe = ps.elements || []
    const ce = cs.elements || []
    const prevMap = new Map(pe.map((e) => [String(e && e.id), e]))
    const curMap = new Map(ce.map((e) => [String(e && e.id), e]))
    const byPair = new Map()
    for (const [id, curE] of curMap) {
      const prevE = prevMap.get(id)
      if (!prevE) continue
      const a = kindOf(prevE)
      const b = kindOf(curE)
      if (a !== b) byPair.set(a + '\u0000' + b, (byPair.get(a + '\u0000' + b) || 0) + 1)
    }
    if (byPair.size) {
      for (const [pair, n] of byPair) {
        const sepIdx = pair.indexOf('\u0000')
        const from = pair.slice(0, sepIdx)
        const to = pair.slice(sepIdx + 1)
        parts.push('第 ' + (i + 1) + ' 页 ' + n + ' 个' + kindLabel(from) + '换为 ' + kindLabel(to))
      }
    }
  }
  const prevParams = prev.params || {}
  const curParams = cur.params || {}
  for (const k of Object.keys(PARAM_LABELS)) {
    // Report added or changed params (cur has the key and its value moved).
    if (curParams[k] !== undefined && String(prevParams[k]) !== String(curParams[k])) {
      parts.push(PARAM_LABELS[k] + '调为 ' + curParams[k])
    }
  }
  if (parts.length === 0) return '本次：结构不变，重新构建'
  return '本次：' + parts.slice(0, 3).join('，') + (parts.length > 3 ? '，等' : '')
}

// Index of a deck: element id → truncated text and slide index → title, used
// to inline context into feedback / selection files (agent-facing problem #5).
function buildDeckContext(deck) {
  const byId = new Map()
  const titles = new Map()
  ;(deck.slides || []).forEach((s, i) => {
    titles.set(i, s && s.title ? String(s.title) : '')
    for (const e of (s && s.elements) || []) {
      if (e && e.id !== undefined && e.id !== null) byId.set(String(e.id), { elem: e, slide: i })
    }
  })
  return {
    elemText(id) {
      const rec = (id === undefined || id === null) ? undefined : byId.get(String(id))
      if (!rec) return ''
      const raw = rec.elem.text !== undefined ? rec.elem.text : (rec.elem.content !== undefined ? rec.elem.content : '')
      const flat = String(raw).replace(/\s+/g, ' ').trim()
      return flat.length > 80 ? flat.slice(0, 80) + '…' : flat
    },
    slideTitle(idx) {
      return (typeof idx === 'number' && titles.has(idx)) ? titles.get(idx) : ''
    },
  }
}

let SlideReflexGateway = (() => {
  const _classSuper = TypertRemoteService
  const _instanceExtraInitializers = []

  return class SlideReflexGateway extends _classSuper {
    static {
      const _metadata = typeof Symbol === 'function' && Symbol.metadata ? Object.create(_classSuper[Symbol.metadata] ?? null) : void 0
      const methods = ['build', 'framesFile', 'applyFeedbackBuild', 'savePalette', 'loadPalette', 'saveFeedback', 'saveSelection', 'loadDeck', 'renderSlides']
      for (const m of methods) {
        __esDecorate(this, null, [Remote(m)], {
          kind: 'method', name: m, static: false, private: false,
          access: { has: (obj) => m in obj, get: (obj) => obj[m] },
          metadata: _metadata,
        }, null, _instanceExtraInitializers)
      }
      if (_metadata) Object.defineProperty(this, Symbol.metadata, { enumerable: true, configurable: true, writable: true, value: _metadata })
    }

    constructor(ctx) {
      super(ctx, 'slideReflex')
      __runInitializers(this, _instanceExtraInitializers)
      let merged = DEFAULTS
      try {
        for (const entry of ctx.get('loader')?.entries() ?? []) {
          if (entry.id === 'dsh-slide-reflex' && entry.options?.config) {
            merged = { ...DEFAULTS, ...entry.options.config }
          }
        }
      } catch { /* keep defaults */ }
      this.config = sanitizeConfig(merged)
      this.frames = []
      this.building = false
      this.lastResult = null
      this.epoch = 0
      this.framesMaxSeen = -1
      this.lastDeckSnapshot = null
      this._watchState = null
      this._watchStop = null
      this._pendingWatchBuild = false
      this._registerDeckWatcher()
    }

    _logInfo(...args) {
      const l = this.ctx && this.ctx.logger
      if (l && typeof l.info === 'function') l.info(...args)
      else console.log('[dsh-slide-reflex]', ...args)
    }

    _logWarn(...args) {
      const l = this.ctx && this.ctx.logger
      if (l && typeof l.warn === 'function') l.warn(...args)
      else console.warn('[dsh-slide-reflex]', ...args)
    }

    // Watcher (problem #1): the agent writes only deckFile and the host
    // auto-triggers the build. fs.watchFile polls stat (800ms) so it also
    // picks up atomic rename writes on Windows and waits for the file to be
    // created when it does not exist yet. Content hash guards against
    // touch-only mtime changes; a 400ms debounce merges consecutive writes.
    _registerDeckWatcher() {
      const file = this.config.deckFile
      const st = { lastHash: null, lastMtime: 0, baselineDone: false, timer: null, disposed: false }
      this._watchState = st
      const readSnap = () => {
        try {
          const s = statSync(file)
          if (!s.isFile()) return null
          return { mtimeMs: s.mtimeMs, hash: hashText(readFileSync(file, 'utf-8')) }
        } catch { return null }
      }
      // File already present at registration → first watch event is a no-op
      // baseline, so plugin load never triggers a spurious rebuild.
      const initial = readSnap()
      if (initial) {
        st.lastHash = initial.hash
        st.lastMtime = initial.mtimeMs
        st.baselineDone = true
      }
      const onWatch = () => {
        if (st.disposed) return
        const snap = readSnap()
        if (!snap) return // file missing (or not yet created) — keep polling
        if (snap.mtimeMs === st.lastMtime && snap.hash === st.lastHash) return
        const changed = snap.hash !== st.lastHash
        st.lastMtime = snap.mtimeMs
        st.lastHash = snap.hash
        if (!st.baselineDone) {
          st.baselineDone = true
          // First appearance after a file-less start = creation → build.
          if (changed) this._scheduleWatchBuild()
          return
        }
        if (changed) this._scheduleWatchBuild()
      }
      try {
        watchFile(file, { interval: WATCH_POLL_MS, persistent: false }, onWatch)
      } catch (e) {
        this._logWarn('watch: cannot register deck watcher: ' + String(e && e.message ? e.message : e))
        return
      }
      const stop = () => {
        st.disposed = true
        if (st.timer) { clearTimeout(st.timer); st.timer = null }
        try { unwatchFile(file, onWatch) } catch { /* already stopped */ }
      }
      this._watchStop = stop
      try {
        if (this.ctx && typeof this.ctx.effect === 'function') this.ctx.effect(() => stop, 'dsh-slide-reflex: deck watcher')
      } catch { /* effect unavailable — persistent:false keeps it from holding the process */ }
    }

    _scheduleWatchBuild() {
      const st = this._watchState
      if (!st || st.disposed) return
      if (st.timer) clearTimeout(st.timer)
      st.timer = setTimeout(() => {
        st.timer = null
        this._runWatchBuild()
      }, WATCH_DEBOUNCE_MS)
      if (typeof st.timer.unref === 'function') st.timer.unref()
    }

    async _runWatchBuild() {
      if (this.building) {
        // A build (explicit ppt_build or an earlier watch build) is running;
        // the deck change must not be dropped — queue it and rebuild after.
        this._logWarn('watch: build already running, queueing this change')
        this._pendingWatchBuild = true
        return
      }
      try {
        const deck = readJson(this.config.deckFile)
        if (!deck || !Array.isArray(deck.slides)) {
          this._logWarn('watch: deck file unreadable or empty, skipping')
          return
        }
        this._logInfo('watch: deck changed → build')
        try {
          // watcher 触发的构建是"预览构建"：自动附带 PNG 渲染，
          // 面板直接展示真实渲染图（render_dir 缺省 = cwd/_render_vision）。
          const res = await this.build(Object.assign({}, deck, { render_png: true }))
          if (res && res.hostError === 'busy') this._logWarn('watch: build already running, skipped')
          else this._logInfo('watch: build ' + (res && res.ok ? 'ok' : 'failed') + (res && res.hostError ? ' — ' + res.hostError : ''))
        } catch (e) {
          this._logWarn('watch: build threw: ' + String(e && e.message ? e.message : e))
        }
      } finally {
        if (this._pendingWatchBuild) {
          this._pendingWatchBuild = false
          this._logWarn('watch: queued change → rebuild')
          this._scheduleWatchBuild()
        }
      }
    }

    // applyFeedbackBuild writes deckFile itself right before building; record
    // the just-written content as the watcher's known state so the self-write
    // never re-triggers a second build.
    _markWatchSelfWrite() {
      const st = this._watchState
      if (!st) return
      try {
        const s = statSync(this.config.deckFile)
        st.lastMtime = s.mtimeMs
        st.lastHash = hashText(readFileSync(this.config.deckFile, 'utf-8'))
        st.baselineDone = true
      } catch { /* deck file not on disk yet */ }
    }

    // Summary (problem #6): diff the just-built deck against the previous
    // snapshot and expose a one-line Chinese summary on the runner result.
    _afterBuild(curDeck) {
      const summary = summarizeDeckChange(this.lastDeckSnapshot, curDeck)
      if (this.lastResult) this.lastResult.summary = summary
      this.lastDeckSnapshot = JSON.parse(JSON.stringify(curDeck))
    }

    // Inline deck context into feedback requests (problem #5).
    _inlineFeedbackContext(requests) {
      const deck = readJson(this.config.deckFile)
      const ctx = deck && Array.isArray(deck.slides) ? buildDeckContext(deck) : null
      if (!ctx) return requests
      return requests.map((rq) => {
        const out = Object.assign({}, rq)
        if (rq.type === 'question') {
          out.elem_text = ctx.elemText(rq.elem_id)
          out.slide_title = ctx.slideTitle(rq.slide)
        } else if (rq.type === 'area') {
          const ids = Array.isArray(rq.elems) ? rq.elems : []
          out.region_elems = ids.map((id) => ({ id, text: ctx.elemText(id) }))
          out.slide_title = ctx.slideTitle(rq.slide)
        }
        return out
      })
    }

    parseLine(line) {
      const t = line.trim()
      if (!t) return
      try {
        const obj = JSON.parse(t)
        if (obj && obj.frame) { obj.frame.seq = this.frames.length; this.frames.push(obj.frame) }
        else if (obj && obj.result) this.lastResult = obj.result
      } catch { /* engine warnings or partial lines */ }
    }

    async build(request) {
      if (this.building) return { ok: false, hostError: 'busy', result: null }
      const subprocess = this.ctx.get('subprocess')
      if (subprocess === undefined) return { ok: false, hostError: 'subprocess service unavailable', result: null }
      this.frames = []
      this.lastResult = null
      this.building = true
      const req = Object.assign({}, request || {})
      req.stream = true
      delete req.live
      req.frames_out = this.config.framesFile
      const sv = req.survey || {}
      delete req.survey
      // Palette merge is handled by the runner (reads _palette_auto.json);
      // the host no longer injects accent_hex/bg_hex into overrides.
      if (!req.style && sv.style) req.style = sv.style
      let lineBuf = ''
      let stderrTail = ''
      let stdoutLossy = false
      let spillPath = null
      const ac = new AbortController()
      const timer = setTimeout(() => ac.abort(), BUILD_TIMEOUT_MS)
      if (typeof timer.unref === 'function') timer.unref()
      try {
        const proc = subprocess.spawn({
          argv: [this.config.python, '_dsh_ppt_runner.py'],
          cwd: this.config.cwd,
          stdio: {
            stdin: { data: JSON.stringify(req) },
            stdout: { maxBytes: 2 * 1024 * 1024, spill: { maxBytes: 16 * 1024 * 1024 } },
            stderr: { maxBytes: 64 * 1024 },
          },
          graceMs: 3000,
          signal: ac.signal,
        })
        let off = 0
        for (;;) {
          if (proc.collected.stdout) {
            const r = proc.collected.stdout.readFrom(off)
            off = r.nextOffset
            if (r.lossy) stdoutLossy = true
            if (r.spillPath) spillPath = r.spillPath
            if (r.text) {
              const lines = (lineBuf + r.text).split('\n')
              lineBuf = lines.pop() || ''
              for (const l of lines) this.parseLine(l)
            }
          }
          const exited = await Promise.race([
            proc.done.then(() => true),
            new Promise((r) => setTimeout(r, 50)).then(() => false),
          ])
          if (exited) {
            if (proc.collected.stdout) {
              const fin = proc.collected.stdout.readFrom(off)
              if (fin.lossy) stdoutLossy = true
              if (fin.spillPath) spillPath = fin.spillPath
              if (fin.text) this.parseLine(lineBuf + fin.text)
            }
            if (proc.collected.stderr) {
              const se = proc.collected.stderr.readFrom(0)
              stderrTail = (se.text || '').slice(-600)
            }
            const outcome = await proc.done
            if (stdoutLossy && spillPath) {
              // The in-memory tail dropped the head of the stream — the spill
              // file still holds the complete stream (sealed at settlement), so
              // re-parse it to keep every frame and the final result line.
              this.frames = []
              this.lastResult = null
              try {
                const full = readFileSync(spillPath, 'utf-8')
                for (const l of full.split('\n')) this.parseLine(l)
                stdoutLossy = false
              } catch { /* keep the lossy partial results */ }
            }
            if (this.lastResult) this.lastResult.survey = sv
            return { ok: true, hostError: null, exitCode: outcome.exitCode, result: this.lastResult, nFrames: this.frames.length, stderrTail, stdoutLossy: stdoutLossy || undefined }
          }
          if (ac.signal.aborted) {
            proc.terminate()
            try { await proc.done } catch { /* tree already gone */ }
            return { ok: false, hostError: 'build timeout', result: null, nFrames: this.frames.length, stderrTail }
          }
        }
      } catch (e) {
        if (ac.signal.aborted) return { ok: false, hostError: 'build timeout', result: null, nFrames: this.frames.length, stderrTail }
        return { ok: false, hostError: String(e && e.message ? e.message : e), result: null, nFrames: this.frames.length, stderrTail }
      } finally {
        clearTimeout(timer)
        this._afterBuild(req)
        this.building = false
        // Epoch advances only when the build has settled and the frames file
        // has been rewritten, so every completed build is a new epoch for the
        // panel: its since cursor rewinds and re-fetches the fresh frames.
        // (framesFile additionally bumps the epoch when it detects a truncation
        // mid-write, as a belt-and-braces rewind.)
        this.epoch += 1
      }
    }

      async renderSlides(request) {
        const deck = (request && request.deck) || readJson(this.config.deckFile)
        if (!deck) return { ok: false, hostError: 'no deck available — generate one in chat first', result: null, rendered_slides: [] }
        const base = realpathFlexible(this.config.cwd || 'D:/ppt')
        const rawDir = request && request.render_dir ? String(request.render_dir) : ''
        const wanted = rawDir ? (isAbsolute(rawDir) ? resolve(rawDir) : resolve(base, rawDir)) : resolve(base, '_render_vision')
        const wantedReal = realpathFlexible(wanted)
        const renderDir = isPathWithin(wantedReal, base) ? wanted : resolve(base, '_render_vision')
        const res = await this.build(Object.assign({}, deck, { render_png: true, render_dir: renderDir }))
        return {
          ok: !!(res && res.ok),
          result: (res && res.result) || null,
          rendered_slides: (res && res.result && res.result.rendered_slides) || [],
          hostError: (res && res.hostError) || null,
        }
      }

    async framesFile(request) {
      let all = []
      let result = null
      try {
        for (const line of readFileSync(this.config.framesFile, 'utf-8').split('\n')) {
          const t = line.trim()
          if (!t) continue
          try {
            const obj = JSON.parse(t)
            if (obj && obj.frame) { obj.frame.seq = all.length; all.push(obj.frame) }
            else if (obj && obj.result) result = obj.result
          } catch { /* partial */ }
        }
      } catch { /* no file yet */ }
      const since = (request && request.since) ? request.since : 0
      const fileMax = all.length - 1
      let epoch = this.epoch
      let from = since
      if (fileMax < this.framesMaxSeen) {
        // The frames file was truncated since the last read — a fresh build is
        // writing it, so treat it as a new build (epoch bump) and rewind to 0.
        epoch = ++this.epoch
        this.framesMaxSeen = -1
        from = 0
      }
      this.framesMaxSeen = Math.max(this.framesMaxSeen, fileMax)
      if (from > fileMax + 1) from = fileMax + 1
      // The runner result on disk has no summary; overlay the host-computed one
      // so the panel's done-status can render it (client already reads it).
      let resultOut = result
      if (result && this.lastResult && typeof this.lastResult.summary === 'string') {
        resultOut = Object.assign({}, result, { summary: this.lastResult.summary })
      }
      return { ok: true, hostError: null, frames: all.slice(from), building: result === null && all.length > 0, result: resultOut, epoch }
    }

    // Preview-state RPC for the PNG-based panel: latest rendered slides
    // (from cwd/_render_vision) plus per-slide element geometry parsed from
    // the frames file (frames remain the geometry source; PNGs are the visuals).
    async previewState() {
      const dir = join(this.config.cwd, '_render_vision')
      const rendered = []
      try {
        for (const name of readdirSync(dir)) {
          const m = /^slide_(\d+)\.png$/.exec(name)
          if (!m) continue
          try {
            const st = statSync(join(dir, name))
            rendered.push({ slide: Number(m[1]), file: join(dir, name), mtime: st.mtimeMs })
          } catch { /* skip */ }
        }
      } catch { /* render dir not created yet */ }
      rendered.sort((a, b) => a.slide - b.slide)
      const latest = new Map()
      for (const f of readFramesFile(this.config.framesFile)) {
        if (!f.elem_id) continue
        const key = f.slide + ':' + f.elem_id
        if (!latest.has(key) || f.seq > latest.get(key).seq) latest.set(key, f)
      }
      const elements = {}
      for (const f of latest.values()) {
        if (!elements[f.slide]) elements[f.slide] = []
        elements[f.slide].push({
          elem_id: f.elem_id,
          x: f.x, y: f.y, w: f.w, h: f.h,
          text: f.text ? String(f.text).replace(/\s+/g, ' ').slice(0, 30) : '',
        })
      }
      return { ok: true, hostError: null, epoch: this.epoch, building: this.building, rendered, elements }
    }

    // One rendered slide as base64 data (PNG browser loads per-page images).
    async slideImage(request) {
      const slide = request && typeof request.slide === 'number' ? request.slide : 0
      const file = join(this.config.cwd, '_render_vision', `slide_${String(slide).padStart(2, '0')}.png`)
      try {
        const data = readFileSync(file)
        return { ok: true, hostError: null, slide, mtime: statSync(file).mtimeMs, data: data.toString('base64') }
      } catch {
        return { ok: false, hostError: 'slide image not found: ' + file, slide, data: null }
      }
    }

    async applyFeedbackBuild(request) {
      const requests = (request && request.requests) || []
      if (!Array.isArray(requests)) return { ok: false, hostError: 'requests must be an array', result: null }
      const deck = readJson(this.config.deckFile)
      if (!deck) return { ok: false, hostError: 'no auto deck — let the agent generate one in chat first', result: null }
      for (const rq of requests) {
        if (rq.type !== 'color') continue
        const rgb = hexToRgb(rq.color_hex)
        if (!rgb) continue
        for (const s of deck.slides || []) {
          for (const e of s.elements || []) {
            if (e.id === rq.elem_id) e.fill_color = rgb
          }
        }
      }
      writeJson(this.config.deckFile, deck)
      this._markWatchSelfWrite()
      writeJson(this.config.feedbackFile, { requests, deck })
      return this.build(Object.assign({}, deck, { frames_out: this.config.framesFile, strict_tokens: false }))
    }

    async savePalette(request) {
      writeJson(this.config.paletteFile, (request && request.palette) || { accent_hex: '', bg_hex: '', swatches: [] })
      return { ok: true, hostError: null, result: null }
    }

    async loadPalette() {
      return { ok: true, hostError: null, result: null, palette: readJson(this.config.paletteFile, { accent_hex: '', bg_hex: '', swatches: [] }) }
    }

    async saveFeedback(request) {
      const raw = (request && request.requests) || []
      const requests = Array.isArray(raw) ? this._inlineFeedbackContext(raw) : raw
      writeJson(this.config.feedbackFile, { requests })
      return { ok: true, hostError: null, result: null }
    }

    async saveSelection(request) {
      const req = (request && typeof request === 'object' && !Array.isArray(request)) ? Object.assign({}, request) : {}
      const deck = readJson(this.config.deckFile)
      const ctx = deck && Array.isArray(deck.slides) ? buildDeckContext(deck) : null
      if (ctx) {
        if (req.elem_id !== undefined && req.elem_id !== null) req.elem_text = ctx.elemText(req.elem_id)
        if (Array.isArray(req.elems)) req.region_elems = req.elems.map((id) => ({ id, text: ctx.elemText(id) }))
        if (req.slide !== undefined && req.slide !== null) req.slide_title = ctx.slideTitle(req.slide)
      }
      writeJson(this.config.selectionFile, req)
      return { ok: true, hostError: null, result: null }
    }

    async loadDeck() {
      const deck = readJson(this.config.deckFile)
      if (deck) { delete deck.live; return { ok: true, hostError: null, result: null, deck, source: 'auto' } }
      const sample = readJson(this.config.cwd.replace(/\\/g, '/') + '/_deck_whitecollar_v2.json')
      if (sample) { delete sample.live; return { ok: true, hostError: null, result: null, deck: sample, source: 'sample' } }
      return { ok: false, hostError: 'no deck available', result: null }
    }
  }
})()

// ---- Agent tool (ppt_build) ----
// The loader unwraps the module's default export as the plugin entry: an
// { apply } object here (dsh-tool-bash-persistent convention) replaces the
// old loader auto-instantiation of the default-exported Service class, so
// apply() re-registers the gateway the same way (`new SlideReflexGateway(ctx)`
// provides ctx.slideReflex + the deck watcher) and adds the agent-facing tool.

function readFramesFile(path) {
  const frames = []
  try {
    for (const line of readFileSync(path, 'utf-8').split('\n')) {
      const t = line.trim()
      if (!t) continue
      try {
        const obj = JSON.parse(t)
        if (obj && obj.frame) { obj.frame.seq = frames.length; frames.push(obj.frame) }
      } catch { /* partial */ }
    }
  } catch { /* no file yet */ }
  return frames
}

// Geometry diagnostics over the deck structure plus the last rendered frames:
// per-slide element inventory, out-of-bounds frames, and pairwise overlaps.
function inspectDeck(deck, frames, slide, elemIds) {
  const slides = (deck && Array.isArray(deck.slides)) ? deck.slides : []
  const pageW = (deck && typeof deck.page_w === 'number') ? deck.page_w : 960
  const pageH = (deck && typeof deck.page_h === 'number') ? deck.page_h : 540
  const wantSlide = (typeof slide === 'number') ? slide : null
  const only = (elemIds && Array.isArray(elemIds) && elemIds.length) ? new Set(elemIds.map(String)) : null
  const issues = []
  const perSlide = []
  for (let i = 0; i < slides.length; i++) {
    if (wantSlide !== null && i !== wantSlide) continue
    const s = slides[i] || {}
    const elems = Array.isArray(s.elements) ? s.elements : []
    const rows = []
    for (const e of elems) {
      if (only && !only.has(String(e.id))) continue
      rows.push({
        id: e.id,
        type: e.type || null,
        recipe: e.recipe || null,
        text: e.text !== undefined ? String(e.text).replace(/\s+/g, ' ').trim().slice(0, 80) : null,
      })
    }
    const geom = []
    if (Array.isArray(frames)) {
      const seen = new Map()
      for (const f of frames) {
        if (f.slide !== i || !f.elem_id) continue
        if (only && !only.has(String(f.elem_id))) continue
        const prev = seen.get(f.elem_id)
        if (!prev || (f.seq || 0) > (prev.seq || 0)) seen.set(f.elem_id, f)
      }
      for (const f of seen.values()) {
        const x = f.x || 0, y = f.y || 0, w = f.w || 0, h = f.h || 0
        geom.push({ elem_id: f.elem_id, x, y, w, h, text: f.text ? String(f.text).replace(/\s+/g, ' ').trim().slice(0, 60) : null })
        if (x < 0 || y < 0 || x + w > pageW || y + h > pageH) {
          issues.push('第 ' + (i + 1) + ' 页元素 ' + f.elem_id + ' 超出页面边界 (x=' + x + ',y=' + y + ',w=' + w + ',h=' + h + ', 页 ' + pageW + '×' + pageH + ')')
        }
      }
      for (let a = 0; a < geom.length; a++) {
        for (let b = a + 1; b < geom.length; b++) {
          const A = geom[a], B = geom[b]
          if (A.x < B.x + B.w && A.x + A.w > B.x && A.y < B.y + B.h && A.y + A.h > B.y) {
            issues.push('第 ' + (i + 1) + ' 页元素 ' + A.elem_id + ' 与 ' + B.elem_id + ' 重叠')
          }
        }
      }
    }
    perSlide.push({ slide: i, archetype: s.archetype || null, title: s.title || null, elements: rows, geometry: geom })
  }
  return { page: { width: pageW, height: pageH }, slide_count: slides.length, slides: perSlide, issues: issues.slice(0, 30), issue_count: issues.length }
}

function renderToolResult(value) {
  const out = []
  out.push(value && value.ok ? 'ok: true' : 'ok: false')
  if (value && value.hostError) out.push('hostError: ' + String(value.hostError))
  if (value && value.result !== undefined && value.result !== null) {
    const json = JSON.stringify(value.result, null, 2)
    out.push('result: ' + (json.length > 6000 ? json.slice(0, 6000) + '\n…(truncated)' : json))
  }
  if (value && Array.isArray(value.rendered_slides)) {
    out.push('rendered_slides: ' + value.rendered_slides.map((s) => (s && s.file) || s).join(', '))
  }
  if (value && value.nFrames !== undefined) out.push('nFrames: ' + value.nFrames)
  return out.join('\n')
}

const name = 'dsh-slide-reflex'
const inject = ['tools']
const Config = z.object({})

function registerPptBuildTool(ctx, gw) {
  ctx.tools.register(defineTool({
    name: 'ppt_build',
    description: '构建 / 渲染 / 检查 PPT deck（Build, render, or inspect the PPT deck）。仅 PPT 制作会话使用：只供 ppt-maker 预设会话中的 Agent 调用，其他会话请勿使用。' +
      'build：把 deck 交给引擎生成帧，不传 deck 则读取 _deck_auto.json（等价于 Agent 只写 deck 文件自动构建）；' +
      'renderSlides：渲染每页 PNG 到 _render_vision；' +
      'inspect：按 slide / elem_ids 对 deck 与上次渲染帧做几何诊断（越界、重叠、文本缺失）。' +
      '始终返回 { ok, result, hostError }。',
    parameters: {
      action: {
        type: 'string',
        required: true,
        enum: ['build', 'renderSlides', 'inspect'],
        description: '要执行的动作：build（构建帧）/ renderSlides（渲染 PNG）/ inspect（几何诊断）',
      },
      deck: {
        type: 'object',
        additionalProperties: true,
        description: '完整 deck JSON（可选）；缺省读取当前 _deck_auto.json',
      },
      slide: {
        type: 'integer',
        description: '目标页索引（0 起，可选；inspect 用，缺省检查全部页）',
      },
      elem_ids: {
        type: 'array',
        items: { type: 'string' },
        description: '只诊断这些元素 id（可选；inspect 用）',
      },
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: true,
        properties: {
          ok: { type: 'boolean' },
          result: { type: 'json' },
          hostError: { oneOf: [{ type: 'string' }, { type: 'null' }] },
        },
      },
      render: (_args, value) => [{ type: 'text', text: renderToolResult(value) }],
    },
    async execute(args) {
      try {
        const deck = (args && typeof args.deck === 'object' && args.deck !== null) ? args.deck : readJson(gw.config.deckFile)
        if (args.action === 'build') {
          if (!deck) return { ok: false, result: null, hostError: 'no deck available — let the agent generate one in chat first' }
          const res = await gw.build(deck)
          return { ok: !!(res && res.ok), result: (res && res.result) || null, hostError: (res && res.hostError) || null, nFrames: (res && res.nFrames) || 0 }
        }
        if (args.action === 'renderSlides') {
          if (!deck) return { ok: false, result: null, hostError: 'no deck available — let the agent generate one in chat first' }
          const res = await gw.renderSlides({ deck })
          return { ok: !!(res && res.ok), result: (res && res.result) || null, hostError: (res && res.hostError) || null, rendered_slides: (res && res.rendered_slides) || [] }
        }
        if (args.action === 'inspect') {
          const frames = readFramesFile(gw.config.framesFile)
          return { ok: true, result: inspectDeck(deck, frames, args && args.slide, args && args.elem_ids), hostError: null }
        }
        return { ok: false, result: null, hostError: 'ppt_build: unknown action "' + String(args && args.action) + '"' }
      } catch (e) {
        return { ok: false, result: null, hostError: String(e && e.message ? e.message : e) }
      }
    },
  }))
}

function apply(ctx) {
  // Re-register the gateway the way the loader used to (auto-instantiation of
  // the default-exported Service class): provides ctx.slideReflex + watcher.
  // The instance is captured once per apply and reused by the tool; do not
  // read ctx.slideReflex here — on a live plugin fiber an un-injected read
  // throws before the service is provided.
  const gw = new SlideReflexGateway(ctx)
  registerPptBuildTool(ctx, gw)
}

export { SlideReflexGateway, Config, apply, inject, name }
export default { Config, apply, inject, name }
