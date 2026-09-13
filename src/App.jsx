import { useEffect, useState } from 'react'
import './App.css'

const API = '/api'
const terminal = new Set(['succeeded', 'failed'])

function App() {
  const [duration, setDuration] = useState(2)
  const [priority, setPriority] = useState(0)
  const [failUntil, setFailUntil] = useState(0)
  const [maxAttempts, setMaxAttempts] = useState(3)
  const [key, setKey] = useState(() => crypto.randomUUID())
  const [jobs, setJobs] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('queue-job-ids') || '[]')
      return Array.isArray(saved) ? saved.map((id) => ({ id, status: 'queued' })) : []
    } catch { return [] }
  })
  const [selectedId, setSelectedId] = useState(() => {
    try { return JSON.parse(localStorage.getItem('queue-job-ids') || '[]')[0] || null }
    catch { return null }
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const jobIds = jobs.map((job) => job.id).join(',')
  useEffect(() => {
    if (!jobIds) return undefined
    let cancelled = false
    const refresh = async () => {
      const results = await Promise.allSettled(jobIds.split(',').map(async (id) => {
        const response = await fetch(`${API}/jobs/${id}`)
        if (!response.ok) throw new Error(`Could not load job ${id}`)
        return response.json()
      }))
      if (!cancelled) setJobs((current) => current.map((job, index) =>
        results[index]?.status === 'fulfilled' ? results[index].value : job
      ))
    }
    refresh()
    const timer = setInterval(refresh, 1500)
    return () => { cancelled = true; clearInterval(timer) }
  }, [jobIds])

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const response = await fetch(`${API}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idempotency_key: key,
          payload: { duration: Number(duration), fail_until_attempt: Number(failUntil) },
          priority: Number(priority),
          max_attempts: Number(maxAttempts),
        }),
      })
      if (!response.ok) throw new Error((await response.json()).detail || 'Submission failed')
      const job = await response.json()
      setJobs((current) => [job, ...current.filter((item) => item.id !== job.id)])
      setSelectedId(job.id)
      const ids = [job.id, ...jobs.map((item) => item.id).filter((id) => id !== job.id)].slice(0, 20)
      localStorage.setItem('queue-job-ids', JSON.stringify(ids))
      setKey(crypto.randomUUID())
    } catch (cause) {
      setError(String(cause.message || cause))
    } finally {
      setBusy(false)
    }
  }

  const clearHistory = () => {
    localStorage.removeItem('queue-job-ids')
    setJobs([])
    setSelectedId(null)
  }

  const selected = jobs.find((job) => job.id === selectedId)

  return (
    <main className="app-shell">
      <header className="topbar"><div className="brand"><img src="/aic-logo.png" alt="Applied Innovation Center" className="brand-logo" /><span className="brand-name">Job Queue</span></div><span className="topbar-tag"><span className="live-dot" /> Background processing demo</span></header>
      <section className="intro"><div className="eyebrow">JOB QUEUE / DASHBOARD</div><h1>Work happens<br /><em>in the background.</em></h1><p>Submit a simulated job and watch a separate worker process it, retry failures, and report the result.</p></section>
      <div className="grid">
        <section className="panel submit-panel"><div className="panel-heading"><span className="heading-icon">＋</span><div><h2>Submit a job</h2><p>Configure a task for the worker</p></div></div>
          <form onSubmit={submit}>
            <label>Duration <span>seconds to simulate work</span><input type="number" min="0" max="30" value={duration} onChange={(e) => setDuration(e.target.value)} required /></label>
            <label>Priority <span>higher jobs are picked first</span><select value={priority} onChange={(e) => setPriority(e.target.value)}><option value="0">Normal · 0</option><option value="1">High · 1</option><option value="2">Urgent · 2</option></select></label>
            <div className="form-row"><label>Fail until attempt <input type="number" min="0" max="10" value={failUntil} onChange={(e) => setFailUntil(e.target.value)} required /></label><label>Max attempts <input type="number" min="1" max="10" value={maxAttempts} onChange={(e) => setMaxAttempts(e.target.value)} required /></label></div>
            <label>Idempotency key <span>reuse a key to get the same job</span><input className="key-input" value={key} onChange={(e) => setKey(e.target.value)} required /></label>
            {error && <p className="error-banner" role="alert">{error}</p>}
            <button className="submit-button" disabled={busy}>{busy ? 'Submitting…' : 'Submit job'} <span>↗</span></button>
          </form>
        </section>
        <section className="panel activity-panel"><div className="panel-heading activity-heading"><span className="heading-icon blue">▤</span><div><h2>Job activity</h2><p>Updates automatically every 1.5 seconds</p></div><button type="button" className="clear-button" onClick={clearHistory} disabled={!jobs.length}>Clear history</button></div>
          {jobs.length === 0 ? <div className="empty"><div className="empty-icon">◎</div><h3>No jobs yet</h3><p>Submit your first job to see its progress here.</p></div> : <>
            <div className="job-list">{jobs.map((job) => <button key={job.id} type="button" aria-expanded={selectedId === job.id} className={`job-item ${selectedId === job.id ? 'active' : ''}`} onClick={() => setSelectedId((current) => current === job.id ? null : job.id)}><span className={`status-dot ${job.status}`} /><span className="job-item-text"><strong>{job.id.slice(0, 8)}…</strong><small>{job.priority === 2 ? 'Urgent' : job.priority === 1 ? 'High' : 'Normal'} priority</small></span><span className={`status-pill ${job.status}`}>{job.status}</span><span className={`chevron ${selectedId === job.id ? 'open' : ''}`} aria-hidden="true">⌄</span></button>)}</div>
            {selected && <div className="details"><div className="details-title"><h3>Job details</h3><span className={`status-pill ${selected.status}`}>{selected.status}</span></div><dl><div><dt>Job ID</dt><dd className="mono">{selected.id}</dd></div><div><dt>Attempts</dt><dd>{selected.attempt_count ?? 0} / {selected.max_attempts ?? '—'}</dd></div><div><dt>Priority</dt><dd>{selected.priority ?? '—'}</dd></div><div><dt>Next available</dt><dd>{selected.status === 'queued' && selected.available_at ? new Date(selected.available_at).toLocaleTimeString() : '—'}</dd></div></dl>{selected.result && <div className="detail-message success"><strong>Result</strong><pre>{JSON.stringify(selected.result, null, 2)}</pre></div>}{selected.error && <div className="detail-message failure"><strong>{terminal.has(selected.status) ? 'Error' : 'Last error'}</strong><p>{selected.error}</p></div>}</div>}
          </>}
        </section>
      </div>
      <footer><span>API → PostgreSQL → Worker</span><span>Built to demonstrate reliable asynchronous processing</span></footer>
    </main>
  )
}

export default App
