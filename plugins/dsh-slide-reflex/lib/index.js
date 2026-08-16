// dsh-slide-reflex — Host half: Typert Remote gateway bridging the
// ppt-reflex python runner and the Client preview panel. Decorators are
// expanded by hand (the runtime does not enable decorator syntax); this
// mirrors exactly what the typert generator emits.
import { readFileSync, writeFileSync } from 'node:fs'
import { isAbsolute, resolve } from 'node:path'
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

function readJson(path, fallback = null) {
  try { return JSON.parse(readFileSync(path, 'utf-8')) } catch { return fallback }
}

function writeJson(path, value) {
  try { writeFileSync(path, JSON.stringify(value), 'utf-8') } catch { /* ignore */ }
}

function hexToRgb(hex) {
  const h = String(hex || '').replace('#', '')
  if (!/^[0-9a-fA-F]{6}$/.test(h)) return null
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]
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
      this.config = DEFAULTS
      try {
        for (const entry of ctx.get('loader')?.entries() ?? []) {
          if (entry.id === 'dsh-slide-reflex' && entry.options?.config) {
            this.config = { ...DEFAULTS, ...entry.options.config }
          }
        }
      } catch { /* keep defaults */ }
      this.frames = []
      this.building = false
      this.lastResult = null
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
      const subprocess = this.ctx.get('subprocess')
      if (subprocess === undefined) return { ok: false, hostError: 'subprocess service unavailable' }
      this.frames = []
      this.lastResult = null
      this.building = true
      const req = Object.assign({}, request || {})
      req.stream = true
      delete req.live
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
        })
        let off = 0
        for (;;) {
          if (proc.collected.stdout) {
            const r = proc.collected.stdout.readFrom(off)
            off = r.nextOffset
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
              if (fin.text) this.parseLine(lineBuf + fin.text)
            }
            if (proc.collected.stderr) {
              const se = proc.collected.stderr.readFrom(0)
              stderrTail = (se.text || '').slice(-600)
            }
            const outcome = await proc.done
            if (this.lastResult) this.lastResult.survey = sv
            return { ok: true, exitCode: outcome.exitCode, result: this.lastResult, nFrames: this.frames.length, stderrTail }
          }
        }
      } catch (e) {
        return { ok: false, hostError: String(e && e.message ? e.message : e), nFrames: this.frames.length, stderrTail }
      } finally {
        this.building = false
      }
    }

      async renderSlides(request) {
        const deck = (request && request.deck) || readJson(this.config.deckFile)
        if (!deck) return { ok: false, error: 'no deck available — generate one in chat first' }
        const base = resolve(this.config.cwd || 'D:/ppt')
        const rawDir = request && request.render_dir ? String(request.render_dir) : ''
        const wanted = rawDir ? (isAbsolute(rawDir) ? resolve(rawDir) : resolve(base, rawDir)) : resolve(base, '_render_vision')
        const renderDir = wanted === base || wanted.startsWith(base + (process.platform === 'win32' ? '\\' : '/'))
          ? wanted
          : resolve(base, '_render_vision')
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
      return { frames: all.slice(request && request.since ? request.since : 0), building: result === null && all.length > 0, result }
    }

    async applyFeedbackBuild(request) {
      const requests = (request && request.requests) || []
      const deck = readJson(this.config.deckFile)
      if (!deck) return { error: 'no auto deck — let the agent generate one in chat first' }
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
      return { ok: true }
    }

    async loadPalette() {
      return { palette: readJson(this.config.paletteFile, { accent_hex: '', bg_hex: '', swatches: [] }) }
    }

    async saveFeedback(request) {
      writeJson(this.config.feedbackFile, { requests: (request && request.requests) || [] })
      return { ok: true }
    }

    async saveSelection(request) {
      writeJson(this.config.selectionFile, request || {})
      return { ok: true }
    }

    async loadDeck() {
      const deck = readJson(this.config.deckFile)
      if (deck) { delete deck.live; return { deck, source: 'auto' } }
      const sample = readJson(this.config.cwd.replace(/\\/g, '/') + '/_deck_whitecollar_v2.json')
      if (sample) { delete sample.live; return { deck: sample, source: 'sample' } }
      return { error: 'no deck available' }
    }
  }
})()

export { SlideReflexGateway, SlideReflexGateway as default }
