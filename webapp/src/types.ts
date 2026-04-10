export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  source: string
}

export interface WSMessage {
  type: string
  content?: string
  message_id?: string
  correlation_id?: string
  [key: string]: unknown
}
