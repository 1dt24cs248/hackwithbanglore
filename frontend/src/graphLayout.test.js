import assert from 'node:assert/strict'
import test from 'node:test'
import { layoutIncidentGraph } from './graphLayout.js'

test('relationship graph layout keeps nodes in viewBox and edge endpoints on node centers', () => {
  const graph = {
    nodes: [
      { id: 'cat:network', node_type: 'pattern', label: 'Network outages' },
      { id: 'inc:b', node_type: 'incident', title: 'B outage' },
      { id: 'inc:a', node_type: 'incident', title: 'A outage' },
    ],
    edges: [
      { source: 'inc:a', target: 'cat:network' },
      { source: 'inc:b', target: 'cat:network' },
    ],
  }
  const layout = layoutIncidentGraph(graph)
  const byId = new Map(layout.nodes.map((node) => [node.id, node]))
  for (const node of layout.nodes) {
    assert.ok(node.x - node.width / 2 >= 0)
    assert.ok(node.x + node.width / 2 <= layout.width)
    assert.ok(node.y - node.height / 2 >= 0)
    assert.ok(node.y + node.height / 2 <= layout.height)
  }
  for (const edge of layout.edges) {
    assert.equal(edge.x1, byId.get(edge.source).x)
    assert.equal(edge.y1, byId.get(edge.source).y)
    assert.equal(edge.x2, byId.get(edge.target).x)
    assert.equal(edge.y2, byId.get(edge.target).y)
  }
  assert.deepEqual(layout.nodes.filter((node) => node.node_type === 'incident').map((node) => node.id), ['inc:a', 'inc:b'])
})
