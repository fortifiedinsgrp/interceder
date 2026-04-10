import { useState, useEffect } from 'react'

interface Worker {
  id: string; status: string; model: string;
  task_spec_json: string; started_at: number; ended_at: number | null;
  summary: string | null;
}

export function WorkersPane() {
  const [workers, setWorkers] = useState<Worker[]>([])

  useEffect(() => {
    fetch('/api/workers').then(r => r.json()).then(setWorkers).catch(() => {})
    const interval = setInterval(() => {
      fetch('/api/workers').then(r => r.json()).then(setWorkers).catch(() => {})
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{ padding: '16px', overflowY: 'auto', height: '100%' }}>
      <h2 style={{ fontSize: '18px', marginBottom: '12px' }}>Workers</h2>
      {workers.length === 0 && <p style={{ color: '#999' }}>No workers yet.</p>}
      {workers.map(w => (
        <div key={w.id} style={{
          padding: '12px', marginBottom: '8px', borderRadius: '8px',
          border: '1px solid #e0e0e0', background: '#fafafa',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <strong>{w.id}</strong>
            <span style={{
              padding: '2px 8px', borderRadius: '12px', fontSize: '12px',
              background: w.status === 'running' ? '#e8f5e9' :
                         w.status === 'done' ? '#e3f2fd' : '#fff3e0',
              color: w.status === 'running' ? '#2e7d32' :
                     w.status === 'done' ? '#1565c0' : '#e65100',
            }}>{w.status}</span>
          </div>
          <div style={{ fontSize: '13px', color: '#666', marginTop: '4px' }}>
            Model: {w.model} | Started: {new Date(w.started_at * 1000).toLocaleString()}
          </div>
          {w.summary && <div style={{ marginTop: '4px', fontSize: '14px' }}>{w.summary}</div>}
        </div>
      ))}
    </div>
  )
}
