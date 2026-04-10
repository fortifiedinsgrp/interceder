export function SettingsPane() {
  return (
    <div style={{ padding: '16px', overflowY: 'auto', height: '100%' }}>
      <h2 style={{ fontSize: '18px', marginBottom: '12px' }}>Settings</h2>
      <p style={{ color: '#999' }}>Settings UI — Phase 13 will populate this pane.</p>
      <div style={{
        padding: '16px', borderRadius: '8px', border: '1px solid #e0e0e0',
        marginTop: '12px',
      }}>
        <h3 style={{ fontSize: '15px', marginBottom: '8px' }}>Quiet Hours</h3>
        <p style={{ fontSize: '14px', color: '#666' }}>11:00 PM — 7:00 AM (default)</p>
      </div>
    </div>
  )
}
