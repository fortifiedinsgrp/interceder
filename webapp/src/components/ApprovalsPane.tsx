import { useState, useEffect } from 'react'

interface Approval {
  id: string; action: string; context_json: string;
  tier: number; status: string; created_at: number; expires_at: number;
}

export function ApprovalsPane() {
  const [approvals, setApprovals] = useState<Approval[]>([])

  useEffect(() => {
    const controller = new AbortController()
    // Approvals are time-sensitive, poll more aggressively than workers
    const load = () =>
      fetch('/api/approvals', { signal: controller.signal })
        .then(r => r.json())
        .then(setApprovals)
        .catch(e => { if (e.name !== 'AbortError') console.error(e) })

    load()
    const interval = setInterval(load, 3000)
    return () => { clearInterval(interval); controller.abort() }
  }, [])

  return (
    <div style={{ padding: '16px', overflowY: 'auto', height: '100%' }}>
      <h2 style={{ fontSize: '18px', marginBottom: '12px' }}>Approvals</h2>
      {approvals.length === 0 && <p style={{ color: '#999' }}>No pending approvals.</p>}
      {approvals.map(a => (
        <div key={a.id} style={{
          padding: '12px', marginBottom: '8px', borderRadius: '8px',
          border: '1px solid #e0e0e0',
        }}>
          <div><strong>Action:</strong> {a.action}</div>
          <div style={{ fontSize: '13px', color: '#666' }}>
            Tier {a.tier} | Expires: {new Date(a.expires_at * 1000).toLocaleString()}
          </div>
          <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
            <button style={{
              padding: '6px 16px', borderRadius: '6px', border: 'none',
              background: '#34c759', color: '#fff', cursor: 'pointer',
            }}>Approve</button>
            <button style={{
              padding: '6px 16px', borderRadius: '6px', border: 'none',
              background: '#ff3b30', color: '#fff', cursor: 'pointer',
            }}>Deny</button>
          </div>
        </div>
      ))}
    </div>
  )
}
