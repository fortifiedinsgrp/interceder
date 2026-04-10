import { useState } from 'react'
import { ChatPane } from './ChatPane'
import { WorkersPane } from './WorkersPane'
import { ApprovalsPane } from './ApprovalsPane'
import { MemoryPane } from './MemoryPane'
import { SettingsPane } from './SettingsPane'

const TABS = ['Chat', 'Workers', 'Approvals', 'Memory', 'Settings'] as const
type Tab = typeof TABS[number]

export function Layout() {
  const [activeTab, setActiveTab] = useState<Tab>('Chat')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Tab bar */}
      <nav style={{
        display: 'flex', borderBottom: '1px solid #e0e0e0',
        overflowX: 'auto', WebkitOverflowScrolling: 'touch',
      }}>
        {TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '12px 16px', border: 'none', background: 'none',
              cursor: 'pointer', fontSize: '14px', whiteSpace: 'nowrap',
              borderBottom: activeTab === tab ? '2px solid #0066cc' : '2px solid transparent',
              color: activeTab === tab ? '#0066cc' : '#666',
              fontWeight: activeTab === tab ? 600 : 400,
            }}
          >{tab}</button>
        ))}
      </nav>

      {/* Active pane */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {activeTab === 'Chat' && <ChatPane />}
        {activeTab === 'Workers' && <WorkersPane />}
        {activeTab === 'Approvals' && <ApprovalsPane />}
        {activeTab === 'Memory' && <MemoryPane />}
        {activeTab === 'Settings' && <SettingsPane />}
      </div>
    </div>
  )
}
