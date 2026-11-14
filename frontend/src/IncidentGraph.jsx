import { useEffect, useMemo, useState } from 'react'
import { AlertCircle, LoaderCircle, RefreshCw, Waypoints } from 'lucide-react'
import { layoutIncidentGraph } from './graphLayout.js'

function shortLabel(value, max = 52) {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value
}

function incidentDate(value) {
  if (!value) return 'Date not recorded'
  const date = new Date(`${String(value).slice(0, 10)}T00:00:00Z`)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { timeZone: 'UTC' })
}

function relationLabel(relation) {
  return relation === 'shared_infrastructure' ? 'Strong' : 'Moderate'
}

function IncidentDetails({ incident, nodesById }) {
  return <>
    <div className="graph-detail-kicker">HISTORICAL INCIDENT</div>
    <h3>{incident.title}</h3>
    <p className="graph-detail-meta">{incident.company} · {incidentDate(incident.incident_date)} · {incident.category}</p>
    <div className="graph-detail-section"><strong>Documented root cause</strong><p>{incident.technical_root_cause || 'Not published in the source.'}</p></div>
    <div className="graph-detail-section"><strong>Why it is connected</strong>
      {incident.relationships.map((relationship) => <div className="graph-reason" key={`${relationship.relation}:${relationship.pattern_label}`}>
        <span className={`graph-relation-badge ${relationship.relation === 'shared_infrastructure' ? 'strong' : 'moderate'}`}>{relationLabel(relationship.relation)}</span>
        <span className="graph-pattern-name">{relationship.pattern_label}</span>
        <p>{relationship.evidence}</p>
        <small>Related incidents: {relationship.related_incident_ids.map((id) => {
          const related = nodesById.get(id)
          return related ? `${related.company} - ${related.title}` : id
        }).join('; ') || 'None listed'}</small>
      </div>)}
    </div>
    {incident.source_url && <a className="graph-source-link" href={incident.source_url} target="_blank" rel="noopener noreferrer">Open official source <span aria-hidden="true">↗</span></a>}
  </>
}

function PatternDetails({ pattern, graph, nodesById, onSelectIncident }) {
  const relatedIds = graph.edges.filter((edge) => edge.target === pattern.id).map((edge) => edge.source)
  return <>
    <div className="graph-detail-kicker">RELATIONSHIP PATTERN</div>
    <h3>{pattern.label}</h3>
    <p className="graph-detail-meta">{relationLabel(pattern.relation)} · {pattern.incident_count} incidents</p>
    <div className="graph-detail-section"><strong>Evidence basis</strong><p>{pattern.evidence_basis === 'documented_infrastructure' ? 'Exact shared component listed in the reports.' : 'Shared library category; this is IncidentIQ classification, not a category asserted by the source reports.'}</p></div>
    <div className="graph-detail-section"><strong>Connected incidents</strong><ul className="graph-related-list">{relatedIds.map((id) => {
      const incident = nodesById.get(id)
      return incident && <li key={id}><button type="button" onClick={() => onSelectIncident(id)}>{incident.company} - {shortLabel(incident.title, 44)}</button></li>
    })}</ul></div>
  </>
}

export default function IncidentGraph({ requestApi }) {
  const [graph, setGraph] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [selection, setSelection] = useState(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    requestApi('/library/relationship-graph?max_patterns=8')
      .then((result) => { if (active) { setGraph(result); setSelection(null) } })
      .catch((reason) => { if (active) setError(reason.message || 'The relationship graph could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [requestApi, attempt])

  const layout = useMemo(() => layoutIncidentGraph(graph), [graph])
  const nodesById = useMemo(() => new Map((graph?.nodes || []).map((node) => [node.id, node])), [graph])
  const edgesByIncident = useMemo(() => {
    const index = new Map()
    for (const edge of graph?.edges || []) {
      if (!index.has(edge.source)) index.set(edge.source, [])
      index.get(edge.source).push(edge.target)
    }
    return index
  }, [graph])
  const highlighted = useMemo(() => {
    if (!selection || !graph) return new Set()
    const ids = new Set([selection.id])
    if (selection.kind === 'incident') for (const patternId of edgesByIncident.get(selection.id) || []) ids.add(patternId)
    else for (const edge of graph.edges) if (edge.target === selection.id) ids.add(edge.source)
    return ids
  }, [selection, graph, edgesByIncident])

  function selectNode(node) { setSelection({ kind: node.node_type, id: node.id }) }
  function activateOnKey(event, node) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      selectNode(node)
    }
  }

  const selectedNode = selection ? nodesById.get(selection.id) : null
  const nodesByIdWithLayout = useMemo(() => new Map(layout.nodes.map((node) => [node.id, node])), [layout])

  return <section className="graph-page">
    <header className="graph-page-heading"><div><div className="page-eyebrow"><span className="eyebrow-line" /> EVIDENCE-BACKED CONNECTIONS</div><h1>Incident Relationship Graph</h1><p>Browse documented infrastructure and library-category links across verified production incidents.</p></div><Waypoints size={22} /></header>
    {loading && <section className="panel graph-state" role="status"><LoaderCircle size={17} className="spin" /> Loading incident relationships…</section>}
    {!loading && error && <section className="panel graph-state graph-error" role="alert"><AlertCircle size={17} /><span>{error}</span><button type="button" className="button button-secondary button-small" onClick={() => setAttempt((value) => value + 1)}><RefreshCw size={13} /> Retry</button></section>}
    {!loading && !error && graph && (graph.edges.length === 0 || layout.nodes.length === 0) && <section className="panel graph-state">No relationships found in the library.</section>}
    {!loading && !error && graph && graph.edges.length > 0 && <>
      <section className="panel graph-legend">
        <div className="graph-legend-items"><span><i className="graph-legend-line solid" /> Shared infrastructure · strong</span><span><i className="graph-legend-line dashed" /> Same library category · moderate</span></div>
        <p>{graph.legend_note}</p><small>{graph.incidents_shown} of {graph.total_library_incidents} incidents shown · {graph.patterns_shown} patterns</small>
      </section>
      <div className="graph-layout">
        <section className="panel graph-canvas-panel" aria-label="Interactive incident relationship graph">
          <div className="graph-column-labels"><span>RELATIONSHIP PATTERNS</span><span>INCIDENTS</span></div>
          <svg className="incident-graph-svg" viewBox={`0 0 ${layout.width} ${layout.height}`} role="group" aria-label="Incident relationship graph">
            {layout.edges.map((edge, index) => {
              const active = selection && (selection.kind === 'incident' ? edge.source === selection.id : edge.target === selection.id)
              const dimmed = selection && !active
              return <line key={`${edge.source}-${edge.target}-${index}`} x1={edge.x1} y1={edge.y1} x2={edge.x2} y2={edge.y2} className={`graph-edge ${edge.relation === 'shared_infrastructure' ? 'graph-edge-strong' : 'graph-edge-moderate'} ${active ? 'is-active' : ''} ${dimmed ? 'is-dimmed' : ''}`} />
            })}
            {layout.nodes.map((node) => {
              const active = highlighted.has(node.id)
              const dimmed = selection && !active
              const label = node.node_type === 'pattern' ? `${node.label} · ${node.incident_count}` : shortLabel(`${node.company} - ${node.title}`)
              return <g key={node.id} className={`graph-node ${node.node_type === 'pattern' ? 'graph-pattern-node' : 'graph-incident-node'} ${selection?.id === node.id ? 'is-selected' : ''} ${active ? 'is-highlighted' : ''} ${dimmed ? 'is-dimmed' : ''}`} role="button" tabIndex={0} aria-pressed={selection?.id === node.id} aria-label={node.node_type === 'pattern' ? `${node.label}, ${node.incident_count} incidents` : `${node.company}: ${node.title}`} onClick={() => selectNode(node)} onKeyDown={(event) => activateOnKey(event, node)}>
                <title>{node.node_type === 'pattern' ? `${node.label} (${node.incident_count} incidents)` : `${node.company} - ${node.title}`}</title>
                <rect x={node.x - node.width / 2} y={node.y - node.height / 2} width={node.width} height={node.height} rx="6" />
                <text x={node.x} y={node.y + 3} textAnchor="middle">{label}</text>
              </g>
            })}
          </svg>
        </section>
        <aside className="panel graph-detail-panel" aria-live="polite">
          {!selectedNode && <div className="graph-detail-empty"><strong>Select a node</strong><p>Choose an incident or pattern to inspect its documented relationships.</p></div>}
          {selectedNode?.node_type === 'incident' && <IncidentDetails incident={selectedNode} nodesById={nodesById} />}
          {selectedNode?.node_type === 'pattern' && <PatternDetails pattern={selectedNode} graph={graph} nodesById={nodesByIdWithLayout} onSelectIncident={(id) => setSelection({ kind: 'incident', id })} />}
        </aside>
      </div>
    </>}
  </section>
}
