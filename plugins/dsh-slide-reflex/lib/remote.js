// Client-side Remote contribution for dsh-slide-reflex, hand-written to mirror
// the descriptor shape the Typert generator emits into a typert.remote-client
// artifact. The browser half mounts it through ctx.remote.$mount.
import { z } from 'zod'

const PACKAGE = 'dsh-slide-reflex'
const SERVICE = 'slideReflex'
const anySchema = z.any()
const oneArg = () => [{
  name: 'request',
  wire: 'request',
  source: 'json',
  codec: { mode: 'strict', typeSymbol: 'json', schema: anySchema },
}]
const result = () => ({ mode: 'strict', typeSymbol: 'json', schema: anySchema })
const loc = { file: 'lib/index.js', line: 1, column: 1 }

const METHODS_WITH_ARG = ['build', 'framesFile', 'applyFeedbackBuild', 'savePalette', 'saveFeedback', 'saveSelection', 'renderSlides']
const METHODS_NO_ARG = ['loadPalette', 'loadDeck']

export const TYPERT_REMOTE = {
  package: PACKAGE,
  descriptors: [
    ...METHODS_WITH_ARG.map((m) => ({
      id: `${PACKAGE}#${SERVICE}/${m}`,
      service: SERVICE,
      namespace: SERVICE,
      method: m,
      invocation: { kind: 'direct' },
      parameters: oneArg(),
      result: result(),
      sourceLocation: loc,
    })),
    ...METHODS_NO_ARG.map((m) => ({
      id: `${PACKAGE}#${SERVICE}/${m}`,
      service: SERVICE,
      namespace: SERVICE,
      method: m,
      invocation: { kind: 'direct' },
      parameters: [],
      result: result(),
      sourceLocation: loc,
    })),
  ],
}
export default TYPERT_REMOTE
