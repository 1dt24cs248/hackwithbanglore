import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import { hindsightBankLabel } from './providerStatus.js'
import { createPostmortemMarkdownBlob, parseInlineMarkdown, parsePostmortemMarkdown } from './postmortemMarkdown.js'

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

test('Routine data refresh avoids provider health checks and guided progress uses persisted runs', () => {
  const appSource = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8')
  const reloadBody = appSource.match(/const reload = useCallback\(async \(\) => \{([\s\S]*?)\n  \}, \[\]\)/)
  assert.ok(reloadBody, 'routine data reload callback exists')
  assert.doesNotMatch(reloadBody[1], /api\(['"]\/health['"]\)/)
  assert.match(appSource, /loadedDetail\.investigation_runs/)
  assert.match(appSource, /run\.execution_status === 'succeeded'/)
  assert.match(appSource, /onRefreshHealth=\{refreshHealth\}/)
})

test('IncidentIQ uses persisted learning prerequisites and only functional identity/navigation controls', () => {
  const appSource = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8')
  assert.match(appSource, /restorePersistedDemoProgress/)
  assert.match(appSource, /historical\.memory_retention_status/)
  assert.match(appSource, /onClick=\{\(\) => \{ setPage\('investigate'\)/)
  assert.doesNotMatch(appSource, /Northstar Systems|SRE Engineering/)
  assert.match(appSource, /error\.category = body\?\.detail\?\.error_category/)
  assert.match(appSource, /<details className="evidence-disclosure">/)
  assert.match(appSource, /<details className="hypothesis-disclosure"/)
})

test('Postmortem Page is wired and supports generation and download', () => {
  const appSource = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8')
  assert.match(appSource, /<PostmortemPage[^>]*incidents=\{incidents\}/)
  assert.match(appSource, /\/incidents\/\$\{incidentId\}\/postmortem/)
  assert.match(appSource, /\/postmortems/)
  assert.match(appSource, /ENGINEER-VERIFIED INCIDENT RECORD/)
  assert.match(appSource, /AUDIT REFERENCE ONLY/)
  assert.match(appSource, /parsePostmortemMarkdown\(content\)/)
  assert.match(appSource, /createPostmortemMarkdownBlob\(pm\.body_markdown\)/)
})

test('Postmortem Markdown preview parses headings, emphasis, code, lists, quotes, and rules', () => {
  const markdown = [
    '# Incident report',
    '',
    '**Incident Reference:** `INC-20261107-9952BCA4`',
    '',
    '- **Service:** `payment-api`',
    '- plain item',
    '',
    '> **AUDIT REFERENCE ONLY**',
    '> Hypothesis, not verified.',
    '',
    '---',
  ].join('\n')
  const blocks = parsePostmortemMarkdown(markdown)

  assert.deepEqual(blocks.map((block) => block.type), [
    'heading', 'paragraph', 'unorderedList', 'quote', 'rule',
  ])
  assert.deepEqual(blocks[1].children.map((token) => token.type), ['strong', 'text', 'code'])
  assert.equal(blocks[1].children[0].children[0].value, 'Incident Reference:')
  assert.equal(blocks[1].children[2].value, 'INC-20261107-9952BCA4')
  assert.equal(blocks[2].items.length, 2)
  assert.equal(blocks[3].children[0][0].type, 'strong')
})

test('Postmortem Markdown download preserves valid source syntax unchanged', async () => {
  const markdown = '# Incident report\n\n**Incident Reference:** `INC-1`\n\n- **Service:** `api`\n\n> verified\n\n---\n'
  const blob = createPostmortemMarkdownBlob(markdown)

  assert.equal(blob.type, 'text/markdown;charset=utf-8')
  assert.equal(await blob.text(), markdown)
  assert.deepEqual(parseInlineMarkdown('**label** `value`').map((token) => token.type), ['strong', 'text', 'code'])
})

