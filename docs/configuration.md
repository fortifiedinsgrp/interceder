# Configuration

## config.toml

Location: `~/Library/Application Support/Interceder/config.toml`

Generated during installation. All values are non-secret — secrets use macOS Keychain references.

### [general]

| Key | Default | Description |
|-----|---------|-------------|
| `user_id` | `"me"` | Your identity. Used as default on all memory entries. Populated from Slack user ID or webapp session when available. |

### [allowlist]

| Key | Default | Description |
|-----|---------|-------------|
| `paths` | `[]` | List of repo root paths the Manager and Workers are allowed to write to. E.g. `["~/code/myrepo", "~/projects/other"]` |

### [quiet_hours]

| Key | Default | Description |
|-----|---------|-------------|
| `start` | `"23:00"` | When quiet hours begin (proactive messages suppressed) |
| `end` | `"07:00"` | When quiet hours end |
| `timezone` | `"local"` | Timezone for quiet hours |

### [proactive.rate_limit_seconds]

Controls how frequently proactive messages can be sent, by type:

| Key | Default | Description |
|-----|---------|-------------|
| `worker_done` | `30` | Minimum seconds between "worker finished" notifications |
| `approval` | `0` | Minimum seconds between approval requests (0 = no limit) |
| `failure` | `0` | Minimum seconds between failure notifications |
| `idle_reflection` | `900` | Minimum seconds between idle reflection messages (15 min) |
| `opportunistic` | `3600` | Minimum seconds between opportunistic suggestions (1 hr) |

### [secrets]

These are **Keychain entry names**, not secret values. Each points to a macOS Keychain entry under the service name `"interceder"`:

| Key | Keychain Entry | Purpose |
|-----|---------------|---------|
| `slack_bot_token` | `interceder/slack_bot_token` | Slack Bot User OAuth Token (`xoxb-...`) |
| `slack_app_token` | `interceder/slack_app_token` | Slack App-Level Token (`xapp-...`) for Socket Mode |
| `webapp_jwt_key` | `interceder/webapp_jwt_key` | JWT signing key for webapp authentication |
| `veo_api_key` | `interceder/veo_api_key` | Google Veo API key for video generation |
| `gemini_api_key` | `interceder/gemini_api_key` | Google Gemini API key for image generation |

### Setting Keychain secrets

```bash
# Store a secret
security add-generic-password -a "interceder" -s "interceder/slack_bot_token" -w "xoxb-your-token-here"

# Retrieve a secret (verify)
security find-generic-password -a "interceder" -s "interceder/slack_bot_token" -w

# Delete a secret
security delete-generic-password -a "interceder" -s "interceder/slack_bot_token"
```

In Python, secrets are accessed via the `keyring` library:
```python
import keyring
token = keyring.get_password("interceder", "slack_bot_token")
```

## Environment Variable Overrides

| Variable | Overrides | Default |
|----------|-----------|---------|
| `INTERCEDER_HOME` | Data directory path | `~/Library/Application Support/Interceder` |
| `INTERCEDER_GATEWAY_HOST` | Gateway bind address | `127.0.0.1` |
| `INTERCEDER_GATEWAY_PORT` | Gateway bind port | `7878` |
| `INTERCEDER_SLACK_APP_TOKEN` | Keychain lookup for Slack app token | (uses Keychain) |
| `INTERCEDER_SLACK_BOT_TOKEN` | Keychain lookup for Slack bot token | (uses Keychain) |

## Model Configuration

Model IDs are defined in `src/interceder/config.py`:

| Constant | Value | Used For |
|----------|-------|----------|
| `MANAGER_MODEL` | `claude-opus-4-6` | Manager Supervisor session |
| `WORKER_DEFAULT_MODEL` | `claude-sonnet-4-6` | Worker subagent sessions |
| `CLASSIFIER_MODEL` | `claude-haiku-4-5-20251001` | Tier classification, routing |

To change models, edit `src/interceder/config.py` and restart services.
