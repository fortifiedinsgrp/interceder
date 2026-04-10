# Slack Setup

Slack integration is optional and can be configured after installation. It lets you message Interceder from any device via Slack DMs.

## Overview

Interceder uses **Slack Socket Mode** — no public URL or ngrok required. The Gateway maintains a persistent WebSocket connection to Slack's servers.

## Step 1: Create a Slack App

1. Go to https://api.slack.com/apps
2. Click **Create New App** → **From scratch**
3. Name it `Interceder` (or whatever you prefer)
4. Select your workspace
5. Click **Create App**

## Step 2: Enable Socket Mode

1. In the app settings, go to **Socket Mode** (left sidebar)
2. Toggle **Enable Socket Mode** to ON
3. You'll be prompted to create an **App-Level Token**:
   - Name: `interceder-socket`
   - Scope: `connections:write`
   - Click **Generate**
4. **Copy the token** (starts with `xapp-`) — you'll need it in Step 5

## Step 3: Configure Bot Permissions

1. Go to **OAuth & Permissions** (left sidebar)
2. Under **Bot Token Scopes**, add:
   - `chat:write` — send messages
   - `im:history` — read DM history
   - `im:read` — access DM channel info
   - `im:write` — open/manage DMs
   - `files:read` — access file attachments

## Step 4: Subscribe to Events

1. Go to **Event Subscriptions** (left sidebar)
2. Toggle **Enable Events** to ON
3. Under **Subscribe to bot events**, add:
   - `message.im` — receive DM messages
4. Click **Save Changes**

## Step 5: Install the App to Your Workspace

1. Go to **Install App** (left sidebar)
2. Click **Install to Workspace**
3. Review permissions and click **Allow**
4. **Copy the Bot User OAuth Token** (starts with `xoxb-`)

## Step 6: Store Tokens in Keychain

```bash
# Store the Bot token
security add-generic-password -a "interceder" -s "interceder/slack_bot_token" -w "xoxb-your-bot-token"

# Store the App-Level token
security add-generic-password -a "interceder" -s "interceder/slack_app_token" -w "xapp-your-app-token"
```

## Step 7: Restart the Gateway

```bash
launchctl unload ~/Library/LaunchAgents/com.interceder.gateway.plist
launchctl load ~/Library/LaunchAgents/com.interceder.gateway.plist
```

## Step 8: Test

1. Open Slack and find the `Interceder` bot in your DMs
2. Send a message — it should be enqueued in the inbox
3. Check the Gateway logs for confirmation:

```bash
tail -f ~/Library/Application\ Support/Interceder/logs/gateway.log
```

You should see: `enqueued inbox: slack-...`

## Troubleshooting

**"Slack tokens not found — running without Slack"**
The Gateway starts without Slack if tokens aren't configured. Check:
```bash
security find-generic-password -a "interceder" -s "interceder/slack_bot_token" -w
security find-generic-password -a "interceder" -s "interceder/slack_app_token" -w
```

**Messages not arriving**
- Verify the bot is in your DMs (not a channel)
- Check that `message.im` event subscription is enabled
- Check Socket Mode is enabled
- Look at `gateway.err.log` for connection errors

**"Slack Socket Mode crashed"**
Usually a token issue. Regenerate tokens and re-store in Keychain.
