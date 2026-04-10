import { useState, useEffect, useRef } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'
import { MessageBubble } from './MessageBubble'
import type { ChatMessage } from '../types'

export function ChatPane() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const wsUrl = `ws://${window.location.host}/ws`
  const { connected, lastMessage, send } = useWebSocket(wsUrl)

  useEffect(() => {
    if (lastMessage?.type === 'reply') {
      setMessages(prev => [...prev, {
        id: lastMessage.message_id || crypto.randomUUID(),
        role: 'assistant',
        content: lastMessage.content || '',
        timestamp: Date.now(),
        source: 'manager',
      }])
    }
  }, [lastMessage])

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim()) return
    const msg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input,
      timestamp: Date.now(),
      source: 'webapp',
    }
    setMessages(prev => [...prev, msg])
    send({ type: 'message', content: input, correlation_id: 'webapp:chat' })
    setInput('')
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      maxWidth: '800px', margin: '0 auto',
      fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #e0e0e0',
        display: 'flex', alignItems: 'center', gap: '8px',
      }}>
        <h1 style={{ margin: 0, fontSize: '18px' }}>Interceder</h1>
        <span style={{
          width: '8px', height: '8px', borderRadius: '50%',
          backgroundColor: connected ? '#34c759' : '#ff3b30',
        }} />
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 0' }}>
        {messages.map(m => <MessageBubble key={m.id} message={m} />)}
        <div ref={scrollRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '12px 16px', borderTop: '1px solid #e0e0e0',
        display: 'flex', gap: '8px',
      }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="Message Interceder..."
          style={{
            flex: 1, padding: '10px 14px', borderRadius: '20px',
            border: '1px solid #ccc', fontSize: '15px', outline: 'none',
          }}
        />
        <button
          onClick={handleSend}
          disabled={!connected || !input.trim()}
          style={{
            padding: '10px 20px', borderRadius: '20px',
            backgroundColor: '#0066cc', color: '#fff',
            border: 'none', fontSize: '15px', cursor: 'pointer',
            opacity: connected && input.trim() ? 1 : 0.5,
          }}
        >Send</button>
      </div>
    </div>
  )
}
