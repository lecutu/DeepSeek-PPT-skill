// dsh-slide-reflex — Host half: Typert Remote gateway bridging the
// ppt-reflex python runner and the Client preview panel. Decorators are
// expanded by hand (the runtime does not enable decorator syntax); this
// mirrors exactly what the typert generator emits.
import { readFileSync, writeFileSync, renameSync, unlinkSync, realpathSync, existsSync, statSync } from 'node:fs'
import { isAbsolute, resolve, dirname, basename, sep } from 'node:path'
import { Remote, TypertRemoteService } from '@deepseek-ai/dsh-typert-protocol'

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
      this.epoch += 1
      const req = Object.assign({}, request || {})
      req.stream = true
      delete req.live
      req.frames_out = this.config.framesFile
      const sv = req.survey || {}
      delete req.survey
      const palette = readJson(this.config.paletteFile)
      if (palette && palette.accent_hex) sv.accent_hex = sv.accent_hex || palette.accent_hex
      if (palette && palette.bg_hex) sv.bg_hex = sv.bg_hex || palette.bg_hex
      if (!req.style && sv.style) req.style = sv.style
      const ov = {}
      if (sv.accent_hex) ov.accent_hex = sv.accent_hex
      if (sv.bg_hex) ov.bg_hex = sv.bg_hex
      if (Object.keys(ov).length) req.overrides = Object.assign({}, req.overrides || {}, ov)
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
            this.ctx.timeout(50).then(() => false),
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
        this.building = false
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
      return { ok: true, hostError: null, frames: all.slice(from), building: result === null && all.length > 0, result, epoch }
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
      writeJson(this.config.feedbackFile, { requests: (request && request.requests) || [] })
      return { ok: true, hostError: null, result: null }
    }

    async saveSelection(request) {
      writeJson(this.config.selectionFile, request || {})
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

export { SlideReflexGateway, SlideReflexGateway as default }
