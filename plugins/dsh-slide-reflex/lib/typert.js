// Host-face Typert manifest for dsh-slide-reflex, hand-written to mirror the
// shape the typert generator emits. The typert loader imports the ./typert
// export and registers these invocations, enabling schema-validated dispatch
// at the API gateway and the Client remote namespace.
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

const METHODS_WITH_ARG = ['build', 'framesFile', 'applyFeedbackBuild', 'savePalette', 'saveFeedback', 'saveSelection', 'renderSlides', 'slideImage']
const METHODS_NO_ARG = ['loadPalette', 'loadDeck', 'previewState']

export const TYPERT = {
  package: PACKAGE,
  face: 'host',
  schemas: [],
  invocations: [
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
  model: {
    services: [],
    events: [],
    objects: [],
  },
}
export default TYPERT
