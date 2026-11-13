import test from 'node:test'
import assert from 'node:assert/strict'
import { queryString } from './libraryFilters.js'

test('library query encodes active filters and always requests a bounded page', () => {
  const query = new URLSearchParams(queryString({ search: 'GitHub ProxySQL', company: 'GitHub', category: '', year: '2020', severity: '', service: 'Database', incident_type: '', verification_status: 'verified' }, 2))
  assert.equal(query.get('page'), '2')
  assert.equal(query.get('limit'), '12')
  assert.equal(query.get('search'), 'GitHub ProxySQL')
  assert.equal(query.get('company'), 'GitHub')
  assert.equal(query.get('year'), '2020')
  assert.equal(query.get('service'), 'Database')
  assert.equal(query.get('verification_status'), 'verified')
  assert.equal(query.has('category'), false)
})
