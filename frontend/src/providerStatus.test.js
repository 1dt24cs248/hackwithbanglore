import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import { hindsightBankLabel } from './providerStatus.js'

test('Memory Explorer bank label uses the backend reported bank ID', () => {
  assert.equal(
    hindsightBankLabel({ dependencies: { hindsight: { bank_id: 'incidentiq-hackathon-demo' } } }),
    'incidentiq-hackathon-demo bank',
  )
})

test('Memory Explorer shows a safe unavailable label before backend status loads', () => {
  assert.equal(hindsightBankLabel(null), 'Hindsight bank unavailable')
})

test('Memory Explorer is wired to the backend health payload', () => {
  const appSource = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8')
  assert.match(appSource, /<MemoryPage[^>]*health=\{health\}/)
  assert.match(appSource, /hindsightBankLabel\(health\)/)
})

test('Postmortem Page is wired and supports generation and download', () => {
  const appSource = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8')
  assert.match(appSource, /<PostmortemPage[^>]*incidents=\{incidents\}/)
  assert.match(appSource, /\/incidents\/\$\{incidentId\}\/postmortem/)
  assert.match(appSource, /\/postmortems/)
  assert.match(appSource, /ENGINEER-VERIFIED INCIDENT RECORD/)
  assert.match(appSource, /AUDIT REFERENCE ONLY/)
})

