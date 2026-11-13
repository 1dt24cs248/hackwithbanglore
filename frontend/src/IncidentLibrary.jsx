import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, ExternalLink, Search, ShieldCheck } from 'lucide-react'
import { queryString } from './libraryFilters.js'

const emptyListing = { items: [], total: 0, page: 1, limit: 12 }

function dateLabel(value) {
  if (!value) return 'Date not disclosed'
  return new Date(`${value}T12:00:00Z`).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' })
}

export default function IncidentLibrary({ requestApi, onInvestigate }) {
  const [summary, setSummary] = useState(null)
  const [listing, setListing] = useState(emptyListing)
  const [selected, setSelected] = useState(null)
  const [filters, setFilters] = useState({ search: '', company: '', category: '', year: '', severity: '', service: '', incident_type: '', verification_status: 'verified' })
  const [page, setPage] = useState(1)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [showGroundTruth, setShowGroundTruth] = useState(false)
  const [revealedCardIds, setRevealedCardIds] = useState(() => new Set())
  const filterKey = JSON.stringify(filters)

  useEffect(() => {
    let active = true
    requestApi('/library/summary').then((data) => { if (active) setSummary(data) }).catch((e) => { if (active) setError(e.message) })
    return () => { active = false }
  }, [requestApi])

  useEffect(() => {
    let active = true
    setBusy(true)
    setError('')
    requestApi(`/library/incidents?${queryString(filters, page)}`).then((data) => {
      if (active) { setListing(data); setSelected(null); setShowGroundTruth(false) }
    }).catch((e) => { if (active) setError(e.message) }).finally(() => { if (active) setBusy(false) })
    return () => { active = false }
  }, [requestApi, page, filterKey])

  const options = useMemo(() => ({
    companies: Object.keys(summary?.companies || {}),
    categories: Object.keys(summary?.categories || {}),
    years: (summary?.years || []).map(String),
    services: summary?.services || [],
    incidentTypes: summary?.incident_types || [],
  }), [summary])
  const categoryChart = Object.entries(summary?.categories || {}).sort((a, b) => b[1] - a[1]).slice(0, 6)
  const companyChart = Object.entries(summary?.companies || {}).sort((a, b) => b[1] - a[1]).slice(0, 6)
  const categoryMaximum = Math.max(1, ...categoryChart.map(([, count]) => count))
  const companyMaximum = Math.max(1, ...companyChart.map(([, count]) => count))

  async function openDetail(id) {
    setBusy(true); setError(''); setShowGroundTruth(false)
    try { setSelected(await requestApi(`/library/incidents/${id}`)) }
    catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }

  const setFilter = (name, value) => { setFilters((current) => ({ ...current, [name]: value })); setPage(1) }
  const choices = (items) => <option value="">All</option>

  return <section className="library-page">
    <div className="page-heading"><div><div className="page-eyebrow"><span className="eyebrow-line"/> SOURCE-VERIFIED HISTORY</div><h1>Incident library</h1><p>Investigate documented production incidents. Published root cause stays separate from the evidence sent to the AI.</p></div></div>
    <div className="library-stats">
      <div><span>Verified incidents</span><strong>{summary?.verified_incidents ?? '—'}</strong></div>
      <div><span>Companies</span><strong>{Object.keys(summary?.companies || {}).length || '—'}</strong></div>
      <div><span>With published metrics</span><strong>{summary?.incidents_with_documented_metrics ?? '—'}</strong></div>
      <div><span>Covered categories</span><strong>{summary?.taxonomy?.filter((x) => x.covered).length ?? '—'} / {summary?.taxonomy?.length ?? '—'}</strong></div>
    </div>
    <div className="library-note"><ShieldCheck size={16}/><span>Every record in this collection is linked to an official primary source. The collection is curated and is not a representative sample of all outages.</span></div>
    <section className="library-insights" aria-label="Evidence snapshot charts">
      <div className="library-chart"><div><h2>Incidents by category</h2><span>Top categories · {summary?.verified_incidents || 0} verified records</span></div>{categoryChart.map(([name, count]) => <div className="library-bar-row" key={name}><span>{name}</span><div className="library-bar-track"><i style={{ width: `${count / categoryMaximum * 100}%` }}/></div><strong>{count}</strong></div>)}</div>
      <div className="library-chart"><div><h2>Incidents by company</h2><span>Top publishers · curated collection</span></div>{companyChart.map(([name, count]) => <div className="library-bar-row" key={name}><span>{name}</span><div className="library-bar-track"><i style={{ width: `${count / companyMaximum * 100}%` }}/></div><strong>{count}</strong></div>)}</div>
    </section>
    <div className="library-category-coverage"><strong>Taxonomy coverage:</strong> {summary?.taxonomy?.filter((x) => x.covered).length || 0} of {summary?.taxonomy?.length || 0} categories have at least one verified example. Categories with no examples are shown in the implementation report.</div>
    {error && <div className="alert alert-error" role="alert">{error}</div>}
    {selected ? <article className="library-detail">
      <button className="button button-secondary button-small" onClick={() => { setSelected(null); setShowGroundTruth(false) }}><ArrowLeft size={14}/> Back to results</button>
      <div className="library-detail-heading"><div><div className="library-meta">{selected.company} · {dateLabel(selected.incident_date)} · {selected.category}</div><h2>{selected.title}</h2></div><span className="severity-pill">{selected.severity}</span></div>
      <div className="library-detail-grid">
        <section><h3>Incident description</h3><p>{selected.investigation_summary}</p><h3>Customer impact</h3><p>{selected.customer_impact}</p><h3>Business impact</h3><p>{selected.business_impact}</p><h3>Symptoms</h3><ul>{selected.symptoms.map((item) => <li key={item}>{item}</li>)}</ul>
        <h3>Documented metrics</h3>{selected.documented_metrics.length ? <ul>{selected.documented_metrics.map((m) => <li key={m.name}><strong>{m.name}:</strong> {String(m.value)} {m.unit || ''} — {m.scope}. {m.evidence}</li>)}</ul> : <p>No original metrics disclosed in the primary source.</p>}
        <h3>Recovery</h3><ul>{selected.recovery_actions.map((item) => <li key={item}>{item}</li>)}</ul><h3>Prevention</h3><ul>{selected.preventive_actions.map((item) => <li key={item}>{item}</li>)}</ul>
        <h3>Evidence gaps</h3><ul>{(selected.data_gaps || []).map((item) => <li key={item}>{item}</li>)}</ul></section>
        <aside><div className="ground-truth-box"><strong>Blind investigation</strong><p>The actual root cause is withheld from the investigation payload. Reveal it only after reviewing the AI findings.</p><button className="button button-secondary button-small" onClick={() => setShowGroundTruth((value) => !value)}>{showGroundTruth ? 'Hide published ground truth' : 'Reveal published ground truth'}</button>{showGroundTruth && <div className="ground-truth-answer"><h3>Company-disclosed root cause</h3><p>{selected.technical_root_cause || 'The original source did not disclose a complete root cause.'}</p><p className="source-note">Ground truth is shown for evaluation; it was not sent as investigation evidence.</p></div>}</div>
        <h3>Original sources</h3>{selected.sources.map((source) => <p className="source-link" key={source.url}><a href={source.url} target="_blank" rel="noreferrer">{source.source_type.replaceAll('_', ' ')} <ExternalLink size={13}/></a><small>{source.evidence_notes}</small></p>)}{selected.duration && <p><strong>Reported duration:</strong> {selected.duration}</p>}{selected.environment && <p><strong>Environment:</strong> {selected.environment}</p>}
        <button className="button button-primary" onClick={() => onInvestigate(selected)}><Search size={14}/> Investigate this incident</button></aside>
      </div>
    </article> : <>
      <div className="library-filters">
        <label className="library-search"><Search size={15}/><input aria-label="Search incidents" value={filters.search} onChange={(e) => setFilter('search', e.target.value)} placeholder="Search title, description, company"/></label>
        <select aria-label="Filter company" value={filters.company} onChange={(e) => setFilter('company', e.target.value)}>{choices(options.companies)}{options.companies.map((v) => <option key={v}>{v}</option>)}</select>
        <select aria-label="Filter category" value={filters.category} onChange={(e) => setFilter('category', e.target.value)}>{choices(options.categories)}{options.categories.map((v) => <option key={v}>{v}</option>)}</select>
        <select aria-label="Filter year" value={filters.year} onChange={(e) => setFilter('year', e.target.value)}>{choices(options.years)}{options.years.map((v) => <option key={v}>{v}</option>)}</select>
        <select aria-label="Filter severity" value={filters.severity} onChange={(e) => setFilter('severity', e.target.value)}>{choices(['critical','high','medium','low'])}{['critical','high','medium','low'].map((v) => <option key={v}>{v}</option>)}</select>
        <select aria-label="Filter affected service" value={filters.service} onChange={(e) => setFilter('service', e.target.value)}>{choices(options.services)}{options.services.map((v) => <option key={v}>{v}</option>)}</select>
        <select aria-label="Filter incident type" value={filters.incident_type} onChange={(e) => setFilter('incident_type', e.target.value)}>{choices(options.incidentTypes)}{options.incidentTypes.map((v) => <option key={v}>{v}</option>)}</select>
        <select aria-label="Filter verification status" value={filters.verification_status} onChange={(e) => setFilter('verification_status', e.target.value)}>{choices(['verified','partially_verified','needs_review','rejected'])}{['verified','partially_verified','needs_review','rejected'].map((v) => <option key={v} value={v}>{v.replaceAll('_',' ')}</option>)}</select>
      </div>
      <div className="library-results-head">{busy ? 'Loading source-backed incidents…' : `${listing.total} verified incidents`} <span>Page {listing.page || page}</span></div>
      <div className="library-card-grid">{listing.items.map((item) => <article className="library-card" key={item.id}>
        <div className="library-card-top"><strong>{item.company}</strong><span>{dateLabel(item.incident_date)}</span></div><h2>{item.title}</h2><div className="library-tags"><span>{item.category}</span><span className="severity-pill">{item.severity}</span><span className="verified-tag"><ShieldCheck size={12}/> Verified source</span></div>
        <p><b>Business impact</b> {item.business_impact}</p>{revealedCardIds.has(item.id) ? <p><b>Published root cause summary</b> {item.technical_root_cause || 'Not disclosed by the source.'}</p> : <button className="library-reveal-link" onClick={() => setRevealedCardIds((current) => new Set(current).add(item.id))}>Reveal published root cause summary</button>}<div className="library-card-actions"><button className="button button-secondary button-small" onClick={() => openDetail(item.id)}>View details <ArrowRight size={13}/></button><button className="button button-primary button-small" onClick={() => onInvestigate(item)}><Search size={13}/> Investigate</button></div>
      </article>)}</div>
      {!listing.items.length && !busy && <div className="library-empty">No matching incidents. Adjust or clear the filters.</div>}
      <div className="library-pagination"><button className="button button-secondary button-small" disabled={page <= 1 || busy} onClick={() => setPage((p) => p - 1)}>Previous</button><span>{listing.total ? `${(page - 1) * listing.limit + 1}–${Math.min(page * listing.limit, listing.total)} of ${listing.total}` : '0 results'}</span><button className="button button-secondary button-small" disabled={page * listing.limit >= listing.total || busy} onClick={() => setPage((p) => p + 1)}>Next</button></div>
    </>}
  </section>
}
