import { useState, useEffect } from 'react'

interface AfkGrant {
  id: string
  scope_json: string
  granted_at: string
  expires_at: string | null
  revoked_at: string | null
}

interface ScheduledTask {
  id: string
  name: string
  cron_expr: string
  prompt: string
  enabled: boolean
  next_run_at: string | null
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function timeRemaining(expires_at: string | null): string {
  if (!expires_at) return 'No expiry'
  const diff = new Date(expires_at).getTime() - Date.now()
  if (diff <= 0) return 'Expired'
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(minutes / 60)
  if (hours > 0) return `${hours}h ${minutes % 60}m remaining`
  return `${minutes}m remaining`
}

function parseScope(scope_json: string): string {
  try {
    const parsed = JSON.parse(scope_json)
    if (Array.isArray(parsed)) return parsed.join(', ')
    if (typeof parsed === 'object' && parsed !== null) {
      return Object.entries(parsed)
        .map(([k, v]) => `${k}: ${v}`)
        .join(', ')
    }
    return String(parsed)
  } catch {
    return scope_json
  }
}

export function SettingsPane() {
  const [killSwitchActive, setKillSwitchActive] = useState(false)
  const [afkGrants, setAfkGrants] = useState<AfkGrant[]>([])
  const [scheduledTasks, setScheduledTasks] = useState<ScheduledTask[]>([])
  const [afkError, setAfkError] = useState<string | null>(null)
  const [scheduleError, setScheduleError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAfk = () => {
      const ctrl = new AbortController()
      fetch('/api/afk/grants', { signal: ctrl.signal })
        .then(r => r.json())
        .then(data => { setAfkGrants(data); setAfkError(null) })
        .catch(err => { if (err.name !== 'AbortError') setAfkError('Failed to load AFK grants') })
      return ctrl
    }

    const fetchSchedules = () => {
      const ctrl = new AbortController()
      fetch('/api/schedules', { signal: ctrl.signal })
        .then(r => r.json())
        .then(data => { setScheduledTasks(data); setScheduleError(null) })
        .catch(err => { if (err.name !== 'AbortError') setScheduleError('Failed to load schedules') })
      return ctrl
    }

    const afkCtrl = fetchAfk()
    const schedCtrl = fetchSchedules()

    const interval = setInterval(() => {
      fetchAfk()
      fetchSchedules()
    }, 5000)

    return () => {
      afkCtrl.abort()
      schedCtrl.abort()
      clearInterval(interval)
    }
  }, [])

  const activeGrants = afkGrants.filter(g => !g.revoked_at)

  return (
    <div style={{ padding: '16px', overflowY: 'auto', height: '100%' }}>
      <h2 style={{ fontSize: '18px', marginBottom: '12px' }}>Settings</h2>

      {/* Kill Switch */}
      <div style={{
        padding: '16px', borderRadius: '8px', border: '1px solid #e0e0e0',
        marginBottom: '16px', background: killSwitchActive ? '#fff5f5' : '#fafafa',
      }}>
        <h3 style={{ fontSize: '15px', marginBottom: '8px' }}>Kill Switch</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <span style={{
            padding: '2px 8px', borderRadius: '12px', fontSize: '12px',
            background: killSwitchActive ? '#fecaca' : '#d1fae5',
            color: killSwitchActive ? '#991b1b' : '#065f46',
            fontWeight: 600,
          }}>
            {killSwitchActive ? 'ACTIVE' : 'INACTIVE'}
          </span>
          <button
            onClick={() => setKillSwitchActive(prev => !prev)}
            style={{
              padding: '8px 20px', borderRadius: '6px', border: 'none',
              cursor: 'pointer', fontWeight: 700, fontSize: '14px',
              background: killSwitchActive ? '#dc2626' : '#b91c1c',
              color: '#fff',
              boxShadow: killSwitchActive ? '0 0 0 3px rgba(220,38,38,0.3)' : 'none',
              transition: 'all 0.15s',
            }}
          >
            {killSwitchActive ? 'Deactivate Kill Switch' : 'Activate Kill Switch'}
          </button>
        </div>
        <p style={{ fontSize: '12px', color: '#999', marginTop: '8px' }}>
          {killSwitchActive
            ? 'Kill switch is active — agent actions are halted.'
            : 'Activate to immediately halt all in-progress agent actions.'}
        </p>
      </div>

      {/* AFK Mode */}
      <div style={{
        padding: '16px', borderRadius: '8px', border: '1px solid #e0e0e0',
        marginBottom: '16px', background: '#fafafa',
      }}>
        <h3 style={{ fontSize: '15px', marginBottom: '8px' }}>
          AFK Mode
          <span style={{
            marginLeft: '8px', padding: '2px 8px', borderRadius: '12px',
            fontSize: '12px', background: '#e0f2fe', color: '#0369a1',
          }}>
            {activeGrants.length} active
          </span>
        </h3>

        {afkError && (
          <p style={{ fontSize: '13px', color: '#dc2626', marginBottom: '8px' }}>{afkError}</p>
        )}

        {activeGrants.length === 0 && !afkError && (
          <p style={{ fontSize: '14px', color: '#999' }}>No active AFK grants.</p>
        )}

        {activeGrants.map(grant => {
          const remaining = timeRemaining(grant.expires_at)
          const isExpiringSoon = grant.expires_at
            ? new Date(grant.expires_at).getTime() - Date.now() < 10 * 60 * 1000
            : false

          return (
            <div key={grant.id} style={{
              padding: '12px', marginBottom: '8px', borderRadius: '8px',
              border: '1px solid #e0e0e0', background: '#fff',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '4px' }}>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '2px' }}>
                    Scope: <span style={{ fontWeight: 400, color: '#444' }}>{parseScope(grant.scope_json)}</span>
                  </div>
                  <div style={{ fontSize: '12px', color: '#666' }}>
                    Granted: {formatDateTime(grant.granted_at)}
                  </div>
                  {grant.expires_at && (
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      Expires: {formatDateTime(grant.expires_at)}
                    </div>
                  )}
                </div>
                <span style={{
                  padding: '2px 8px', borderRadius: '12px', fontSize: '12px',
                  background: isExpiringSoon ? '#fef3c7' : '#d1fae5',
                  color: isExpiringSoon ? '#92400e' : '#065f46',
                  whiteSpace: 'nowrap',
                }}>
                  {remaining}
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Scheduled Tasks */}
      <div style={{
        padding: '16px', borderRadius: '8px', border: '1px solid #e0e0e0',
        marginBottom: '16px', background: '#fafafa',
      }}>
        <h3 style={{ fontSize: '15px', marginBottom: '8px' }}>
          Scheduled Tasks
          <span style={{
            marginLeft: '8px', padding: '2px 8px', borderRadius: '12px',
            fontSize: '12px', background: '#ede9fe', color: '#5b21b6',
          }}>
            {scheduledTasks.length} tasks
          </span>
        </h3>

        {scheduleError && (
          <p style={{ fontSize: '13px', color: '#dc2626', marginBottom: '8px' }}>{scheduleError}</p>
        )}

        {scheduledTasks.length === 0 && !scheduleError && (
          <p style={{ fontSize: '14px', color: '#999' }}>No scheduled tasks.</p>
        )}

        {scheduledTasks.map(task => (
          <div key={task.id} style={{
            padding: '12px', marginBottom: '8px', borderRadius: '8px',
            border: '1px solid #e0e0e0', background: '#fff',
            opacity: task.enabled ? 1 : 0.6,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '4px' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '2px' }}>{task.name}</div>
                <div style={{ fontSize: '12px', color: '#666', fontFamily: 'monospace' }}>{task.cron_expr}</div>
                {task.next_run_at && (
                  <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                    Next run: {formatDateTime(task.next_run_at)}
                  </div>
                )}
              </div>
              <span style={{
                padding: '2px 8px', borderRadius: '12px', fontSize: '12px',
                background: task.enabled ? '#d1fae5' : '#f3f4f6',
                color: task.enabled ? '#065f46' : '#6b7280',
                whiteSpace: 'nowrap',
              }}>
                {task.enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Quiet Hours */}
      <div style={{
        padding: '16px', borderRadius: '8px', border: '1px solid #e0e0e0',
        background: '#fafafa',
      }}>
        <h3 style={{ fontSize: '15px', marginBottom: '8px' }}>Quiet Hours</h3>
        <p style={{ fontSize: '14px', color: '#666' }}>11:00 PM — 7:00 AM (default)</p>
      </div>
    </div>
  )
}
