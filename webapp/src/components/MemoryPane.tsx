import { useState } from 'react'

interface MemoryResult {
  id: string; role: string; content: string; source: string; created_at: number;
}

export function MemoryPane() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<MemoryResult[]>([])

  const search = async () => {
    if (!query.trim()) return
    const resp = await fetch(`/api/memory/search?q=${encodeURIComponent(query)}`)
    const data = await resp.json()
    setResults(data.results || [])
  }

  return (
    <div style={{ padding: '16px', overflowY: 'auto', height: '100%' }}>
      <h2 style={{ fontSize: '18px', marginBottom: '12px' }}>Memory Browser</h2>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        <input
          value={query} onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
          placeholder="Search memory archive..."
          style={{
            flex: 1, padding: '8px 12px', borderRadius: '8px',
            border: '1px solid #ccc', fontSize: '14px',
          }}
        />
        <button onClick={search} style={{
          padding: '8px 16px', borderRadius: '8px', border: 'none',
          background: '#0066cc', color: '#fff', cursor: 'pointer',
        }}>Search</button>
      </div>
      {results.map(r => (
        <div key={r.id} style={{
          padding: '10px', marginBottom: '6px', borderRadius: '6px',
          border: '1px solid #e0e0e0', fontSize: '14px',
        }}>
          <div style={{ fontSize: '12px', color: '#999' }}>
            [{r.role}] {r.source} — {new Date(r.created_at * 1000).toLocaleString()}
          </div>
          <div style={{ marginTop: '4px', whiteSpace: 'pre-wrap' }}>{r.content}</div>
        </div>
      ))}
    </div>
  )
}
