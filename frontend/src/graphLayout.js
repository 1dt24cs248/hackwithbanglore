const ROW_HEIGHT = 34
const TOP_PADDING = 18

export function layoutIncidentGraph(graph) {
  const patterns = (graph?.nodes || []).filter((node) => node.node_type === 'pattern')
  const incidents = (graph?.nodes || []).filter((node) => node.node_type === 'incident')
  const patternIndex = new Map(patterns.map((node, index) => [node.id, index]))
  const firstPattern = new Map()
  for (const edge of graph?.edges || []) {
    const order = patternIndex.get(edge.target)
    if (order === undefined) continue
    firstPattern.set(edge.source, Math.min(firstPattern.get(edge.source) ?? Infinity, order))
  }
  incidents.sort((left, right) =>
    (firstPattern.get(left.id) ?? Infinity) - (firstPattern.get(right.id) ?? Infinity)
    || left.title.localeCompare(right.title)
    || left.id.localeCompare(right.id),
  )

  const rowCount = Math.max(patterns.length, incidents.length, 1)
  const height = TOP_PADDING * 2 + rowCount * ROW_HEIGHT
  const width = 800
  const placedPatterns = patterns.map((node, index) => ({
    ...node, x: 155, y: TOP_PADDING + index * ROW_HEIGHT + ROW_HEIGHT / 2,
    width: 270, height: 26,
  }))
  const placedIncidents = incidents.map((node, index) => ({
    ...node, x: 600, y: TOP_PADDING + index * ROW_HEIGHT + ROW_HEIGHT / 2,
    width: 370, height: 26,
  }))
  const nodeById = new Map([...placedPatterns, ...placedIncidents].map((node) => [node.id, node]))
  const edges = (graph?.edges || []).flatMap((edge) => {
    const source = nodeById.get(edge.source)
    const target = nodeById.get(edge.target)
    return source && target ? [{ ...edge, x1: source.x, y1: source.y, x2: target.x, y2: target.y }] : []
  })

  return { width, height, nodes: [...placedPatterns, ...placedIncidents], edges }
}
