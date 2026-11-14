import { useEffect, useState } from 'react'
import { AlertCircle, BookOpen, ExternalLink, LoaderCircle, RefreshCw, ShieldCheck } from 'lucide-react'

const TABS = [
  { id: 'verified_workspace', label: 'Verified in Your Workspace' },
  { id: 'public_library', label: 'Public Incident Library' },
]

function dateLabel(value) {
  if (!value) return 'Date not recorded'
  const date = new Date(`${String(value).slice(0, 10)}T00:00:00Z`)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { timeZone: 'UTC' })
}

function timestampLabel(value) {
  if (!value) return 'Not recorded'
  const timestamp = new Date(value)
  return Number.isNaN(timestamp.getTime()) ? value : timestamp.toLocaleString()
}

function ActionList({ title, items }) {
  if (!items?.length) return null
  return <div className="precedent-field"><strong>{title}</strong><ul>{items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></div>
}

function Relevance({ score }) {
  return <div className="precedent-relevance" aria-label={`Lexical relevance ${score} percent`}>
    <span>Lexical relevance</span><strong>{score}%</strong>
    <div className="precedent-meter"><i style={{ width: `${Math.max(0, Math.min(100, score))}%` }} /></div>
  </div>
}

function WorkspaceCard({ item }) {
  return <article className="precedent-card">
    <div className="precedent-card-head"><div><span className="precedent-overline"><ShieldCheck size={12} /> VERIFIED WORKSPACE RECORD</span><h3>{item.title}</h3><small>{item.incident_number} · Verified {timestampLabel(item.verified_at)}</small></div><Relevance score={item.relevance_score} /></div>
    <div className="precedent-signal-list" aria-label="Matching technical signals">{item.matching_signals.map((signal) => <span key={signal}>{signal.replaceAll('_', ' ')}</span>)}</div>
    <details className="precedent-details"><summary>View verified experience</summary>
      <div className="precedent-field"><strong>Verified root cause</strong><p>{item.verified_root_cause}</p></div>
      <div className="precedent-field"><strong>Verified resolution</strong><p>{item.verified_resolution}</p></div>
      <div className="precedent-meta"><span>Verification status: {item.verification_status}</span>{item.memory_retention_status && <span>Memory retention: {item.memory_retention_status}</span>}</div>
    </details>
  </article>
}

function PublicCard({ item }) {
  return <article className="precedent-card">
    <div className="precedent-card-head"><div><span className="precedent-overline"><BookOpen size={12} /> PUBLIC HISTORICAL PRECEDENT</span><h3>{item.title}</h3><small>{item.company} · {dateLabel(item.incident_date)} · {item.category}</small></div><Relevance score={item.relevance_score} /></div>
    <div className="precedent-signal-list" aria-label="Matching technical signals">{item.matching_signals.map((signal) => <span key={signal}>{signal.replaceAll('_', ' ')}</span>)}</div>
    <details className="precedent-details"><summary>View documented incident details</summary>
      <div className="precedent-field"><strong>Published root cause</strong><p>{item.technical_root_cause || 'Not disclosed in the source.'}</p></div>
      <ActionList title="Recovery actions" items={item.recovery_actions} />
      <ActionList title="Preventive actions" items={item.preventive_actions} />
      {item.source_url && <a className="precedent-source-link" href={item.source_url} target="_blank" rel="noreferrer">Open official source <ExternalLink size={13} /></a>}
    </details>
  </article>
}

export default function PrecedentRadar({ incidentId, requestApi }) {
  const [activeTab, setActiveTab] = useState('verified_workspace')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!incidentId) return undefined
    let active = true
    setLoading(true)
    setError('')
    requestApi(`/incidents/${encodeURIComponent(incidentId)}/precedents?limit=5`)
      .then((result) => { if (active) setData(result) })
      .catch((reason) => { if (active) setError(reason.message || 'Could not load precedents.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [incidentId, requestApi, attempt])

  const items = data?.[activeTab] || []
  return <section className="panel precedent-radar" aria-labelledby="precedent-radar-title">
    <div className="panel-heading"><div><div className="section-kicker">PRECEDENT RADAR</div><h2 id="precedent-radar-title">Historical matches</h2><p>Similar incidents are precedents, not confirmed diagnoses.</p></div><BookOpen size={17} className="heading-accent" /></div>
    <div className="precedent-tabs" role="tablist" aria-label="Precedent knowledge tier">
      {TABS.map((tab) => <button key={tab.id} type="button" role="tab" aria-selected={activeTab === tab.id} className={activeTab === tab.id ? 'active' : ''} onClick={() => setActiveTab(tab.id)}>{tab.label}</button>)}
    </div>
    {data?.score_method && <p className="precedent-score-note">{data.score_method}</p>}
    {loading && <div className="precedent-state" role="status"><LoaderCircle className="spin" size={16} /> Finding historical precedents…</div>}
    {!loading && error && <div className="precedent-state precedent-error" role="alert"><AlertCircle size={16} /><span>{error}</span><button type="button" className="button button-secondary button-small" onClick={() => setAttempt((value) => value + 1)}><RefreshCw size={13} /> Retry</button></div>}
    {!loading && !error && items.length === 0 && <div className="precedent-state">No matching {activeTab === 'verified_workspace' ? 'verified workspace records' : 'public incidents'} found for this evidence.</div>}
    {!loading && !error && items.length > 0 && <div className="precedent-list">{items.map((item) => activeTab === 'verified_workspace' ? <WorkspaceCard key={item.id} item={item} /> : <PublicCard key={item.id} item={item} />)}</div>}
    <div className="precedent-disclaimer"><ShieldCheck size={13} /> Ranking uses lexical TF-IDF similarity and matching signals; it does not establish a shared root cause.</div>
  </section>
}
