# Omnichannel Demo Script

> **Purpose:** Step-by-step instructions for demonstrating omnichannel context preservation  
> **Duration:** ~10 minutes  
> **Audience:** Stakeholders, customers, technical teams

---

## Overview

This demo showcases the core value proposition of omnichannel:

> **"Customers don't repeat themselves when switching channels"**

You will:
1. Make a voice call about a power outage
2. Switch to the webchat (separate application)
3. See the conversation context automatically appear
4. Continue the conversation without repeating information

---

## Prerequisites

### Deployed Resources

```bash
# Check deployment is active
curl -s https://<your-backend-url>/health | jq .

# Expected output:
# {"status": "healthy", "agents_loaded": 18, ...}
```

### URLs Needed

| Application | URL | Purpose |
|-------------|-----|---------|
| **Voice Frontend** | `https://artagent-frontend-xxx.azurecontainerapps.io` | Voice calls |
| **WebChat Demo** | `https://webchat-demo-xxx.azurecontainerapps.io` | Chat channel |
| **Backend API** | `https://artagent-backend-xxx.azurecontainerapps.io` | Shared backend |

---

## Demo Flow

### Part 1: Voice Call (Main App)

**Open the Voice Frontend in Tab 1**

```
https://artagent-frontend-xxx.azurecontainerapps.io
```

**Start a call with these talking points:**

```
📞 YOU: "Hi, I'm calling to report a power outage"

🤖 AGENT: "I'm sorry to hear that. Can I get your service address?"

📞 YOU: "Yes, it's 123 Oak Street, Springfield"

🤖 AGENT: "Thank you. I can see there's a known outage affecting 
          your area. A crew has been dispatched and the estimated 
          restoration time is 4:00 PM. Is there anything else 
          I can help with?"

📞 YOU: "No, that's all for now. Thanks."

🤖 AGENT: "You're welcome. You can also check for updates on our 
          webchat at any time. Have a great day!"
```

**What Happened Behind the Scenes:**

```
┌─────────────────────────────────────────────────────────────────┐
│  CustomerContextManager saved:                                   │
│                                                                  │
│  {                                                               │
│    "customer_id": "+1234567890",                                │
│    "conversation_summary": "Customer reported power outage at   │
│                             123 Oak Street. Crew dispatched,    │
│                             ETA 4:00 PM.",                      │
│    "collected_data": {                                          │
│      "service_address": "123 Oak Street, Springfield",          │
│      "issue_type": "power_outage",                              │
│      "outage_eta": "4:00 PM",                                   │
│      "account_verified": true                                   │
│    }                                                            │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

### Part 2: Switch to WebChat (New Tab)

**Open the WebChat Demo in Tab 2**

```
https://webchat-demo-xxx.azurecontainerapps.io
```

**Enter the same phone number used in the voice call:**

```
+1234567890
```

**Click "Start Chat"**

---

### Part 3: See the Magic ✨

**What you'll see immediately:**

```
┌─────────────────────────────────────────────────────────────────┐
│  ╔═══════════════════════════════════════════════════════════╗  │
│  ║  ✅ CONVERSATION CONTINUED FROM PHONE CALL                 ║  │
│  ║                                                            ║  │
│  ║  "Customer reported power outage at 123 Oak Street.       ║  │
│  ║   Crew dispatched, ETA 4:00 PM."                          ║  │
│  ║                                                            ║  │
│  ║  [address: 123 Oak St] [issue: outage] [verified: ✓]      ║  │
│  ╚═══════════════════════════════════════════════════════════╝  │
│                                                                  │
│  🤖 "I have your conversation history from your phone call.     │
│      No need to repeat yourself!"                                │
└─────────────────────────────────────────────────────────────────┘
```

**The key demo point:**
- ✅ The webchat ALREADY KNOWS about the outage
- ✅ The webchat ALREADY KNOWS the address
- ✅ The webchat ALREADY KNOWS the ETA
- ✅ Customer doesn't repeat themselves!

---

### Part 4: Continue the Conversation

**Type in the webchat:**

```
📝 YOU: "Any update on the crew?"
```

**Expected response:**

```
🤖 AGENT: "Based on your recent call, I can see you reported an 
          outage at 123 Oak Street, Springfield. Current status: 
          Crew is en route with an estimated arrival of 4:00 PM. 
          Would you like me to send you a text when power is restored?"
```

**Notice:**
- Agent referenced the VOICE call data
- Agent knew the ADDRESS without asking
- Agent knew the ISSUE TYPE without asking
- **Customer didn't repeat themselves!**

---

## Key Talking Points

### For Executives

> "When customers call during a storm and wait times are high, we can 
> seamlessly transition them to webchat or WhatsApp. Their entire 
> conversation history follows them - they never repeat themselves."

### For Technical Teams

> "The CustomerContextManager stores conversation state in Redis (hot) 
> and Cosmos DB (cold). Any channel can retrieve this context using 
> the customer's phone number as the key."

### For Customer Experience

> "Call center wait times drop by 40% during outages when customers 
> can switch to async channels. CSAT improves because they don't 
> have to repeat themselves."

---

## Architecture Diagram (For Technical Discussions)

```
┌─────────────────────┐         ┌─────────────────────┐
│   VOICE FRONTEND    │         │   WEBCHAT DEMO      │
│   (React App)       │         │   (React App)       │
│   Port 3000         │         │   Port 3001         │
└─────────┬───────────┘         └─────────┬───────────┘
          │                               │
          │ Voice                         │ Chat
          │ WebSocket                     │ WebSocket
          │                               │
          ▼                               ▼
┌─────────────────────────────────────────────────────────┐
│                    SHARED BACKEND                        │
│               (FastAPI + Multi-Agent)                    │
│                                                          │
│  /api/v1/media/ws          /api/v1/channels/webchat/ws  │
│       │                              │                   │
│       └──────────┬───────────────────┘                   │
│                  ▼                                       │
│       ┌─────────────────────┐                           │
│       │ CustomerContextMgr  │ ← Unified Customer View   │
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

---

## Troubleshooting

### WebChat shows "No context"

The voice call didn't save context. Check:

1. Backend logs: `az containerapp logs show --name artagent-backend-xxx ...`
2. Redis connection: Ensure `REDIS_HOST` is configured
3. Customer ID format: Must match exactly (include `+` prefix for phone numbers)

### WebSocket connection fails

```bash
# Test WebSocket endpoint
curl -I https://<backend>/api/v1/channels/webchat/ws/test123

# Should return: HTTP/1.1 426 Upgrade Required
# (This is correct - it's a WebSocket endpoint)
```

### Context not appearing

```bash
# Query customer context directly
curl https://<backend>/api/v1/channels/customer/+1234567890/context
```

---

## Variations

### High-Volume Scenario

Demonstrate proactive channel switch during storm:

```
📞 AGENT: "Due to the storm, we're experiencing high call volumes. 
          Wait times are currently 45 minutes. Would you like to 
          continue this conversation on webchat or WhatsApp instead?"

📞 YOU: "Yes, webchat please"

📞 AGENT: "Perfect! I'm sending your conversation summary to our 
          webchat. You can continue there without repeating anything. 
          Thank you for calling!"

[Customer opens webchat - sees full context]
```

### Billing Follow-up Scenario

```
📞 Voice: "I have a question about my bill"
📞 Agent: "Your balance is $127.45 due Feb 15th"

[Later, on webchat]

📝 Chat: "Can I make a payment?"
🤖 Agent: "I see from your call your balance is $127.45. 
          Would you like to pay the full amount or set up a plan?"
```

---

## Success Metrics

Track these during the demo:

| Metric | Target | How to Verify |
|--------|--------|---------------|
| Context appears on webchat | < 2 seconds | Visual |
| Customer info pre-populated | 100% | No repeat questions |
| Agent references voice call | Yes | Response mentions "from your call" |
| WebSocket connection | Stable | No disconnects |

---

## Local Development Testing

For testing locally before Azure deployment:

### Quick Start

```bash
# From project root
./devops/scripts/test-webchat-demo.sh
```

### Manual Steps

1. **Start the backend:**
   ```bash
   # Terminal 1
   make run_server
   ```

2. **Start webchat demo:**
   ```bash
   # Terminal 2
   cd apps/webchat-demo
   npm install
   VITE_BACKEND_URL=http://localhost:8000 npm run dev -- --port 3001
   ```

3. **Open browser:**
   - WebChat: http://localhost:3001
   - Enter test customer ID: `+15551234567`

4. **Test messages:**
   - "What's the status of my outage?"
   - "When will the crew arrive?"

---

## Azure Deployment

### Deploy with azd

```bash
# Enable webchat demo
azd env set ENABLE_WEBCHAT_DEMO true

# Deploy everything
azd up

# Get URLs after deployment
azd env get-values | grep -E "URL|FQDN"
```

### Verify Deployment

```bash
# Check webchat demo is running
curl https://<webchat-demo-url>/

# Check backend health
curl https://<backend-url>/health

# Test WebSocket (should return 426 Upgrade Required)
curl -I https://<backend-url>/api/v1/channels/webchat/ws/test
```

---

## Next Steps After Demo

1. **Interested in WhatsApp?** → [WhatsApp Integration Guide](../guides/whatsapp-integration.md)
2. **Want to deploy?** → [Quickstart Guide](../getting-started/quickstart.md)
3. **Technical deep dive?** → [Omnichannel Architecture](../architecture/omnichannel-handoff/README.md)

---

## Observability & Agent Tracing

### Azure AI Foundry Integration

The utilities scenario includes full agent observability. After running the demo, you can view agent traces in **Azure AI Foundry Portal**:

1. Navigate to: **AI Foundry Portal** → Your Project → **Tracing**
2. Find traces by session ID or time range
3. View the full conversation flow across agents

### What You'll See

```
📊 Trace: invoke_agent UtilitiesConcierge
   ├── gen_ai.usage.input_tokens: 450
   ├── gen_ai.usage.output_tokens: 127
   ├── session.id: abc123-456
   ├── duration_ms: 823
   │
   └── 📊 Trace: invoke_agent OutageAgent (handoff)
       ├── gen_ai.usage.input_tokens: 380
       ├── gen_ai.usage.output_tokens: 95
       └── context_preserved: true
```

### Application Insights Queries

View agent performance in Application Insights:

```kql
// Agent handoff latencies
dependencies
| where name startswith "invoke_agent"
| summarize avg(duration), count() by name
| order by count_ desc

// Token usage by agent
dependencies  
| where name startswith "invoke_agent"
| extend agent_name = tostring(customDimensions["gen_ai.agent.name"])
| extend input_tokens = toint(customDimensions["gen_ai.usage.input_tokens"])
| extend output_tokens = toint(customDimensions["gen_ai.usage.output_tokens"])
| summarize total_input = sum(input_tokens), total_output = sum(output_tokens) by agent_name
```

### Enable Content Recording (Development Only)

To capture full prompts and completions in traces:

```bash
azd env set AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED true
azd deploy
```

⚠️ **Warning:** This captures all prompts/completions including any PII. Only enable in development environments.

### Terraform Configuration

Observability is configured in `infra/terraform/variables.tf`:

```hcl
variable "enable_tracing" {
  description = "Enable OpenTelemetry tracing for AI agents"
  type        = bool
  default     = true
}

variable "enable_genai_content_recording" {
  description = "Enable recording of GenAI prompts and completions"
  type        = bool
  default     = false  # Disabled by default for PII protection
}
```
