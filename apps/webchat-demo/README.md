# WebChat Demo - Omnichannel Context Preservation

> A standalone web chat application demonstrating omnichannel context preservation.
> When customers switch from voice to webchat, their conversation history follows them.

## The Demo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     OMNICHANNEL DEMO FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   STEP 1: Voice Call (Main Frontend)                                        │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │  Customer: "I'm calling about a power outage at 123 Oak Street"    │    │
│   │  Agent: "I see you're at 123 Oak Street. Let me check..."         │    │
│   │  Agent: "There's a known outage. Crew ETA is 4:00 PM"             │    │
│   │                                                                    │    │
│   │  → Context saved to CustomerContextManager                         │    │
│   └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│   STEP 2: Switch to WebChat (This App)                                      │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │  [Customer enters same phone number]                               │    │
│   │                                                                    │    │
│   │  ╔════════════════════════════════════════════════════════════╗   │    │
│   │  ║  ✅ CONVERSATION CONTINUED FROM PHONE CALL                  ║   │    │
│   │  ║                                                             ║   │    │
│   │  ║  "I see you recently called about a power outage at        ║   │    │
│   │  ║   123 Oak Street. Crew is en route, ETA 4:00 PM."          ║   │    │
│   │  ║                                                             ║   │    │
│   │  ║  [address: 123 Oak St] [issue: outage] [verified: ✓]       ║   │    │
│   │  ╚════════════════════════════════════════════════════════════╝   │    │
│   │                                                                    │    │
│   │  Customer: "Any update on the crew?"                              │    │
│   │  Agent: "The crew is 2 miles away. They should arrive by 4 PM."  │    │
│   │                                                                    │    │
│   │  → Customer didn't repeat themselves! ✓                           │    │
│   └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Local Development

```bash
# Navigate to this directory
cd apps/webchat-demo

# Install dependencies
npm install

# Set backend URL (use deployed backend or local)
export VITE_BACKEND_URL=http://localhost:8000

# Start development server
npm run dev

# Open http://localhost:3001
```

### With Deployed Backend

```bash
# Use your deployed Azure backend
export VITE_BACKEND_URL=https://artagent-backend-xxxxx.azurecontainerapps.io

npm run dev
```

### Via URL Parameter

You can also pass the backend URL directly:

```
http://localhost:3001?backend=https://your-backend.azurecontainerapps.io
```

Or pre-fill the customer ID:

```
http://localhost:3001?customer_id=+1234567890&backend=https://your-backend.azurecontainerapps.io
```

## Docker

### Build

```bash
docker build -t webchat-demo .
```

### Run

```bash
docker run -p 3001:3001 \
  -e BACKEND_URL=https://your-backend.azurecontainerapps.io \
  webchat-demo
```

## Deploy to Azure Container Apps

The webchat demo can be deployed alongside the main application:

```bash
# Build and push to ACR
az acr build --registry $ACR_NAME --image webchat-demo:latest .

# Create Container App
az containerapp create \
  --name webchat-demo \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENV \
  --image $ACR_NAME.azurecr.io/webchat-demo:latest \
  --target-port 3001 \
  --ingress external \
  --env-vars BACKEND_URL=https://artagent-backend-xxx.azurecontainerapps.io
```

## How It Works

### 1. Voice Call Saves Context

When a customer calls via voice, the orchestrator saves their context:

```python
# In voice orchestrator
await context_manager.update_customer_data(
    customer_id=phone_number,
    data={
        "issue_type": "power_outage",
        "service_address": "123 Oak Street",
        "account_verified": True,
        "outage_eta": "4:00 PM",
    }
)
await context_manager.set_summary(
    customer_id=phone_number,
    summary="Customer reported power outage at 123 Oak Street. Crew dispatched, ETA 4:00 PM."
)
```

### 2. WebChat Retrieves Context

When the customer connects to webchat with the same phone number:

```python
# In webchat WebSocket handler
context = await context_manager.get_or_create(customer_id)

if context.conversation_summary:
    # Send handoff message with context
    await websocket.send_json({
        "type": "handoff",
        "source_channel": context.sessions[-1].channel,
        "context_summary": context.conversation_summary,
        "collected_data": context.collected_data,
    })
```

### 3. Customer Sees Their History

The WebChat UI displays:
- Green banner showing context was preserved
- Summary of previous conversation
- Collected data chips (address, issue type, etc.)
- Agent continues without asking repeated questions

## Architecture

```
┌─────────────────────┐         ┌─────────────────────┐
│   Voice Frontend    │         │   WebChat Demo      │
│   (artagent)        │         │   (this app)        │
│   Port: 3000        │         │   Port: 3001        │
└─────────┬───────────┘         └─────────┬───────────┘
          │                               │
          │ Voice WebSocket               │ Chat WebSocket
          │                               │
          ▼                               ▼
┌─────────────────────────────────────────────────────────┐
│                    BACKEND API                           │
│              (FastAPI + Multi-Agent System)              │
│                                                          │
│  /api/v1/media/ws          /api/v1/channels/webchat/ws  │
│       │                              │                   │
│       └──────────┬───────────────────┘                   │
│                  ▼                                       │
│       ┌─────────────────────┐                           │
│       │ CustomerContextMgr  │ ← Shared across channels  │
│       └──────────┬──────────┘                           │
│                  │                                       │
│         ┌───────┴───────┐                               │
│         ▼               ▼                               │
│   ┌──────────┐   ┌──────────┐                          │
│   │  Redis   │   │ Cosmos   │                          │
│   │  (hot)   │   │ (cold)   │                          │
│   └──────────┘   └──────────┘                          │
└─────────────────────────────────────────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `src/App.jsx` | Main React application with all components |
| `src/main.jsx` | React entry point |
| `index.html` | HTML template |
| `vite.config.js` | Vite build configuration |
| `Dockerfile` | Container build instructions |
| `entrypoint.sh` | Runtime configuration injection |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_BACKEND_URL` | Backend API URL (build-time) | `http://localhost:8000` |
| `BACKEND_URL` | Backend API URL (runtime, Docker) | - |

## Demo Script

For a live demo, follow this script:

1. **Open Voice App** (main artagent frontend)
   - Make a call about a power outage
   - Provide your phone number and address
   - Let the agent confirm the outage and give an ETA

2. **Open WebChat App** (this app in a new tab)
   - Enter the same phone number
   - Click "Start Chat"

3. **See the Magic**
   - Green "Conversation Continued" banner appears
   - Shows summary from the voice call
   - Shows collected data (address, issue type, etc.)

4. **Test Continuity**
   - Ask "Any update on the crew?"
   - Agent responds with context (knows about the outage)
   - Customer didn't repeat themselves!

## Related Documentation

- [Omnichannel Architecture](../../docs/architecture/omnichannel-handoff/README.md)
- [WhatsApp Integration](../../docs/guides/whatsapp-integration.md)
- [Channel Adapters](../artagent/backend/channels/README.md)
