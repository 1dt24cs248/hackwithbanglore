import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertCircle, ArrowDownRight, ArrowRight, ArrowUpRight, BrainCircuit,
  Check, CheckCircle2, ChevronDown, ChevronRight, CircleHelp, Clock3, Command,
  Database, Download, ExternalLink, FileText, Fingerprint, Gauge, History, Layers3, LoaderCircle,
  Menu, MessageSquareText, Network, Plus, Radar, RefreshCw, Search, ShieldCheck,
  Sparkles, SquareActivity, X,
} from 'lucide-react'
import { hindsightBankLabel } from './providerStatus.js'
import { parsePostmortemMarkdown } from './postmortemMarkdown.js'

const API_ROOT = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api').replace(/\/$/, '')
const DATA_LABEL = import.meta.env.VITE_DATA_LABEL
const DEMO_STORAGE_KEY = 'incidentiq.synthetic-demo.v1'
const DEMO_FIXTURES = {
  history: {
    title: 'SYNTHETIC DEMO · Payment API 503 after worker release',
    description: 'Synthetic demonstration only. Payment API requests return HTTP 503 during checkout. Database connection utilization is near capacity, Redis latency is elevated, and failures began after a worker-concurrency change.',
    service_name: 'payment-api',
    environment: 'simulated-production',
    severity: 'high',
    source: 'synthetic_demo',
    error_messages: ['Synthetic demo: checkout requests returned HTTP 503.'],
    logs: [
      { log_type: 'error', log_text: 'SYNTHETIC: checkout handler returned HTTP 503; request trace DEMO-TRACE-001.', source_system: 'synthetic_fixture' },
      { log_type: 'warning', log_text: 'SYNTHETIC: database connection pool utilization reached 98%.', source_system: 'synthetic_fixture' },
      { log_type: 'warning', log_text: 'SYNTHETIC: Redis p95 latency increased to 420 ms.', source_system: 'synthetic_fixture' },
    ],
    system_metrics: { database_connection_utilization_percent: 98, redis_p95_latency_ms: 420, checkout_http_503_rate_percent: 17 },
    deployment: { deployment_id: 'DEP-DEMO-921', version: 'demo-2026.11.06-a', change_summary: 'Synthetic scenario: worker concurrency was changed before the simulated incident.' },
  },
  followUp: {
    title: 'SYNTHETIC DEMO · Checkout failures after follow-up release',
    description: 'Synthetic follow-up incident related to the earlier payment-api 503 scenario. Checkout failures and elevated database connections have returned after a later simulated release. Treat all prior context as historical evidence, not proof of the current cause.',
    service_name: 'payment-api',
    environment: 'simulated-production',
    severity: 'high',
    source: 'synthetic_demo',
    error_messages: ['Synthetic demo: checkout requests intermittently returned HTTP 503.'],
    logs: [
      { log_type: 'error', log_text: 'SYNTHETIC: payment-api checkout returned HTTP 503 after follow-up release.', source_system: 'synthetic_fixture' },
      { log_type: 'warning', log_text: 'SYNTHETIC: database connection utilization reached 95%; compare with current deployment evidence.', source_system: 'synthetic_fixture' },
      { log_type: 'note', log_text: 'SYNTHETIC: historical context may be relevant but requires engineer validation.', source_system: 'synthetic_fixture' },
    ],
    system_metrics: { database_connection_utilization_percent: 95, redis_p95_latency_ms: 360, checkout_http_503_rate_percent: 9 },
    deployment: { deployment_id: 'DEP-DEMO-922', version: 'demo-2026.11.06-b', change_summary: 'Synthetic follow-up release for the IncidentIQ memory demonstration.' },
  },
}
function readDemoProgress() {
  const empty = { historicalIncidentId: null, historicalOffRunId: null, historicalRetentionStatus: null, followUpIncidentId: null }
  try {
    const saved = JSON.parse(window.localStorage.getItem(DEMO_STORAGE_KEY) || '{}')
    return Object.fromEntries(Object.keys(empty).map((key) => [key, typeof saved[key] === 'string' ? saved[key] : null]))
  } catch { return empty }
}

async function api(path, options = {}) {
  let response
  try {
    const url = path === '/health' ? `${new URL(API_ROOT).origin}/health` : `${API_ROOT}${path}`
    response = await fetch(url, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    })
  } catch {
    throw new Error('Cannot reach the IncidentIQ API. Confirm the backend is running, then retry.')
  }
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    const message = body?.detail?.message || body?.detail || 'The request could not be completed.'
    const error = new Error(typeof message === 'string' ? message : 'The request could not be completed.')
    error.code = body?.detail?.code
    error.category = body?.detail?.error_category
    error.resourceId = body?.detail?.investigation_id
    throw error
  }
  return body?.data ?? body
}

const navItems = [
  { id: 'dashboard', label: 'Command center', icon: Gauge, group: 'Workspace' },
  { id: 'investigate', label: 'Investigations', icon: Radar, group: 'Workspace' },
  { id: 'memory', label: 'Memory explorer', icon: BrainCircuit, group: 'Intelligence' },
  { id: 'postmortem', label: 'Postmortems', icon: FileText, group: 'Intelligence' },
]

const provenanceStyle = {
  current_incident_evidence: ['Current evidence', 'blue'],
  historical_hindsight_memory: ['Hindsight memory', 'violet'],
  historical_memory: ['Hindsight memory', 'violet'],
  ai_generated_hypothesis: ['AI hypothesis', 'amber'],
  ai_hypothesis: ['AI hypothesis', 'amber'],
  engineer_verified_root_cause: ['Engineer verified', 'green'],
}

function App() {
  const [page, setPage] = useState('dashboard')
  const [mobileNav, setMobileNav] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [checkingHealth, setCheckingHealth] = useState(false)
  const [toast, setToast] = useState(null)
  const [dashboard, setDashboard] = useState(null)
  const [incidents, setIncidents] = useState([])
  const [memoryActivity, setMemoryActivity] = useState([])
  const [health, setHealth] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [selectedIncidentId, setSelectedIncidentId] = useState('')
  const [recentRuns, setRecentRuns] = useState([])
  const [demo, setDemo] = useState(readDemoProgress)

  const notify = useCallback((kind, message) => {
    setToast({ kind, message })
    window.setTimeout(() => setToast(null), 4200)
  }, [])

  const refreshHealth = useCallback(async () => {
    setCheckingHealth(true)
    try {
      setHealth(await api('/health'))
    } catch {
      setHealth({ application: 'unavailable', dependencies: {} })
    } finally {
      setCheckingHealth(false)
    }
  }, [])

  const reload = useCallback(async () => {
    setRefreshing(true)
    setLoadError('')
    const [summary, list, memory] = await Promise.allSettled([
      api('/dashboard/summary'), api('/incidents?page=1&limit=30'),
      api('/memory/activity?limit=8'),
    ])
    if (summary.status === 'fulfilled') setDashboard(summary.value)
    if (list.status === 'fulfilled') {
      const items = list.value.items || []
      setIncidents(items)
      setSelectedIncidentId((current) => current || items[0]?.id || '')
    }
    if (memory.status === 'fulfilled') setMemoryActivity(memory.value.items || [])
    const failures = [summary, list].filter((item) => item.status === 'rejected')
    if (failures.length) setLoadError(failures[0].reason.message)
    setRefreshing(false)
  }, [])

  useEffect(() => { reload(); refreshHealth() }, [reload, refreshHealth])
  useEffect(() => { try { window.localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(demo)) } catch { /* Demo progress is a convenience; the backend remains authoritative. */ } }, [demo])

  const selectedIncident = useMemo(
    () => incidents.find((incident) => incident.id === selectedIncidentId),
    [incidents, selectedIncidentId],
  )

  const onRunCreated = useCallback((run, incident) => {
    setRecentRuns((items) => [{
      id: run.investigation_id, incidentTitle: incident.title,
      incidentNumber: incident.incident_number, mode: run.memory_mode,
      status: run.execution_status, createdAt: new Date().toISOString(),
    }, ...items].slice(0, 5))
    if (run.incident_id === demo.historicalIncidentId && run.memory_mode === 'off') {
      setDemo((current) => ({ ...current, historicalOffRunId: run.investigation_id }))
    }
    reload()
  }, [demo.historicalIncidentId, reload])

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
        <div className="brand-lockup">
          <div className="brand-mark"><Network size={19} strokeWidth={2.2} /></div>
          <div><div className="brand-name">incident<span>iq</span></div><div className="brand-caption">INCIDENT RESPONSE</div></div>
          <button className="icon-button sidebar-close" aria-label="Close navigation" onClick={() => setMobileNav(false)}><X size={17} /></button>
        </div>
        <div className="workspace-label"><span className="workspace-symbol"><Database size={14}/></span><div className="workspace-copy"><strong>Local workspace</strong><span>Current API data</span></div></div>
        <nav className="side-nav" aria-label="Primary navigation">
          {['Workspace', 'Intelligence'].map((group) => <div className="nav-group" key={group}>
            <div className="nav-label">{group}</div>
            {navItems.filter((item) => item.group === group).map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item ${page === id ? 'active' : ''}`} onClick={() => { setPage(id); setMobileNav(false) }}><Icon size={17} /><span>{label}</span>{id === 'investigate' && <span className="nav-count">{dashboard?.open_incidents ?? '—'}</span>}</button>)}
          </div>)}
          <div className="nav-group"><div className="nav-label">Demo</div><button className={`nav-item ${page === 'compare' ? 'active' : ''}`} onClick={() => { setPage('compare'); setMobileNav(false) }}><Layers3 size={17} /><span>Memory comparison</span><span className="live-dot" /></button></div>
        </nav>
        <div className="sidebar-bottom">
          <button className="memory-promo" onClick={() => { setPage('investigate'); setMobileNav(false) }}><div className="promo-icon"><BrainCircuit size={17} /></div><div><strong>Hindsight learning loop</strong><p>Open the verified learning workflow.</p></div><ArrowRight size={15} /></button>
          <div className="user-profile"><div className="avatar"><ShieldCheck size={15}/></div><div className="profile-copy"><strong>Local session</strong><span>Unauthenticated</span></div></div>
        </div>
      </aside>
      {mobileNav && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}

      <main className="main-shell">
        <header className="topbar">
          <div className="topbar-left"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileNav(true)}><Menu size={19} /></button><div className="breadcrumb">Workspace <ChevronRight size={14} /> <strong>{navItems.find((item) => item.id === page)?.label || (page === 'compare' ? 'Memory comparison' : 'Postmortems')}</strong></div></div>
          <div className="topbar-actions"><div className="topbar-status"><span className={`status-pulse ${health?.application === 'available' ? '' : 'status-unknown'}`} />{health?.application === 'available' ? 'API reachable' : health ? 'API unavailable' : 'Checking API'} <span className="status-divider" /> <span className="topbar-env">LOCAL API</span></div><button className="icon-button" title="Refresh data" onClick={reload} disabled={refreshing}><RefreshCw size={16} className={refreshing ? 'spin' : ''} /></button></div>
        </header>

        <div className="content-wrap">
          {DATA_LABEL && <div className="test-data-banner"><CircleHelp size={14}/><span>{DATA_LABEL}</span></div>}
          {loadError && <div className="alert alert-error"><AlertCircle size={17} /><span>{loadError}</span><button onClick={reload}>Retry</button></div>}
          {page === 'dashboard' && <DashboardPage dashboard={dashboard} incidents={incidents} activities={memoryActivity} health={health} recentRuns={recentRuns} onOpenIncident={(id) => { setSelectedIncidentId(id); setPage('investigate') }} onNavigate={setPage} loading={refreshing} onRefreshHealth={refreshHealth} checkingHealth={checkingHealth} />}
          {page === 'investigate' && <InvestigationPage incidents={incidents} selectedIncidentId={selectedIncidentId} setSelectedIncidentId={setSelectedIncidentId} selectedIncident={selectedIncident} onIncidentCreated={(id) => { setSelectedIncidentId(id); reload() }} onRunCreated={onRunCreated} notify={notify} demo={demo} setDemo={setDemo} onDataChanged={reload} />}
          {page === 'compare' && <ComparisonPage incidents={incidents} selectedIncidentId={selectedIncidentId} setSelectedIncidentId={setSelectedIncidentId} selectedIncident={selectedIncident} onRunCreated={onRunCreated} notify={notify} />}
          {page === 'memory' && <MemoryPage incidents={incidents} selectedIncidentId={selectedIncidentId} setSelectedIncidentId={setSelectedIncidentId} onNavigate={setPage} health={health} />}
          {page === 'postmortem' && <PostmortemPage incidents={incidents} notify={notify} onNavigate={setPage} />}
        </div>
        <footer className="footer"><span>INCIDENTIQ <span className="footer-separator">/</span> Local operational data</span><span>Verified resolutions are retained in Hindsight.</span></footer>
      </main>
      {toast && <div className={`toast toast-${toast.kind}`} role="status">{toast.kind === 'success' ? <CheckCircle2 size={17} /> : <AlertCircle size={17} />}{toast.message}<button onClick={() => setToast(null)} aria-label="Dismiss"><X size={15} /></button></div>}
    </div>
  )
}

function DashboardPage({ dashboard, incidents, activities, health, recentRuns, onOpenIncident, onNavigate, loading, onRefreshHealth, checkingHealth }) {
  const cards = [
    { label: 'Total incidents', value: dashboard?.total_incidents, icon: SquareActivity, tone: 'cyan', foot: 'Across this workspace' },
    { label: 'Open incidents', value: dashboard?.open_incidents, icon: Activity, tone: 'violet', foot: 'Awaiting investigation' },
    { label: 'Resolved', value: dashboard?.resolved_incidents, icon: ShieldCheck, tone: 'green', foot: 'Engineer verified' },
    { label: 'Critical severity', value: dashboard?.critical_incidents, icon: AlertCircle, tone: 'red', foot: 'Requires attention' },
  ]
  const severities = ['critical', 'high', 'medium', 'low']
  const total = dashboard?.total_incidents || 0
  return <>
    <PageHeading eyebrow={formatLongDate()} title="Incident overview" subtitle="Current incident and integration status from the local API." action={<button className="button button-primary" onClick={() => onNavigate('investigate')}><Plus size={16} /> New investigation</button>} />
    <section className="metric-grid" aria-label="Incident statistics">
      {cards.map(({ label, value, icon: Icon, tone, foot }, index) => <article className={`metric-card metric-${tone}`} key={label} style={{ '--delay': `${index * 55}ms` }}><div className="metric-top"><div className={`metric-icon ${tone}`}><Icon size={17} /></div><span className="metric-period">CURRENT</span></div><div className="metric-value">{loading && value == null ? <span className="skeleton skeleton-number" /> : value ?? '—'}</div><div className="metric-bottom"><strong>{label}</strong><span>{foot}</span></div></article>)}
    </section>
    <section className="overview-grid">
      <article className="panel severity-panel"><div className="panel-heading"><div><div className="section-kicker">INCIDENT LANDSCAPE</div><h2>Severity distribution</h2></div><span className="panel-period">API snapshot</span></div>
        {total ? <div className="severity-content"><div className="severity-ring" style={{ '--critical': `${(dashboard.severity_distribution.critical / total) * 100}%`, '--high': `${(dashboard.severity_distribution.high / total) * 100}%`, '--medium': `${(dashboard.severity_distribution.medium / total) * 100}%`, '--low': `${(dashboard.severity_distribution.low / total) * 100}%` }}><div className="ring-center"><strong>{total}</strong><span>INCIDENTS</span></div></div><div className="severity-legend">{severities.map((severity) => { const count = dashboard?.severity_distribution?.[severity] || 0; return <div className="severity-row" key={severity}><span className={`severity-dot ${severity}`} /><span className="severity-name">{severity}</span><div className="severity-track"><div className={`severity-fill ${severity}`} style={{ width: `${Math.max((count / total) * 100, count ? 3 : 0)}%` }} /></div><strong>{count}</strong></div> })}</div></div> : <EmptyState icon={Radar} title="No incident signals yet" copy="Once incidents are submitted, severity distribution will appear here." action={<button className="text-button" onClick={() => onNavigate('investigate')}>Submit your first incident <ArrowRight size={14} /></button>} />}
      </article>
      <article className="panel system-panel"><div className="panel-heading"><div><div className="section-kicker">PLATFORM STATUS</div><h2>Intelligence services</h2></div><button className="text-button" onClick={onRefreshHealth} disabled={checkingHealth}>{checkingHealth ? 'Checking…' : 'Re-check integrations'}</button></div><div className="service-list">{serviceRows(health).map((item) => <ServiceRow key={item.label} {...item} />)}</div><div className="system-note"><CircleHelp size={14} /><span>Provider checks run at startup or when requested; data refreshes do not call providers.</span></div></article>
    </section>
    <section className="dashboard-lower">
      <article className="panel incidents-panel"><div className="panel-heading"><div><div className="section-kicker">RECENT INCIDENTS</div><h2>Recent incidents <span className="inline-count">{incidents.length}</span></h2></div><button className="text-button" onClick={() => onNavigate('investigate')}>View investigations <ArrowRight size={14} /></button></div>
        {incidents.length ? <div className="incident-table-wrap"><table className="incident-table"><thead><tr><th>Incident</th><th>Service</th><th>Severity</th><th>Status</th><th>Reported</th><th></th></tr></thead><tbody>{incidents.slice(0, 6).map((incident) => <tr key={incident.id} onClick={() => onOpenIncident(incident.id)}><td><div className="incident-title-cell"><span className="incident-ref">{incident.incident_number}</span><strong>{incident.title}</strong></div></td><td><span className="service-name"><span className="service-glyph">{incident.service_name?.slice(0, 1).toUpperCase()}</span>{incident.service_name}</span></td><td><SeverityBadge value={incident.severity} /></td><td><StatusBadge value={incident.status} /></td><td className="date-cell">{formatRelative(incident.created_at)}</td><td><ChevronRight size={15} className="row-chevron" /></td></tr>)}</tbody></table></div> : <EmptyState icon={SquareActivity} title="Your incident queue is clear" copy="New incidents submitted to the API will appear here." action={<button className="button button-secondary button-small" onClick={() => onNavigate('investigate')}><Plus size={14} /> Create incident</button>} />}
      </article>
      <div className="activity-column">
        <article className="panel activity-panel"><div className="panel-heading"><div><div className="section-kicker">THIS SESSION · AI REASONING</div><h2>Investigation activity</h2></div><Sparkles size={16} className="heading-accent" /></div>{recentRuns.length ? <div className="activity-list">{recentRuns.map((run) => <div className="activity-item" key={run.id}><div className={`activity-icon ${run.mode}`}><BrainCircuit size={15} /></div><div className="activity-copy"><strong>{run.incidentTitle}</strong><span>{run.incidentNumber} · MEMORY_{run.mode.toUpperCase()}</span></div><StatusBadge value={run.status} /></div>)}</div> : <div className="compact-empty"><span className="empty-orbit"><BrainCircuit size={18} /></span><p>Investigation runs from this session will appear here after analysis.</p><button className="text-button" onClick={() => onNavigate('investigate')}>Start an investigation <ArrowRight size={13} /></button></div>}</article>
        <article className="panel memory-activity-panel"><div className="panel-heading"><div><div className="section-kicker">HINDSIGHT MEMORY</div><h2>Learning activity</h2></div><History size={16} className="heading-accent violet-text" /></div>{activities.length ? <div className="memory-activity-list">{activities.slice(0, 4).map((event) => <div className="memory-activity-row" key={event.id}><span className={`event-indicator ${event.status}`} /><div><strong>{event.operation === 'recall' ? 'Memory recalled' : event.operation === 'retain' ? `${event.memory_type} retained` : 'Memory event'}</strong><span>{event.memory_type} · {formatRelative(event.created_at)}</span></div><span className={`mini-status ${event.status}`}>{event.status}</span></div>)}</div> : <div className="compact-empty compact-empty-small"><p>No memory operations recorded yet. Recalled and retained memory activity will show here.</p><button className="text-button" onClick={() => onNavigate('memory')}>Explore memory <ArrowRight size={13} /></button></div>}</article>
      </div>
    </section>
  </>
}

function serviceRows(health) {
  const deps = health?.dependencies || {}
  const state = (key) => {
    const item = deps[key]
    if (!item) return ['Unknown', 'neutral', 'Status unavailable']
    if (item.status === 'connected') return ['Connected', 'good', 'Connection checked successfully']
    if (item.status === 'reachable' || item.reachable === true) return ['Reachable', 'good', 'Provider check succeeded']
    if (item.status === 'unavailable') return ['Unavailable', 'bad', 'Last connection check failed']
    if (item.configured) return ['Configured', 'neutral', 'Checked when the service is used']
    return ['Not configured', 'neutral', 'Optional configuration is missing']
  }
  const database = state('database'); const memory = state('hindsight'); const groq = state('groq')
  return [
    { label: 'PostgreSQL', sub: 'Operational system of record', icon: Database, state: database[0], tone: database[1], note: database[2] },
    { label: 'Hindsight', sub: 'Persistent incident memory', icon: BrainCircuit, state: memory[0], tone: memory[1], note: memory[2] },
    { label: 'Groq inference', sub: 'Structured investigation reasoning', icon: Sparkles, state: groq[0], tone: groq[1], note: groq[2] },
  ]
}

function ServiceRow({ label, sub, icon: Icon, state, tone, note }) {
  return <div className="service-row"><div className="service-icon"><Icon size={16} /></div><div className="service-row-copy"><strong>{label}</strong><span>{sub}</span></div><div className={`service-state ${tone}`} title={note}><span />{state}</div></div>
}

function InvestigationPage({ incidents, selectedIncidentId, setSelectedIncidentId, selectedIncident, onIncidentCreated, onRunCreated, notify, demo, setDemo, onDataChanged }) {
  const [showForm, setShowForm] = useState(!incidents.length)
  const [mode, setMode] = useState('on')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [runError, setRunError] = useState('')
  const [detail, setDetail] = useState(null)
  const [demoBusy, setDemoBusy] = useState('')
  const [demoError, setDemoError] = useState('')
  useEffect(() => {
    let active = true
    async function restorePersistedDemoProgress() {
      if (!incidents.length) return
      try {
        const firstPage = await api('/incidents?page=1&limit=100')
        const pages = Math.max(1, Math.ceil((firstPage.total || 0) / 100))
        for (let page = 1; page <= pages; page += 1) {
          const listing = page === 1 ? firstPage : await api(`/incidents?page=${page}&limit=100`)
          const candidate = (listing.items || []).find((item) =>
            item.title === DEMO_FIXTURES.history.title && item.service_name === DEMO_FIXTURES.history.service_name,
          )
          if (!candidate) continue
          const historical = await api(`/incidents/${candidate.id}`)
          if (!active) return
          if (historical.source !== 'synthetic_demo' || historical.environment !== DEMO_FIXTURES.history.environment) return
          const completedMemoryOffRun = historical.investigation_runs?.find(
            (run) => run.memory_mode === 'off' && run.execution_status === 'succeeded',
          )
          setDemo((current) => ({
            ...current,
            historicalIncidentId: historical.id,
            historicalOffRunId: completedMemoryOffRun?.id || null,
            historicalRetentionStatus: historical.memory_retention_status || null,
          }))
          return
        }
      } catch { /* A demo fixture is optional; never create one during page load. */ }
    }
    restorePersistedDemoProgress()
    return () => { active = false }
  }, [incidents])
  useEffect(() => {
    let active = true
    if (!selectedIncidentId) { setDetail(null); return undefined }
    api(`/incidents/${selectedIncidentId}`).then((loadedDetail) => {
      if (!active) return
      setDetail(loadedDetail)
      if (loadedDetail.source === 'synthetic_demo' && loadedDetail.title === DEMO_FIXTURES.history.title) {
        const completedMemoryOffRun = loadedDetail.investigation_runs?.find(
          (run) => run.memory_mode === 'off' && run.execution_status === 'succeeded',
        )
        setDemo((current) => ({
          ...current,
          historicalIncidentId: loadedDetail.id,
          historicalOffRunId: completedMemoryOffRun?.id || null,
          historicalRetentionStatus: loadedDetail.memory_retention_status || null,
        }))
      }
    }).catch(() => { if (active) setDetail(null) })
    return () => { active = false }
  }, [selectedIncidentId])
  useEffect(() => { setResult(null); setRunError('') }, [selectedIncidentId])

  async function runInvestigation() {
    if (!selectedIncidentId) return
    setRunning(true); setRunError(''); setResult(null)
    try {
      const run = await api(`/incidents/${selectedIncidentId}/investigate`, { method: 'POST', body: JSON.stringify({ memory_mode: mode === 'on' ? 'MEMORY_ON' : 'MEMORY_OFF' }) })
      setResult(run); onRunCreated(run, selectedIncident)
      notify('success', `Investigation completed with MEMORY_${mode.toUpperCase()}.`)
    } catch (error) { setRunError(error.message); notify('error', error.message) }
    finally { setRunning(false) }
  }

  async function getOrCreateSynthetic(kind) {
    const fixture = DEMO_FIXTURES[kind]
    const idKey = kind === 'history' ? 'historicalIncidentId' : 'followUpIncidentId'
    const savedId = demo[idKey]
    if (savedId) {
      try {
        const existing = await api(`/incidents/${savedId}`)
        if (existing.source === 'synthetic_demo' && existing.title === fixture.title) return existing
      } catch { /* A stale browser pointer is ignored; no existing record is changed. */ }
    }
    // Browser storage can be cleared or differ across devices. Reuse an exact,
    // server-confirmed synthetic fixture before creating a new incident.
    const firstPage = await api('/incidents?page=1&limit=100')
    const pageCount = Math.max(1, Math.ceil((firstPage.total || 0) / 100))
    for (let page = 1; page <= pageCount; page += 1) {
      const listing = page === 1 ? firstPage : await api(`/incidents?page=${page}&limit=100`)
      for (const candidate of listing.items || []) {
        if (candidate.title !== fixture.title || candidate.service_name !== fixture.service_name) continue
        try {
          const existing = await api(`/incidents/${candidate.id}`)
          if (existing.source === 'synthetic_demo' && existing.title === fixture.title && existing.environment === fixture.environment) {
            setDemo((current) => ({ ...current, [idKey]: existing.id }))
            return existing
          }
        } catch { /* Ignore missing candidate records; never mutate them. */ }
      }
    }
    const created = await api('/incidents', { method: 'POST', body: JSON.stringify(fixture) })
    setDemo((current) => ({ ...current, [idKey]: created.incident_id, ...(kind === 'history' ? { historicalOffRunId: null, historicalRetentionStatus: null } : {}) }))
    return {
      id: created.incident_id,
      incident_id: created.incident_id,
      incident_number: created.incident_number,
      title: fixture.title,
      status: created.status,
      severity: fixture.severity,
      service_name: fixture.service_name,
      created_at: new Date().toISOString(),
      source: fixture.source,
    }
  }

  async function openSyntheticHistory() {
    setDemoBusy('history'); setDemoError('')
    try {
      const incident = await getOrCreateSynthetic('history')
      setShowForm(false)
      setMode('off'); setResult(null); setRunError('')
      onIncidentCreated(incident.id || incident.incident_id)
      notify('success', 'Synthetic historical incident ready. Run MEMORY_OFF, then review and confirm the real simulated resolution.')
    } catch (error) { setDemoError(error.message) }
    finally { setDemoBusy('') }
  }

  async function createAndInvestigateFollowUp() {
    if (!demo.historicalOffRunId || !['success', 'skipped_duplicate'].includes(demo.historicalRetentionStatus)) return
    setDemoBusy('followup'); setDemoError(''); setRunning(true); setResult(null); setRunError('')
    try {
      const incident = await getOrCreateSynthetic('followUp')
      const incidentId = incident.id || incident.incident_id
      setShowForm(false)
      setMode('on'); onIncidentCreated(incidentId)
      const run = await api(`/incidents/${incidentId}/investigate`, { method: 'POST', body: JSON.stringify({ memory_mode: 'MEMORY_ON' }) })
      setResult(run); onRunCreated(run, incident)
      notify('success', 'Follow-up investigation completed. Review the actual Hindsight memories returned; they are historical context, not proof.')
    } catch (error) { setRunError(error.message); setDemoError(error.message); notify('error', error.message) }
    finally { setDemoBusy(''); setRunning(false) }
  }

  async function recordResolution(incidentId, retentionStatus) {
    if (incidentId === demo.historicalIncidentId) {
      setDemo((current) => ({ ...current, historicalRetentionStatus: retentionStatus }))
    }
    try { setDetail(await api(`/incidents/${incidentId}`)) } catch { /* The saved response remains visible in the review panel. */ }
    onDataChanged()
  }

  return <>
    <PageHeading eyebrow="INCIDENT INVESTIGATION" title="Investigation center" subtitle="Bring current evidence and historical memory into one reviewable investigation." action={<button className="button button-secondary" onClick={() => setShowForm((value) => !value)}><Plus size={15} /> Submit incident</button>} />
    <section className="panel guided-demo-panel" aria-labelledby="guided-demo-title">
      <div className="guided-demo-copy"><span className="demo-label">SYNTHETIC DATA ONLY</span><h2 id="guided-demo-title">Guided Hindsight learning loop</h2><p>Creates labeled sample incidents only when you click. The browser reuses saved or exact-matching synthetic fixtures; no other records are edited or deleted.</p></div>
      <div className="demo-steps">
        <div className={`demo-step ${demo.historicalIncidentId ? 'complete' : 'current'}`}><span>01</span><div><strong>Historical incident</strong><small>{demo.historicalIncidentId ? 'Synthetic record ready' : 'Create or reopen sample'}</small></div></div>
        <div className={`demo-step ${demo.historicalOffRunId ? 'complete' : ''}`}><span>02</span><div><strong>MEMORY_OFF</strong><small>{demo.historicalOffRunId ? 'Run completed' : 'Investigate without recall'}</small></div></div>
        <div className={`demo-step ${['success', 'skipped_duplicate'].includes(demo.historicalRetentionStatus) ? 'complete' : ''}`}><span>03</span><div><strong>Engineer review</strong><small>{demo.historicalRetentionStatus === 'success' ? 'Hindsight retain succeeded' : demo.historicalRetentionStatus === 'skipped_duplicate' ? 'Duplicate safely skipped' : demo.historicalRetentionStatus === 'failed' ? 'Retention failed — follow-up disabled' : 'Confirm a verified outcome'}</small></div></div>
        <div className={`demo-step ${demo.followUpIncidentId ? 'complete' : ''}`}><span>04</span><div><strong>MEMORY_ON follow-up</strong><small>{demo.followUpIncidentId ? 'Follow-up created' : 'Recall retained history'}</small></div></div>
      </div>
      <div className="guided-demo-actions"><button className="button button-secondary button-small" onClick={openSyntheticHistory} disabled={Boolean(demoBusy || running)}>{demoBusy === 'history' ? <><LoaderCircle size={14} className="spin"/> Loading sample…</> : <><Plus size={14}/> Create / load historical sample</>}</button><button className="button button-primary button-small" onClick={createAndInvestigateFollowUp} disabled={Boolean(demoBusy || running) || !demo.historicalOffRunId || !['success', 'skipped_duplicate'].includes(demo.historicalRetentionStatus)}>{demoBusy === 'followup' ? <><LoaderCircle size={14} className="spin"/> Recalling & investigating…</> : <><BrainCircuit size={14}/> Create & investigate related sample</>}</button></div>
      {(!demo.historicalOffRunId || !['success', 'skipped_duplicate'].includes(demo.historicalRetentionStatus)) && <p className="demo-prerequisite-note" role="status">{!demo.historicalOffRunId ? 'The follow-up unlocks after a successful MEMORY_OFF run on the historical sample.' : 'The follow-up unlocks after an engineer confirms the verified resolution and Hindsight reports retain success.'}</p>}
      {demoError && <div className="inline-error"><AlertCircle size={15}/>{demoError}</div>}
    </section>
    <div className="investigation-toolbar panel"><div className="incident-select-wrap"><label htmlFor="incident-select">INCIDENT CONTEXT</label><div className="select-shell"><SquareActivity size={16} /><select id="incident-select" value={selectedIncidentId} onChange={(event) => setSelectedIncidentId(event.target.value)}><option value="">Select an incident…</option>{incidents.map((item) => <option value={item.id} key={item.id}>{item.incident_number} · {item.title}</option>)}</select><ChevronDown size={15} /></div></div><div className="mode-select"><div className="mode-label">MEMORY MODE</div><div className="segmented-control"><button className={mode === 'off' ? 'selected' : ''} onClick={() => setMode('off')}><span className="mode-toggle-dot off" />MEMORY_OFF</button><button className={mode === 'on' ? 'selected memory-selected' : ''} onClick={() => setMode('on')}><span className="mode-toggle-dot on" />MEMORY_ON</button></div></div><button className="button button-primary run-button" onClick={runInvestigation} disabled={!selectedIncidentId || running}>{running ? <><LoaderCircle className="spin" size={16} /> Investigating…</> : <><Sparkles size={16} /> Run investigation</>}</button></div>
    {showForm && <IncidentForm onCreated={(id) => { onIncidentCreated(id); setShowForm(false); notify('success', 'Incident submitted to the production record.') }} onCancel={() => setShowForm(false)} />}
    {!selectedIncident ? <div className="panel page-empty"><EmptyState icon={Radar} title="Select an incident to investigate" copy="Choose an incident from the context selector, or submit a new one. The analysis will use only evidence and memories returned by the backend." action={<button className="button button-secondary button-small" onClick={() => setShowForm(true)}><Plus size={14} /> Submit incident</button>} /></div> : <div className="investigation-layout">
      <aside className="context-column"><article className="panel context-panel"><div className="panel-heading"><div><div className="section-kicker">CURRENT INCIDENT</div><h2>Context</h2></div><SeverityBadge value={selectedIncident.severity} /></div><div className="context-reference">{selectedIncident.incident_number}<span className="ref-separator">/</span><StatusBadge value={selectedIncident.status} /></div><h3 className="context-title">{selectedIncident.title}</h3><div className="context-attribute"><span>Service</span><strong>{selectedIncident.service_name}</strong></div>{detail?.environment && <div className="context-attribute"><span>Environment</span><strong>{detail.environment}</strong></div>}{detail?.source === 'synthetic_demo' && <div className="synthetic-context-note">SYNTHETIC DEMO DATA · not production telemetry</div>}<div className="context-attribute"><span>Reported</span><strong>{formatDate(detail?.created_at || selectedIncident.created_at)}</strong></div><div className="context-divider"/><div className="context-section-label">DESCRIPTION</div><p className="context-description">{detail?.description || 'Loading incident details…'}</p>{detail?.root_cause_summary && <div className="verified-context"><ShieldCheck size={15}/><div><span>ENGINEER VERIFIED</span><p>{detail.root_cause_summary}</p></div></div>}{detail?.logs?.length > 0 && <details className="evidence-disclosure"><summary className="context-section-label">CURRENT EVIDENCE <span>{detail.logs.length}</span></summary><div className="evidence-stack">{detail.logs.map((log) => <div className="raw-evidence" key={log.id}><span className="evidence-type">{log.log_type}</span><code>{log.log_text}</code><ProvenanceTag value="current_incident_evidence" /></div>)}</div></details>}</article><article className="panel workflow-card"><div className="section-kicker">INVESTIGATION FLOW</div><WorkflowStep number="01" title="Current evidence" active /><WorkflowStep number="02" title="Hindsight recall" active={Boolean(result?.memory_mode === 'on') || (running && mode === 'on')} muted={result?.memory_mode === 'off' || (!result && !running && mode === 'off')} label={result ? (result.memory_mode === 'off' ? 'Skipped in MEMORY_OFF' : `${result.analysis.historical_memories.length} memories returned`) : runError ? 'Not completed' : running ? (mode === 'on' ? 'Recalling' : 'Skipped in MEMORY_OFF') : (mode === 'on' ? 'Runs on submission' : 'Will be skipped')} /><WorkflowStep number="03" title="AI reasoning" active={Boolean(result) || running} /><WorkflowStep number="04" title="Engineer review" active={Boolean(result && detail?.verified_resolutions?.length)} label={result && detail?.verified_resolutions?.length ? 'Verified' : result ? 'Pending verification' : 'Available after a successful run'} last /></article></aside>
      <div className="analysis-column">{runError && <div className="alert alert-error"><AlertCircle size={17}/><div><strong>Investigation could not complete</strong><span>{runError}</span></div></div>}{running && <LoadingAnalysis mode={mode} />}{result && <InvestigationResult result={result} incident={selectedIncident} detail={detail} onResolutionRecorded={recordResolution} onDataChanged={onDataChanged} notify={notify} />}{!result && detail?.verified_resolutions?.length > 0 && <EngineerReviewPanel result={null} incident={selectedIncident} detail={detail} onResolutionRecorded={recordResolution} onDataChanged={onDataChanged} notify={notify} />}{!running && !result && !runError && !detail?.verified_resolutions?.length && <div className="panel analysis-placeholder"><div className="placeholder-visual"><div className="placeholder-orbit orbit-one"/><div className="placeholder-orbit orbit-two"/><div className="placeholder-core"><BrainCircuit size={27}/></div><span className="orbit-node node-one"/><span className="orbit-node node-two"/><span className="orbit-node node-three"/></div><div className="section-kicker">READY TO INVESTIGATE</div><h2>Evidence in. Clarity out.</h2><p>Run an investigation to analyze current signals{mode === 'on' ? ' alongside relevant Hindsight memory.' : ' without retrieving Hindsight memory.'}</p><button className="button button-primary" onClick={runInvestigation}><Sparkles size={15}/> Start {mode === 'on' ? 'memory-on' : 'memory-off'} analysis</button><span className="placeholder-foot"><ShieldCheck size={13}/>Recommendations always require engineer review</span></div>}</div>
    </div>}
  </>
}

function IncidentForm({ onCreated, onCancel }) {
  const [form, setForm] = useState({ title: '', description: '', service_name: '', environment: 'production', severity: 'high', error: '', deployment_id: '', metrics: '' })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  function update(event) { setForm((current) => ({ ...current, [event.target.name]: event.target.value })) }
  async function submit(event) {
    event.preventDefault(); setSubmitting(true); setError('')
    let system_metrics = {}
    if (form.metrics.trim()) {
      try { system_metrics = JSON.parse(form.metrics) } catch { setError('Metrics must be valid JSON, for example {"db_utilization": 98}.'); setSubmitting(false); return }
      if (!system_metrics || typeof system_metrics !== 'object' || Array.isArray(system_metrics)) { setError('Metrics must be a JSON object.'); setSubmitting(false); return }
    }
    const payload = { title: form.title, description: form.description, service_name: form.service_name, environment: form.environment, severity: form.severity, error_messages: form.error ? [form.error] : [], system_metrics }
    if (form.deployment_id.trim()) payload.deployment = { deployment_id: form.deployment_id.trim() }
    try { const created = await api('/incidents', { method: 'POST', body: JSON.stringify(payload) }); onCreated(created.incident_id) }
    catch (requestError) { setError(requestError.message) }
    finally { setSubmitting(false) }
  }
  return <form className="panel incident-form" onSubmit={submit}><div className="panel-heading"><div><div className="section-kicker">NEW RECORD</div><h2>Submit an incident</h2></div><button type="button" className="icon-button" onClick={onCancel} aria-label="Close form"><X size={17}/></button></div><div className="form-grid"><Field label="Incident title" required><input required name="title" maxLength="255" value={form.title} onChange={update} placeholder="e.g. Payment API returns HTTP 503"/></Field><Field label="Affected service" required><input required name="service_name" value={form.service_name} onChange={update} placeholder="payment-api"/></Field><Field label="Description" required full><textarea required name="description" rows="3" value={form.description} onChange={update} placeholder="What changed? What are customers experiencing?"/></Field><Field label="Severity"><select name="severity" value={form.severity} onChange={update}><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></Field><Field label="Environment"><input name="environment" value={form.environment} onChange={update}/></Field><Field label="Error message"><input name="error" value={form.error} onChange={update} placeholder="HTTP 503 from checkout endpoint"/></Field><Field label="Deployment ID"><input name="deployment_id" value={form.deployment_id} onChange={update} placeholder="DEP-921"/></Field><Field label="System metrics · JSON" full><input name="metrics" value={form.metrics} onChange={update} placeholder={'{"database_connection_utilization_percent": 98}'}/></Field></div>{error && <div className="inline-error"><AlertCircle size={15}/>{error}</div>}<div className="form-actions"><span>Stored in PostgreSQL. No external action is taken.</span><div><button type="button" className="button button-secondary" onClick={onCancel}>Cancel</button><button className="button button-primary" disabled={submitting}>{submitting ? <><LoaderCircle size={15} className="spin"/> Submitting</> : <><Plus size={15}/> Create incident</>}</button></div></div></form>
}

function Field({ label, required, full, children }) { return <label className={`form-field ${full ? 'field-full' : ''}`}><span>{label}{required && <b> *</b>}</span>{children}</label> }


function EngineerReviewPanel({ result, incident, detail, onResolutionRecorded, onDataChanged, notify }) {
  const [rootCause, setRootCause] = useState('')
  const [resolution, setResolution] = useState('')
  const [verifiedBy, setVerifiedBy] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [resolutionBusy, setResolutionBusy] = useState(false)
  const [resolutionError, setResolutionError] = useState('')
  const [resolutionResult, setResolutionResult] = useState(null)
  const [retentionBusy, setRetentionBusy] = useState(false)
  const [attemptedAction, setAttemptedAction] = useState('')
  const [outcome, setOutcome] = useState('')
  const [recordedBy, setRecordedBy] = useState('')
  const [failureBusy, setFailureBusy] = useState(false)
  const [failureError, setFailureError] = useState('')
  const [failureResult, setFailureResult] = useState(null)

  async function submitResolution(event) {
    event.preventDefault(); setResolutionBusy(true); setResolutionError('')
    try {
      const saved = await api(`/incidents/${incident.id}/resolve`, {
        method: 'POST',
        body: JSON.stringify({
          root_cause_summary: rootCause,
          resolution_summary: resolution,
          verified_by: verifiedBy,
          confirmed,
          ...(result ? { investigation_run_id: result.investigation_id } : {}),
        }),
      })
      setResolutionResult(saved)
      await onResolutionRecorded(incident.id, saved.memory_retention_status)
      const statusMessage = saved.memory_retention_status === 'success'
        ? 'Verified resolution saved; Hindsight retain reported success.'
        : saved.memory_retention_status === 'skipped_duplicate'
          ? 'Verified resolution saved; Hindsight safely skipped a duplicate memory.'
          : saved.memory_retention_status === 'failed'
            ? `Verified resolution saved, but Hindsight retention failed${saved.memory_error_category ? ` (${saved.memory_error_category})` : ''}. No memory-learning success is claimed.`
            : 'Verified resolution saved, but the Hindsight retention result is unknown. No memory-learning success is claimed.'
      notify(saved.memory_retention_status === 'failed' || !saved.memory_retention_status ? 'error' : 'success', statusMessage)
    } catch (error) { setResolutionError(error.message) }
    finally { setResolutionBusy(false) }
  }

  async function retryResolutionRetention() {
    setRetentionBusy(true); setResolutionError('')
    try {
      const saved = await api(`/incidents/${incident.id}/resolution/retain`, { method: 'POST' })
      setResolutionResult(saved)
      await onResolutionRecorded(incident.id, saved.memory_retention_status)
      const statusMessage = saved.memory_retention_status === 'success'
        ? 'Hindsight retain reported success for the saved verified resolution.'
        : saved.memory_retention_status === 'skipped_duplicate'
          ? 'Hindsight safely skipped an already-retained verified resolution.'
          : `Hindsight retention is still unavailable${saved.memory_error_category ? ` (${saved.memory_error_category})` : ''}.`
      notify(saved.memory_retention_status === 'failed' || !saved.memory_retention_status ? 'error' : 'success', statusMessage)
    } catch (error) { setResolutionError(error.message) }
    finally { setRetentionBusy(false) }
  }

  async function submitFailedApproach() {
    setFailureBusy(true); setFailureError('')
    try {
      const saved = await api(`/incidents/${incident.id}/failed-approaches`, {
        method: 'POST',
        body: JSON.stringify({
          attempted_action: attemptedAction,
          outcome,
          recorded_by: recordedBy,
          ...(result ? { investigation_run_id: result.investigation_id } : {}),
        }),
      })
      setFailureResult(saved)
      const statusMessage = saved.memory_retention_status === 'success'
        ? 'Failed approach retained in Hindsight as a separate failure memory.'
        : saved.memory_retention_status === 'skipped_duplicate'
          ? 'This failed approach was already retained; duplicate safely skipped.'
          : saved.memory_retention_status === 'failed'
            ? `Failed approach was submitted, but Hindsight retention failed${saved.memory_error_category ? ` (${saved.memory_error_category})` : ''}.`
            : 'The failed-approach retention result is unknown; no learning success is claimed.'
      notify(saved.memory_retention_status === 'failed' || !saved.memory_retention_status ? 'error' : 'success', statusMessage)
      onDataChanged()
    } catch (error) { setFailureError(error.message) }
    finally { setFailureBusy(false) }
  }

  const existingResolution = detail?.verified_resolutions?.[0]
  const displayedResolution = resolutionResult
    ? detail?.verified_resolutions?.find((item) => item.id === resolutionResult.resolution_id) || existingResolution
    : existingResolution
  const alreadyResolved = Boolean(resolutionResult || existingResolution)
  const retentionStatus = resolutionResult
    ? resolutionResult.memory_retention_status ?? null
    : detail?.memory_retention_status ?? null
  return <section className="panel engineer-review-panel" aria-labelledby="engineer-review-heading">
    <div className="panel-heading"><div><div className="section-kicker">{result ? `HUMAN-IN-THE-LOOP · RUN ${result.investigation_id.slice(0, 8).toUpperCase()}` : 'PERSISTED VERIFIED RESOLUTION'}</div><h2 id="engineer-review-heading">Engineer review</h2><p>AI findings stay hypotheses until an engineer explicitly confirms a verified outcome.</p></div><ShieldCheck size={18} className="heading-accent"/></div>
    {alreadyResolved ? <div className="review-saved-state"><div className="review-status-line"><CheckCircle2 size={16}/><strong>Verified resolution recorded</strong><span className={`retention-pill ${retentionStatus || 'unknown'}`}>Hindsight retain: {retentionStatus ? retentionStatus.replace('_', ' ') : 'status unknown'}</span></div><p><b>Root cause:</b> {displayedResolution?.root_cause_summary || rootCause || detail?.root_cause_summary || 'See the verified incident record.'}</p>{displayedResolution?.resolution_summary && <p><b>Resolution:</b> {displayedResolution.resolution_summary}</p>}{retentionStatus !== 'success' && retentionStatus !== 'skipped_duplicate' && <><p className="review-warning">{retentionStatus === 'failed' ? 'The incident record is resolved, but Hindsight retention failed. Do not treat the resolution as learned memory.' : 'No retention result is recorded for this resolution. Do not treat it as learned memory.'}</p><button type="button" className="button button-secondary button-small" onClick={retryResolutionRetention} disabled={retentionBusy}>{retentionBusy ? <><LoaderCircle size={14} className="spin"/> Retrying retention…</> : <><RefreshCw size={14}/> Retry Hindsight retention</>}</button></>}{resolutionError && <div className="inline-error"><AlertCircle size={15}/>{resolutionError}</div>}</div> : <form className="engineer-review-form" onSubmit={submitResolution}>
      <div className="review-form-intro"><span className="provenance-tag provenance-amber"><i/>AI hypotheses are not verified facts</span><span>Complete only after checking the outcome in your synthetic/local environment.</span></div>
      <div className="form-grid"><Field label="Verified root cause" required full><textarea required minLength="1" maxLength="20000" rows="3" value={rootCause} onChange={(event) => setRootCause(event.target.value)} placeholder="Enter the cause you verified from the available evidence." /></Field><Field label="Resolution applied and verified" required full><textarea required minLength="1" maxLength="20000" rows="3" value={resolution} onChange={(event) => setResolution(event.target.value)} placeholder="Describe the corrective action actually applied and how it was verified." /></Field><Field label="Engineer display name · not authenticated" required><input required maxLength="150" value={verifiedBy} onChange={(event) => setVerifiedBy(event.target.value)} placeholder="Name for the audit record" /></Field><div className="review-identity-note">A typed name is recorded as supplied; this app does not authenticate identity.</div></div>
      <label className="confirmation-check"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /><span>I explicitly confirm that this root cause and resolution are verified.</span></label>
      {resolutionError && <div className="inline-error"><AlertCircle size={15}/>{resolutionError}</div>}
      <div className="form-actions"><span>Only this explicit confirmation calls the verified-resolution endpoint and requests Hindsight retention.</span><button className="button button-primary" disabled={resolutionBusy || !confirmed || !rootCause.trim() || !resolution.trim() || !verifiedBy.trim()}>{resolutionBusy ? <><LoaderCircle size={15} className="spin"/> Saving & retaining…</> : <><ShieldCheck size={15}/> Confirm verified resolution</>}</button></div>
    </form>}
    {resolutionResult && <div className={`retention-result ${retentionStatus || 'unknown'}`} role="status"><span>{retentionStatus === 'success' ? 'HINDSIGHT RETAIN SUCCEEDED' : retentionStatus === 'skipped_duplicate' ? 'DUPLICATE RETENTION SKIPPED' : retentionStatus === 'failed' ? 'HINDSIGHT RETAIN FAILED' : 'HINDSIGHT RETENTION STATUS UNKNOWN'}</span><p>{retentionStatus === 'success' ? 'The API reported that the verified resolution was retained.' : retentionStatus === 'skipped_duplicate' ? 'The API reported an existing stable memory; no duplicate retain was performed.' : retentionStatus === 'failed' ? `The resolution is recorded, but the memory operation failed${resolutionResult.memory_error_category ? ` (${resolutionResult.memory_error_category})` : ''}.` : 'No retention result was returned. Do not treat this resolution as learned memory.'}</p></div>}
    <details className="failed-approach-details"><summary><span><ArrowDownRight size={15}/> Record an unsuccessful troubleshooting approach</span><small>Separate failure memory · optional</small></summary>
      {failureResult && <div className={`retention-result ${failureResult.memory_retention_status || 'unknown'}`} role="status"><span>{failureResult.memory_retention_status === 'success' ? 'FAILED APPROACH RETAINED' : failureResult.memory_retention_status === 'skipped_duplicate' ? 'DUPLICATE SKIPPED' : failureResult.memory_retention_status === 'failed' ? 'RETENTION FAILED' : 'RETENTION STATUS UNKNOWN'}</span><p>{failureResult.memory_retention_status === 'success' ? 'Hindsight reported success for a separate failed-approach memory.' : failureResult.memory_retention_status === 'skipped_duplicate' ? 'The stable memory already exists; no duplicate retain was performed.' : failureResult.memory_retention_status === 'failed' ? `The approach was submitted, but Hindsight retention failed${failureResult.memory_error_category ? ` (${failureResult.memory_error_category})` : ''}. The form values remain available for retry.` : 'No retention result was returned. Do not treat this approach as learned memory.'}</p></div>}
      {(!failureResult || !['success', 'skipped_duplicate'].includes(failureResult.memory_retention_status)) && <form className="engineer-review-form failed-approach-form" onSubmit={(event) => { event.preventDefault(); submitFailedApproach() }}>
        <div className="form-grid"><Field label="Troubleshooting action tried" required full><textarea required maxLength="10000" rows="2" value={attemptedAction} onChange={(event) => setAttemptedAction(event.target.value)} placeholder="What action was attempted?" /></Field><Field label="Observed outcome" required full><textarea required maxLength="10000" rows="2" value={outcome} onChange={(event) => setOutcome(event.target.value)} placeholder="What happened, and why was this approach unsuccessful?" /></Field><Field label="Engineer display name · not authenticated" required><input required maxLength="150" value={recordedBy} onChange={(event) => setRecordedBy(event.target.value)} placeholder="Name for the audit record" /></Field><div className="review-identity-note">A typed name is not identity verification.</div></div>
        {failureError && <div className="inline-error"><AlertCircle size={15}/>{failureError}</div>}
        <div className="form-actions"><span>Stored as historical failure context, not as a guaranteed outcome.</span><button className="button button-secondary" disabled={failureBusy || !attemptedAction.trim() || !outcome.trim() || !recordedBy.trim()}>{failureBusy ? <><LoaderCircle size={15} className="spin"/> Retrying…</> : <><Plus size={14}/>{failureResult ? 'Retry retention' : 'Record failed approach'}</>}</button></div>
      </form>}
    </details>
  </section>
}

function InvestigationResult({ result, incident, detail, onResolutionRecorded, onDataChanged, notify }) {
  const analysis = result.analysis
  return <div className="result-stack"><div className="result-banner"><div className="result-banner-icon"><Check size={17}/></div><div className="result-banner-copy"><div><span className="section-kicker">INVESTIGATION COMPLETE</span><span className="run-id">RUN {result.investigation_id.slice(0, 8).toUpperCase()}</span></div><h2>{analysis.summary}</h2><p>{incident.incident_number} · {result.model_identifier} · MEMORY_{result.memory_mode.toUpperCase()}</p></div><span className="status-chip success">Succeeded</span></div>
    <div className="provenance-key panel"><span className="section-kicker">EVIDENCE PROVENANCE</span><div><ProvenanceTag value="current_incident_evidence"/><ProvenanceTag value="historical_hindsight_memory"/><ProvenanceTag value="ai_generated_hypothesis"/><ProvenanceTag value="engineer_verified_root_cause"/></div></div>
    <div className="analysis-section"><div className="section-heading"><div><div className="section-kicker">POTENTIAL ROOT CAUSES</div><h2>Hypotheses to validate</h2></div><span className="count-chip">{analysis.potential_root_causes.length} hypotheses</span></div>{analysis.potential_root_causes.length ? <div className="hypothesis-list">{analysis.potential_root_causes.map((item, index) => <details className="hypothesis-disclosure" key={`${item.cause}-${index}`}><summary><span>HYPOTHESIS {String(index + 1).padStart(2, '0')}</span><strong>{item.cause}</strong><span>{Math.round(item.confidence * 100)}% confidence</span></summary><article className="panel hypothesis-card"><div className="hypothesis-top"><span className="hypothesis-rank">HYPOTHESIS {String(index + 1).padStart(2, '0')}</span><ProvenanceTag value={item.provenance}/></div><p>{item.rationale}</p><EvidenceRefs items={item.supporting_evidence}/><div className="hypothesis-foot"><span><ShieldCheck size={14}/>Not a verified root cause</span><span>{Math.round(item.confidence * 100)}% model confidence</span></div></article></details>)}</div> : <EmptyState icon={CircleHelp} title="No root-cause hypotheses returned" copy="The model returned no hypotheses for this evidence."/>}</div>
    <div className="analysis-section"><div className="section-heading"><div><div className="section-kicker">INVESTIGATION PLAN</div><h2>Recommended next steps</h2></div><span className="count-chip">Engineer review required</span></div>{analysis.recommended_steps.length ? <div className="recommendation-list">{analysis.recommended_steps.map((step, index) => <article className="panel recommendation-card" key={`${step.step}-${index}`}><div className="step-number">{String(index + 1).padStart(2, '0')}</div><div className="recommendation-body"><div className="recommendation-title-row"><h3>{step.step}</h3><ProvenanceTag value={step.provenance}/></div><p>{step.rationale}</p><EvidenceRefs items={step.supporting_evidence}/><span className="review-required"><ShieldCheck size={13}/> Requires engineer review</span></div></article>)}</div> : <EmptyState icon={CircleHelp} title="No steps returned" copy="No recommendations were included in this model response."/>}</div>
    <EngineerReviewPanel result={result} incident={incident} detail={detail} onResolutionRecorded={onResolutionRecorded} onDataChanged={onDataChanged} notify={notify} />
    <div className="result-bottom-grid"><article className="panel memory-result-card"><div className="panel-heading"><div><div className="section-kicker">HINDSIGHT · {result.memory_mode === 'off' ? 'HISTORICAL RECALL SKIPPED' : `HISTORICAL RECALL COMPLETED · ${analysis.historical_memories.length} RESULTS`}</div><h2>Historical context</h2></div><BrainCircuit size={16} className="violet-text"/></div>{result.memory_mode === 'off' ? <div className="memory-off-note"><span className="memory-off-icon"><ArrowDownRight size={16}/></span><div><strong>Memory retrieval skipped</strong><p>MEMORY_OFF used current incident evidence only. No Hindsight recall was performed.</p></div></div> : analysis.historical_memories.length ? <div className="memory-result-list">{analysis.historical_memories.map((memory) => <div className={`memory-result-item ${memory.tags?.includes('failed-approach') ? 'failure-memory' : ''}`} key={memory.id}><div className="memory-result-top"><ProvenanceTag value="historical_hindsight_memory"/><span>{memory.tags?.includes('failed-approach') ? 'HISTORICAL FAILED APPROACH · CAUTION' : memory.tags?.join(' · ') || 'Historical record'}</span></div><p>{memory.text}</p>{memory.tags?.includes('failed-approach') && <small className="failure-memory-note">Previously reported as unsuccessful; outcomes may differ in this incident.</small>}<code>{memory.id}</code></div>)}</div> : <EmptyState icon={History} title="No relevant memories returned" copy="Hindsight recall succeeded but returned no historical matches."/>}</article><article className="panel confidence-card"><div className="panel-heading"><div><div className="section-kicker">MODEL LIMITATIONS</div><h2>Confidence & gaps</h2></div><Fingerprint size={16} className="heading-accent"/></div><div className="confidence-score"><span>Assessment</span><strong>{Math.round(analysis.confidence.score * 100)}<small>%</small></strong></div><div className="limitation-list">{analysis.confidence.limitations.map((item, index) => <div key={index}><AlertCircle size={13}/>{item}</div>)}</div>{analysis.information_still_required.length > 0 && <div className="required-info"><strong>Still needed</strong>{analysis.information_still_required.map((item, index) => <span key={index}><ChevronRight size={13}/>{item}</span>)}</div>}</article></div>
  </div>
}

function ComparisonPage({ incidents, selectedIncidentId, setSelectedIncidentId, selectedIncident, onRunCreated, notify }) {
  const [loading, setLoading] = useState(false)
  const [comparison, setComparison] = useState(null)
  const [error, setError] = useState('')
  async function compare() {
    if (!selectedIncident) return
    setLoading(true); setError(''); setComparison(null)
    try {
      const off = await api(`/incidents/${selectedIncident.id}/investigate`, { method: 'POST', body: JSON.stringify({ memory_mode: 'MEMORY_OFF' }) })
      onRunCreated(off, selectedIncident)
      const on = await api(`/incidents/${selectedIncident.id}/investigate`, { method: 'POST', body: JSON.stringify({ memory_mode: 'MEMORY_ON' }) })
      onRunCreated(on, selectedIncident)
      setComparison({ off, on })
      notify('success', 'Both investigation runs completed. Review their actual outputs below.')
    } catch (requestError) { setError(requestError.message); notify('error', requestError.message) }
    finally { setLoading(false) }
  }
  const offAnalysis = comparison?.off?.analysis
  const onAnalysis = comparison?.on?.analysis
  return <>
    <PageHeading eyebrow="CONTROLLED INVESTIGATION COMPARISON" title="Memory changes the context." subtitle="Same incident. Two separate runs. Compare what the model received and returned." action={<div className="compare-trust"><ShieldCheck size={15}/>Real results · No performance claims</div>} />
    <div className="comparison-control panel"><div className="comparison-intro"><div className="comparison-icon"><Layers3 size={19}/></div><div><strong>Choose an incident to compare</strong><span>Each mode creates its own investigation run against the same recorded incident.</span></div></div><div className="compare-controls"><div className="select-shell"><SquareActivity size={15}/><select aria-label="Select incident" value={selectedIncidentId} onChange={(event) => { setSelectedIncidentId(event.target.value); setComparison(null) }}><option value="">Select incident…</option>{incidents.map((item) => <option value={item.id} key={item.id}>{item.incident_number} · {item.title}</option>)}</select><ChevronDown size={15}/></div><button className="button button-primary" onClick={compare} disabled={!selectedIncident || loading}>{loading ? <><LoaderCircle size={16} className="spin"/> Running both modes…</> : <><Layers3 size={16}/> Run comparison <ArrowRight size={15}/></>}</button></div></div>
    <div className="comparison-mode-labels"><div className="mode-heading mode-off"><span className="mode-heading-dot"/><div><strong>MEMORY_OFF</strong><small>Current evidence only</small></div>{comparison?.off && <span className="run-state"><CheckCircle2 size={14}/>Run complete</span>}</div><div className="comparison-vs">VS</div><div className="mode-heading mode-on"><span className="mode-heading-dot"/><div><strong>MEMORY_ON</strong><small>Current evidence + Hindsight recall</small></div>{comparison?.on && <span className="run-state"><CheckCircle2 size={14}/>Run complete</span>}</div></div>
    {error && <div className="alert alert-error"><AlertCircle size={17}/><div><strong>Comparison incomplete</strong><span>{error}{comparison?.off ? ' MEMORY_OFF completed, but MEMORY_ON did not; no two-mode comparison is shown.' : ''}</span></div></div>}
    {loading && <div className="comparison-loading"><div className="compare-loader"><span/><span/><span/></div><div><strong>Running two investigations</strong><p>First without memory, then with a real Hindsight recall. No result is assumed.</p></div></div>}
    {comparison && <><div className="comparison-context"><span>INCIDENT CONTEXT</span><strong>{selectedIncident?.incident_number}</strong><b>{selectedIncident?.title}</b><span>{selectedIncident?.service_name} · {selectedIncident?.severity}</span></div><div className="comparison-grid"><ComparisonColumn mode="off" analysis={offAnalysis} run={comparison.off}/><ComparisonColumn mode="on" analysis={onAnalysis} run={comparison.on}/></div><div className="comparison-footnote"><CircleHelp size={15}/><span>Differences below describe returned content only. They do not imply greater accuracy, confidence, or reduced MTTR.</span></div></>}
    {!comparison && !loading && !error && <div className="panel comparison-empty"><div className="compare-art"><div className="compare-art-side"><Database size={18}/><span>Evidence</span></div><div className="compare-art-core"><BrainCircuit size={21}/></div><div className="compare-art-side violet"><History size={18}/><span>Memory</span></div></div><h2>See what memory adds to context</h2><p>Run a paired comparison to see current evidence alone beside the same incident with relevant historical Hindsight memories.</p><div className="comparison-truth-list"><span><Check size={14}/>Same incident context</span><span><Check size={14}/>Separate, recorded runs</span><span><Check size={14}/>Actual results only</span></div></div>}
  </>
}

function ComparisonColumn({ mode, analysis, run }) {
  const on = mode === 'on'
  return <article className={`comparison-column panel ${on ? 'column-memory-on' : 'column-memory-off'}`}><div className="comparison-column-head"><div className={`column-mode-icon ${on ? 'violet' : ''}`}>{on ? <BrainCircuit size={17}/> : <Database size={17}/>}</div><div><strong>{on ? 'MEMORY_ON' : 'MEMORY_OFF'}</strong><span>{on ? 'Hindsight context included' : 'No memory recall performed'}</span></div><span className="run-id-small">{run.investigation_id.slice(0, 8).toUpperCase()}</span></div><div className="comparison-summary"><div className="section-kicker">AI SUMMARY</div><p>{analysis.summary}</p><span className="model-note">{run.model_identifier}</span></div><div className="comparison-subsection"><div className="comparison-subheading"><strong>Root-cause hypotheses</strong><span>{analysis.potential_root_causes.length}</span></div>{analysis.potential_root_causes.length ? analysis.potential_root_causes.map((item, index) => <div className="comparison-result-item" key={index}><div className="comparison-item-label"><ProvenanceTag value="ai_generated_hypothesis"/><span>{Math.round(item.confidence * 100)}% confidence</span></div><strong>{item.cause}</strong><p>{item.rationale}</p></div>) : <p className="muted-empty">No hypotheses returned.</p>}</div><div className="comparison-subsection"><div className="comparison-subheading"><strong>Recommended steps</strong><span>{analysis.recommended_steps.length}</span></div>{analysis.recommended_steps.length ? analysis.recommended_steps.map((item, index) => <div className="comparison-result-item recommendation-compare" key={index}><div className="compare-step-number">{String(index + 1).padStart(2, '0')}</div><div><strong>{item.step}</strong><p>{item.rationale}</p><span className="review-required"><ShieldCheck size={12}/>Engineer review required</span></div></div>) : <p className="muted-empty">No steps returned.</p>}</div><div className="comparison-subsection memory-subsection"><div className="comparison-subheading"><strong>Retrieved historical memories</strong><span>{analysis.historical_memories.length}</span></div>{on ? analysis.historical_memories.length ? analysis.historical_memories.map((memory) => <div className="mini-memory" key={memory.id}><ProvenanceTag value="historical_hindsight_memory"/>{memory.tags?.includes('failed-approach') && <span className="failure-memory-note">Historical failed approach · caution</span>}<p>{memory.text}</p><code>{memory.id}</code></div>) : <div className="memory-empty-inline"><History size={15}/><span>Recall returned no matching memories for this incident.</span></div> : <div className="memory-empty-inline"><ArrowDownRight size={15}/><span>Recall was intentionally skipped in this run.</span></div>}</div></article>
}

function MemoryPage({ incidents, selectedIncidentId, setSelectedIncidentId, onNavigate, health }) {
  const [entries, setEntries] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!selectedIncidentId) { setEntries(null); setLoading(false); setError(''); return }
    let active = true
    setLoading(true); setError('')
    api(`/incidents/${selectedIncidentId}/memories`).then((data) => { if (active) setEntries(data.entries || []) }).catch((requestError) => { if (active) { setEntries(null); setError(requestError.message) } }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [selectedIncidentId])
  return <><PageHeading eyebrow="PERSISTENT CONTEXT · HINDSIGHT" title="Memory explorer" subtitle="Inspect historical knowledge retrieved for a real incident. Memory supports investigation; it does not prove current root cause." action={<div className="memory-bank-status"><span className="status-pulse violet-pulse"/>{hindsightBankLabel(health)}</div>} />
    <div className="memory-query-bar panel"><div><div className="section-kicker">RECALL CONTEXT</div><span>Select an incident to make an actual Hindsight recall request.</span></div><div className="select-shell"><SquareActivity size={15}/><select value={selectedIncidentId} onChange={(event) => setSelectedIncidentId(event.target.value)} aria-label="Select incident for memory recall"><option value="">Select incident…</option>{incidents.map((item) => <option key={item.id} value={item.id}>{item.incident_number} · {item.title}</option>)}</select><ChevronDown size={15}/></div></div>
    {error && <div className="alert alert-error"><AlertCircle size={16}/>{error}</div>}{loading && <div className="panel memory-loading"><LoaderCircle size={18} className="spin"/><span>Recalling relevant historical knowledge…</span></div>}{entries && !loading && (entries.length ? <div className="memory-explorer-grid">{entries.map((entry) => <article className="panel memory-card" key={entry.id}><div className="memory-card-top"><ProvenanceTag value={entry.provenance}/><span className="memory-type-tag">{entry.memory_type || 'historical'}</span></div><p>{entry.summary}</p><div className="memory-card-context"><span><History size={13}/>{entry.context || 'Historical incident knowledge'}</span>{entry.occurred_start && <span><Clock3 size={13}/>{formatDate(entry.occurred_start)}</span>}</div><div className="memory-card-foot"><code>{entry.id}</code><span>{entry.tags?.join(' · ')}</span></div></article>)}</div> : <div className="panel memory-no-results"><div className="empty-orbit violet-orbit"><History size={20}/></div><h2>No relevant memories returned</h2><p>Hindsight recall completed for the selected incident but returned no historical entries. No memories have been invented or inferred.</p><button className="button button-secondary button-small" onClick={() => onNavigate('investigate')}>Continue investigation <ArrowRight size={14}/></button></div>)}{!entries && !loading && !error && <div className="panel memory-no-results"><div className="empty-orbit violet-orbit"><BrainCircuit size={20}/></div><h2>Start with an incident</h2><p>Select an incident above to retrieve its relevant historical Hindsight memories.</p></div>}
  </>
}

function PostmortemPage({ incidents, notify, onNavigate }) {
  const [postmortems, setPostmortems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedPm, setSelectedPm] = useState(null)
  const [viewMode, setViewMode] = useState('rendered')
  const [generatingId, setGeneratingId] = useState(null)

  const loadPostmortems = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api('/postmortems')
      setPostmortems(data.items || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadPostmortems()
  }, [loadPostmortems])

  async function openPostmortem(id) {
    try {
      const data = await api(`/postmortems/${id}`)
      setSelectedPm(data)
      setViewMode('rendered')
    } catch (err) {
      notify('error', err.message)
    }
  }

  async function generatePostmortem(incidentId) {
    setGeneratingId(incidentId)
    try {
      const data = await api(`/incidents/${incidentId}/postmortem`, { method: 'POST' })
      notify('success', 'Postmortem checked against the latest verified incident record.')
      await loadPostmortems()
      setSelectedPm(data)
      setViewMode('rendered')
    } catch (err) {
      notify('error', err.message)
    } finally {
      setGeneratingId(null)
    }
  }

  async function downloadPostmortem(pm) {
    if (!pm?.id) return
    try {
      const response = await fetch(`${API_ROOT}/postmortems/${pm.id}/download`)
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        const message = body?.detail?.message || body?.detail || 'The postmortem download could not be completed.'
        throw new Error(typeof message === 'string' ? message : 'The postmortem download could not be completed.')
      }
      const blob = await response.blob()
      const disposition = response.headers.get('content-disposition') || ''
      const filename = disposition.match(/filename="([^"]+)"/i)?.[1] || `postmortem-${pm.incident_number || pm.id.slice(0, 8)}.md`
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.setTimeout(() => URL.revokeObjectURL(url), 0)
      setSelectedPm((current) => current?.id === pm.id ? { ...current, downloaded_count: (current.downloaded_count || 0) + 1 } : current)
      setPostmortems((current) => current.map((item) => item.id === pm.id ? { ...item, downloaded_count: (item.downloaded_count || 0) + 1 } : item))
      notify('success', 'Postmortem markdown downloaded.')
    } catch (error) { notify('error', error.message) }
  }

  const resolvedIncidents = incidents.filter((inc) => inc.status === 'resolved')
  const ungeneratedResolved = resolvedIncidents.filter(
    (inc) => !postmortems.some((pm) => pm.incident_id === inc.id)
  )

  if (selectedPm) {
    return (
      <>
        <PageHeading
          eyebrow="POSTMORTEM DOCUMENT"
          title={selectedPm.title}
          subtitle={`Incident: ${selectedPm.incident_number} · Status: ${selectedPm.status.toUpperCase()}`}
          action={
            <div className="postmortem-actions">
              <button
                className="button button-secondary button-small"
                onClick={() => setViewMode((m) => (m === 'rendered' ? 'raw' : 'rendered'))}
              >
                {viewMode === 'rendered' ? 'Raw markdown' : 'Formatted view'}
              </button>
              <button
                className="button button-secondary button-small"
                disabled={generatingId === selectedPm.incident_id}
                onClick={() => generatePostmortem(selectedPm.incident_id)}
              >
                {generatingId === selectedPm.incident_id ? <><LoaderCircle size={13} className="spin"/> Updating…</> : 'Refresh from latest resolution'}
              </button>
              <button
                className="button button-primary button-small"
                onClick={() => downloadPostmortem(selectedPm)}
              >
                <Download size={14} /> Download .md
              </button>
              <button
                className="button button-secondary button-small"
                onClick={() => setSelectedPm(null)}
              >
                <X size={14} /> Close
              </button>
            </div>
          }
        />
        <article className="panel postmortem-viewer">
          {viewMode === 'raw' ? (
            <textarea
              className="postmortem-raw-box"
              readOnly
              value={selectedPm.body_markdown || ''}
            />
          ) : (
            <div className="postmortem-doc">
              <div className="postmortem-callout-verified">
                <strong><ShieldCheck size={14} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 4 }} />ENGINEER-VERIFIED INCIDENT RECORD</strong>
                <p style={{ margin: '4px 0 0' }}>This postmortem is grounded in an explicitly confirmed root cause and resolution. Unverified AI hypotheses are isolated strictly for audit reference.</p>
              </div>
              <RenderPostmortemMarkdown content={selectedPm.body_markdown || ''} />
            </div>
          )}
        </article>
      </>
    )
  }

  return (
    <>
      <PageHeading
        eyebrow="ENGINEER REVIEW WORKSPACE"
        title="Postmortem center"
        subtitle="Preserve verified causes, impact, and lessons in a reviewable incident record."
        action={
          <button className="button button-secondary button-small" onClick={loadPostmortems} disabled={loading}>
            <RefreshCw size={13} className={loading ? 'spin' : ''} /> Refresh
          </button>
        }
      />
      <div className="postmortem-container">
        {error && <div className="alert alert-error"><AlertCircle size={17} /><span>{error}</span></div>}

        {ungeneratedResolved.length > 0 && (
          <section className="panel" aria-label="Eligible incidents">
            <div className="panel-heading">
              <div>
                <div className="section-kicker">ELIGIBLE RESOLVED INCIDENTS</div>
                <h2>Generate postmortems from verified resolutions</h2>
              </div>
              <span className="count-chip">{ungeneratedResolved.length} ready</span>
            </div>
            <div className="postmortem-grid">
              {ungeneratedResolved.map((inc) => (
                <div className="panel postmortem-card" key={inc.id}>
                  <div className="postmortem-card-top">
                    <div>
                      <span className="incident-ref">{inc.incident_number}</span>
                      <h3>{inc.title}</h3>
                    </div>
                    <SeverityBadge value={inc.severity} />
                  </div>
                  <div className="postmortem-card-foot">
                    <span>{inc.service_name}</span>
                    <button
                      className="button button-primary button-small"
                      disabled={generatingId === inc.id}
                      onClick={() => generatePostmortem(inc.id)}
                    >
                      {generatingId === inc.id ? (
                        <><LoaderCircle size={13} className="spin" /> Generating…</>
                      ) : (
                        <><FileText size={13} /> Generate postmortem</>
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="panel" aria-label="Generated postmortems">
          <div className="panel-heading">
            <div>
              <div className="section-kicker">OFFICIAL POSTMORTEMS</div>
              <h2>Incident postmortem archive <span className="inline-count">{postmortems.length}</span></h2>
            </div>
          </div>
          {loading && !postmortems.length ? (
            <div className="panel memory-loading"><LoaderCircle size={18} className="spin" /><span>Loading postmortem archive…</span></div>
          ) : postmortems.length ? (
            <div className="incident-table-wrap">
              <table className="incident-table">
                <thead>
                  <tr>
                    <th>Incident</th>
                    <th>Document Title</th>
                    <th>Status</th>
                    <th>Generated</th>
                    <th>Downloads</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {postmortems.map((pm) => (
                    <tr key={pm.id} onClick={() => openPostmortem(pm.id)}>
                      <td>
                        <span className="incident-ref">{pm.incident_number}</span>
                      </td>
                      <td>
                        <strong>{pm.title}</strong>
                      </td>
                      <td>
                        <StatusBadge value={pm.status} />
                      </td>
                      <td className="date-cell">{formatDate(pm.created_at)}</td>
                      <td>{pm.downloaded_count}</td>
                      <td>
                        <button className="button button-secondary button-small" onClick={(e) => { e.stopPropagation(); openPostmortem(pm.id); }}>
                          View <ChevronRight size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon={FileText}
              title="No postmortems generated yet"
              copy="Once an incident has an engineer-verified resolution, generate an official postmortem here. IncidentIQ does not produce unverified placeholder reports."
              action={
                <button className="button button-secondary button-small" onClick={() => onNavigate('investigate')}>
                  <Radar size={14} /> Go to investigations
                </button>
              }
            />
          )}
        </section>
      </div>
    </>
  )
}

function RenderPostmortemMarkdown({ content }) {
  const blocks = parsePostmortemMarkdown(content)
  return (
    <div className="postmortem-markdown-content">
      {blocks.map((block, index) => {
        if (block.type === 'rule') return <hr key={index} />
        if (block.type === 'heading') {
          const Tag = `h${block.level}`
          return <Tag key={index}><RenderInlineMarkdown tokens={block.children} /></Tag>
        }
        if (block.type === 'paragraph') return <p key={index}><RenderInlineMarkdown tokens={block.children} /></p>
        if (block.type === 'quote') {
          const quoteText = block.children.map((tokens) => inlineMarkdownText(tokens)).join(' ')
          const warning = quoteText.includes('AUDIT REFERENCE ONLY') || quoteText.includes('Unverified AI')
          return <blockquote key={index} className={warning ? 'postmortem-callout-warning' : ''}>
            {block.children.map((tokens, lineIndex) => <p key={lineIndex}><RenderInlineMarkdown tokens={tokens} /></p>)}
          </blockquote>
        }
        if (block.type === 'unorderedList' || block.type === 'orderedList') {
          const Tag = block.type === 'orderedList' ? 'ol' : 'ul'
          return <Tag key={index}>{block.items.map((tokens, itemIndex) => <li key={itemIndex}><RenderInlineMarkdown tokens={tokens} /></li>)}</Tag>
        }
        if (block.type === 'codeBlock') return <pre key={index}><code>{block.value}</code></pre>
        return null
      })}
    </div>
  )
}

function RenderInlineMarkdown({ tokens }) {
  return tokens.map((token, index) => {
    if (token.type === 'strong') return <strong key={index}><RenderInlineMarkdown tokens={token.children} /></strong>
    if (token.type === 'emphasis') return <em key={index}><RenderInlineMarkdown tokens={token.children} /></em>
    if (token.type === 'code') return <code key={index}>{token.value}</code>
    return <span key={index}>{token.value}</span>
  })
}

function inlineMarkdownText(tokens) {
  return tokens.map((token) => token.value ?? inlineMarkdownText(token.children || [])).join('')
}

function LoadingAnalysis({ mode }) { return <div className="panel loading-analysis"><div className="loading-visual"><div className="loading-ring"/><div className="loading-core"><BrainCircuit size={22}/></div></div><div className="section-kicker">INVESTIGATION IN PROGRESS</div><h2>Following the evidence trail</h2><p>{mode === 'on' ? 'Retrieving relevant Hindsight memories, then asking Groq to analyze the combined context.' : 'Analyzing the current incident evidence. Hindsight recall is skipped in MEMORY_OFF.'}</p><div className="loading-steps"><span className="done"><Check size={12}/>Incident context loaded</span>{mode === 'on' ? <span className="active"><LoaderCircle size={12} className="spin"/>Hindsight recall</span> : <span className="skipped"><ArrowDownRight size={12}/>Hindsight skipped</span>}<span><Sparkles size={12}/>Structured AI reasoning</span><span><ShieldCheck size={12}/>Engineer review</span></div></div> }

function WorkflowStep({ number, title, active, muted, label, last }) { return <div className={`workflow-step ${active ? 'complete' : ''} ${muted ? 'muted' : ''} ${last ? 'last' : ''}`}><div className="workflow-rail"><span>{active ? <Check size={12}/> : number}</span></div><div className="workflow-copy"><strong>{title}</strong>{label && <em>{label}</em>}</div></div> }
function EvidenceRefs({ items }) { return <div className="evidence-refs">{items.map((item, index) => <span key={`${item.reference}-${index}`} title={item.relevance}><ProvenanceTag value={item.provenance}/><span className="evidence-ref-text">{item.reference.replace(/^(current|memory|verified):/, '')}</span></span>)}</div> }
function ProvenanceTag({ value }) { const [label, tone] = provenanceStyle[value] || ['Source', 'neutral']; return <span className={`provenance-tag provenance-${tone}`}><i/>{label}</span> }
function SeverityBadge({ value }) { return <span className={`severity-badge ${value || 'unknown'}`}><i/>{value || 'unknown'}</span> }
function StatusBadge({ value }) { const tone = value === 'resolved' || value === 'succeeded' || value === 'success' ? 'good' : value === 'failed' || value === 'critical' ? 'bad' : value === 'running' || value === 'investigating' ? 'active' : 'neutral'; return <span className={`status-badge ${tone}`}><i/>{value || 'unknown'}</span> }
function EmptyState({ icon: Icon, title, copy, action }) { return <div className="empty-state"><div className="empty-icon"><Icon size={19}/></div><h3>{title}</h3><p>{copy}</p>{action}</div> }
function PageHeading({ eyebrow, title, subtitle, action }) { return <div className="page-heading"><div><div className="page-eyebrow"><span className="eyebrow-line"/>{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>{action && <div className="heading-action">{action}</div>}</div> }
function formatRelative(value) { if (!value) return '—'; const time = new Date(value).getTime(); if (Number.isNaN(time)) return '—'; const seconds = Math.max(0, Math.floor((Date.now() - time) / 1000)); if (seconds < 60) return 'just now'; if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`; if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`; return `${Math.floor(seconds / 86400)}d ago` }
function formatDate(value) { if (!value) return '—'; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(date) }
function formatLongDate() { return new Intl.DateTimeFormat(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }).format(new Date()).toUpperCase() }

export default App
