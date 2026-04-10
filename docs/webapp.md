# Web App

Interceder includes a React/TypeScript web dashboard for chatting with the Manager, viewing workers, managing approvals, and searching memory.

## Building

Requires Node.js 18+ and npm.

```bash
cd webapp
npm install
npm run build
```

Built assets go to `webapp/dist/`. The Gateway serves them at `http://127.0.0.1:7878`.

### Development mode

```bash
cd webapp
npm run dev
```

Starts Vite dev server on `http://localhost:5173` with hot reload. API requests proxy to the Gateway on port 7878.

## Tech Stack

- **React 19** + **TypeScript 5.6**
- **Vite 6** — build tool and dev server
- **WebSocket** — real-time communication with the Gateway

## Components

| Component | File | Purpose |
|-----------|------|---------|
| Layout | `src/components/Layout.tsx` | Main layout, tab navigation |
| ChatPane | `src/components/ChatPane.tsx` | Chat interface — send messages, see responses |
| MessageBubble | `src/components/MessageBubble.tsx` | Individual message display |
| WorkersPane | `src/components/WorkersPane.tsx` | Active/completed workers list |
| ApprovalsPane | `src/components/ApprovalsPane.tsx` | Pending approval requests |
| MemoryPane | `src/components/MemoryPane.tsx` | Full-text memory search |
| SettingsPane | `src/components/SettingsPane.tsx` | Configuration and status |

## WebSocket API

The webapp connects to `ws://127.0.0.1:7878/ws` (or via Tailscale IP).

### Client → Server messages

**Send a message:**
```json
{
  "type": "message",
  "content": "Hello, Interceder",
  "correlation_id": "webapp:abc123"
}
```

**Ping (keep-alive):**
```json
{ "type": "ping" }
```

### Server → Client messages

**Acknowledgment:**
```json
{
  "type": "ack",
  "message_id": "webapp-abc123def456"
}
```

**Pong:**
```json
{ "type": "pong" }
```

**Manager response (broadcast from outbox drain):**
```json
{
  "type": "message",
  "id": "outbox-id",
  "content": "Here's what I found...",
  "source": "manager",
  "kind": "text",
  "created_at": 1712700000
}
```

## REST API Endpoints

The Gateway exposes these dashboard endpoints at `/api/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Gateway health check |
| `/api/workers` | GET | List workers (optional `?status=running`) |
| `/api/approvals` | GET | List approvals (default `?status=pending`) |
| `/api/memory/search` | GET | Full-text search (`?q=search+term`) |
| `/api/loops` | GET | List Karpathy loops |
| `/api/audit` | GET | Audit log (optional `?limit=100`) |
| `/api/afk/grants` | GET | Active AFK grants |
| `/api/schedules` | GET | Scheduled tasks |

## Remote Access via Tailscale

If Tailscale is configured, the webapp is accessible from any device on your Tailscale network:

```
http://<tailscale-ip>:7878
```

The Gateway binds to `127.0.0.1` by default. To bind to all interfaces (required for Tailscale access), set:

```bash
export INTERCEDER_GATEWAY_HOST=0.0.0.0
```

Then restart the Gateway service.
