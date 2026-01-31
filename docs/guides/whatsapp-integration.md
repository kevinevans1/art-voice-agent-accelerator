# WhatsApp Integration Guide

> **Status:** 📋 Prerequisites Documented | 🔧 Scaffolding Complete | ⏳ Terraform WIP  
> **Last Updated:** January 2026

---

## Overview

This guide walks through integrating WhatsApp messaging into the Real-Time Voice Agent Accelerator using **Azure Communication Services Advanced Messaging**.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      WHATSAPP INTEGRATION FLOW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   📱 CUSTOMER WHATSAPP              ☁️ AZURE                                 │
│   ┌───────────────────┐            ┌─────────────────────────────────────┐  │
│   │                   │            │  Azure Communication Services       │  │
│   │  WhatsApp App     │◀──────────▶│  ┌───────────────────────────────┐ │  │
│   │  (on phone)       │  Messages  │  │  Advanced Messaging           │ │  │
│   │                   │            │  │  (WhatsApp Business API)      │ │  │
│   └───────────────────┘            │  └──────────────┬────────────────┘ │  │
│                                    └─────────────────┼───────────────────┘  │
│                                                      │                       │
│                                                      ▼ Event Grid            │
│                                    ┌─────────────────────────────────────┐  │
│                                    │     BACKEND CONTAINER APP           │  │
│                                    │  ┌───────────────────────────────┐ │  │
│                                    │  │  POST /api/v1/channels/       │ │  │
│                                    │  │       whatsapp/webhook        │ │  │
│                                    │  │                               │ │  │
│                                    │  │  • Parse incoming message     │ │  │
│                                    │  │  • Load customer context      │ │  │
│                                    │  │  • Process with AI agent      │ │  │
│                                    │  │  • Send reply via ACS SDK     │ │  │
│                                    │  └───────────────────────────────┘ │  │
│                                    └─────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### 1. Azure Resources (Already Deployed via `azd up`)

| Resource | Purpose | Status |
|----------|---------|--------|
| Azure Communication Services | Message routing | ✅ Deployed |
| Backend Container App | Webhook endpoint | ✅ Deployed |
| Cosmos DB | Customer context storage | ✅ Deployed |
| Redis | Session state cache | ✅ Deployed |
| Event Grid | Webhook delivery | ✅ Available |

### 2. Meta Business Requirements

Before you can use WhatsApp with ACS, you need:

| Requirement | Description | How to Get |
|-------------|-------------|------------|
| **Meta Business Account** | Parent account for WhatsApp Business | [business.facebook.com](https://business.facebook.com) |
| **WhatsApp Business Account** | Connected to Meta Business Manager | Created in Meta Business Suite |
| **Verified Phone Number** | Phone number for your WhatsApp channel | Provided during setup |
| **Message Templates** | Pre-approved templates for business-initiated messages | Created in Meta Business Manager |

### 3. Python Package

The `azure-communication-messages` package is required:

```bash
# Add to project dependencies
pip install azure-communication-messages>=1.1.0
```

---

## Step-by-Step Setup

### Step 1: Create Meta Business Account

1. Go to [business.facebook.com](https://business.facebook.com)
2. Click **Create Account**
3. Enter business details and verify your identity
4. Complete business verification (may take 1-2 days)

### Step 2: Connect WhatsApp to Azure Communication Services

#### Via Azure Portal

1. Navigate to your **Azure Communication Services** resource
2. Go to **Channels** → **WhatsApp**
3. Click **Connect WhatsApp Business Account**
4. Sign in with your Meta Business Manager credentials
5. Select your WhatsApp Business Account
6. Choose or add a phone number
7. Complete the verification process

#### What You'll Get

After connection, you'll receive:

| Value | Environment Variable | Description |
|-------|---------------------|-------------|
| Channel Registration ID | `ACS_WHATSAPP_CHANNEL_ID` | Unique ID for your WhatsApp channel |
| Connection String | `ACS_CONNECTION_STRING` | Already deployed with your ACS resource |

### Step 3: Create Message Templates

WhatsApp requires pre-approved templates for business-initiated messages (e.g., handoff notifications).

1. Go to **Meta Business Manager** → **WhatsApp Manager** → **Message Templates**
2. Create templates for your use cases:

#### Example: Conversation Continuation Template

```
Template Name: conversation_continuation
Category: UTILITY
Language: English

Header: None
Body: 
"Hi {{1}}, we're continuing your conversation from your recent call. 
Here's a summary: {{2}}

Reply to this message to continue chatting with our support team."

Footer: None
Buttons: None
```

#### Example: Outage Update Template

```
Template Name: outage_update
Category: UTILITY
Language: English

Body:
"Power Outage Update for {{1}}:
Status: {{2}}
Estimated Restoration: {{3}}

Reply with HELP for assistance or STATUS for updates."
```

3. Submit templates for review (usually approved within 24 hours)

### Step 4: Configure Event Grid Webhook

#### Via Azure Portal

1. Go to your **Azure Communication Services** resource
2. Navigate to **Events** → **+ Event Subscription**
3. Configure:
   - **Name:** `whatsapp-messages`
   - **Event Schema:** Event Grid Schema
   - **Event Types:** 
     - `Microsoft.Communication.AdvancedMessageReceived`
     - `Microsoft.Communication.AdvancedMessageDeliveryStatusUpdated`
   - **Endpoint Type:** Web Hook
   - **Endpoint:** `https://<your-backend-url>/api/v1/channels/whatsapp/webhook`

4. Click **Create**

#### Via Terraform (Add to your deployment)

Add to `infra/terraform/whatsapp.tf`:

```hcl
# ============================================================================
# WHATSAPP EVENT GRID SUBSCRIPTION
# ============================================================================

resource "azurerm_eventgrid_system_topic" "acs_whatsapp" {
  count = var.enable_whatsapp ? 1 : 0

  name                   = "evgt-acs-whatsapp-${var.environment}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = "global"
  source_arm_resource_id = azapi_resource.acs.id
  topic_type             = "Microsoft.Communication.CommunicationServices"
  
  tags = local.tags
}

resource "azurerm_eventgrid_system_topic_event_subscription" "whatsapp_messages" {
  count = var.enable_whatsapp ? 1 : 0

  name                = "whatsapp-messages-sub"
  system_topic        = azurerm_eventgrid_system_topic.acs_whatsapp[0].name
  resource_group_name = azurerm_resource_group.main.name

  included_event_types = [
    "Microsoft.Communication.AdvancedMessageReceived",
    "Microsoft.Communication.AdvancedMessageDeliveryStatusUpdated",
  ]

  webhook_endpoint {
    url = "https://${azurerm_container_app.backend.latest_revision_fqdn}/api/v1/channels/whatsapp/webhook"
  }

  retry_policy {
    max_delivery_attempts = 30
    event_time_to_live    = 1440  # 24 hours
  }
}
```

Add to `infra/terraform/variables.tf`:

```hcl
variable "enable_whatsapp" {
  description = "Enable WhatsApp channel integration"
  type        = bool
  default     = false
}

variable "whatsapp_channel_id" {
  description = "ACS WhatsApp channel registration ID"
  type        = string
  default     = ""
  sensitive   = true
}
```

### Step 5: Configure Environment Variables

Add to your App Configuration or `.env.local`:

```bash
# WhatsApp Configuration
ACS_WHATSAPP_CHANNEL_ID=<your-channel-registration-id>

# Already configured via azd up:
# ACS_CONNECTION_STRING=<from-key-vault>
```

#### Via Azure App Configuration

```bash
# Set WhatsApp channel ID
az appconfig kv set \
  --name <your-appconfig-name> \
  --key "ACS_WHATSAPP_CHANNEL_ID" \
  --value "<your-channel-id>" \
  --yes
```

---

## Code Implementation

### Existing Scaffolding

The codebase already includes WhatsApp scaffolding:

| File | Purpose |
|------|---------|
| [channels/whatsapp.py](../../apps/artagent/backend/channels/whatsapp.py) | WhatsApp adapter with send/receive |
| [channels/context.py](../../apps/artagent/backend/channels/context.py) | Cross-channel customer context |
| [endpoints/channels.py](../../apps/artagent/backend/api/v1/endpoints/channels.py) | REST API endpoints |
| [channels/base.py](../../apps/artagent/backend/channels/base.py) | Base adapter interface |

### Key Classes

#### WhatsAppAdapter

```python
from apps.artagent.backend.channels.whatsapp import WhatsAppAdapter

# Initialize
adapter = WhatsAppAdapter()
await adapter.initialize()

# Send free-form message (within 24h reply window)
await adapter.send_message(
    customer_id="+1234567890",
    message="Your outage has been resolved!",
)

# Send template message (for business-initiated)
await adapter.send_template_message(
    customer_id="+1234567890",
    template_name="outage_update",
    template_values=["123 Oak St", "Under repair", "4:00 PM today"],
)
```

#### CustomerContextManager

```python
from apps.artagent.backend.channels.context import CustomerContextManager

manager = CustomerContextManager()

# Get customer context (shared across voice/whatsapp/webchat)
context = await manager.get_or_create(customer_id="+1234567890")

# Context includes data from voice calls!
print(context.collected_data)  # {"account_verified": True, "issue": "billing"}
print(context.conversation_summary)  # "Customer called about billing dispute..."
```

### Webhook Handler

The webhook endpoint at `/api/v1/channels/whatsapp/webhook` handles:

1. **Event Grid Validation** - Responds to subscription validation requests
2. **Incoming Messages** - Routes to AI agent for processing
3. **Delivery Status** - Tracks message delivery/read receipts

```python
# From apps/artagent/backend/api/v1/endpoints/channels.py

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request) -> dict[str, Any]:
    """Handle incoming WhatsApp messages from ACS Event Grid."""
    body = await request.json()
    
    # Event Grid validation
    if event.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
        return {"validationResponse": event["data"]["validationCode"]}
    
    # Process message with AI agent
    await process_whatsapp_message(event["data"])
    return {"status": "processed"}
```

---

## Voice-to-WhatsApp Handoff

### How It Works

When a voice call has high wait times, the system can offer to continue on WhatsApp:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      VOICE → WHATSAPP HANDOFF                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   📞 VOICE CALL                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Agent: "Wait times are high. Would you like to continue on         │   │
│   │         WhatsApp and get updates there?"                            │   │
│   │  Customer: "Yes, that would be great."                              │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                       │                                      │
│                                       ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  HANDOFF SERVICE                                                     │   │
│   │  1. Save conversation to Cosmos DB                                   │   │
│   │  2. Generate summary with AI                                         │   │
│   │  3. Send WhatsApp template with context                              │   │
│   │  4. End voice call gracefully                                        │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                       │                                      │
│                                       ▼                                      │
│   📱 WHATSAPP                                                                │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Template: "Hi! We're continuing from your call.                     │   │
│   │            Summary: You called about a power outage at 123 Oak St.  │   │
│   │            Reply to continue chatting."                              │   │
│   │                                                                      │   │
│   │  Customer: "Any update on the crew?"                                 │   │
│   │  Agent: "The crew is en route, ETA 4:00 PM." ← Has full context!    │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Using the Handoff Tool

```python
# From registries/toolstore/channel_handoff.py (to be created)

@register_tool
async def offer_whatsapp_handoff(
    phone_number: str,
    conversation_summary: str,
    reason: str = "high_volume"
) -> dict:
    """
    Offer to continue the conversation on WhatsApp.
    
    Args:
        phone_number: Customer's phone number
        conversation_summary: Summary of the conversation so far
        reason: Why handoff is being offered (high_volume, after_hours, etc.)
    
    Returns:
        Handoff status and details
    """
    # Implementation in channels/handoff_service.py
    ...
```

---

## Testing

### Local Testing

```bash
# 1. Ensure WhatsApp environment variables are set
export ACS_WHATSAPP_CHANNEL_ID="your-channel-id"

# 2. Start the backend
make run_backend

# 3. Test the webhook endpoint
curl -X POST http://localhost:8000/api/v1/channels/whatsapp/webhook \
  -H "Content-Type: application/json" \
  -d '[{
    "eventType": "Microsoft.Communication.AdvancedMessageReceived",
    "data": {
      "from": "+1234567890",
      "to": "channel-id",
      "receivedTimestamp": "2026-01-30T10:00:00Z",
      "message": {
        "text": "Hello!",
        "messageId": "msg_test_123"
      }
    }
  }]'
```

### WhatsApp Sandbox (Recommended for Development)

Azure provides a WhatsApp Sandbox for testing without a production account:

1. Go to ACS resource → **Try Communication Services**
2. Select **Try WhatsApp**
3. Scan QR code with your phone
4. Send "join <sandbox-keyword>" to the sandbox number
5. Test sending/receiving messages

See: [WhatsApp Sandbox Quickstart](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/advanced-messaging/whatsapp/whatsapp-sandbox-quickstart)

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `azure-communication-messages not found` | Package not installed | `pip install azure-communication-messages>=1.1.0` |
| `ACS_WHATSAPP_CHANNEL_ID not configured` | Missing env var | Set channel ID from Azure Portal |
| Webhook not receiving events | Event Grid not configured | Create Event Grid subscription |
| Template messages failing | Template not approved | Check Meta Business Manager for status |
| 24-hour window expired | Can't send free-form after 24h | Use template message to re-initiate |

### Debug Logging

Enable debug logs for the WhatsApp adapter:

```python
import logging
logging.getLogger("channels.whatsapp").setLevel(logging.DEBUG)
```

### Event Grid Troubleshooting

```bash
# Check Event Grid subscription status
az eventgrid event-subscription show \
  --name whatsapp-messages \
  --source-resource-id <acs-resource-id>

# View delivery failures
az eventgrid event-subscription show \
  --name whatsapp-messages \
  --source-resource-id <acs-resource-id> \
  --include-full-endpoint-url \
  --query "deliveryWithResourceIdentity"
```

---

## Pricing

WhatsApp messages are billed per conversation (24-hour window):

| Conversation Type | Description | Approximate Cost |
|-------------------|-------------|------------------|
| **User-initiated** | Customer messages you first | $0.005-0.02 |
| **Business-initiated (Utility)** | Templates for updates | $0.01-0.03 |
| **Business-initiated (Marketing)** | Promotional templates | $0.05-0.15 |

Prices vary by country. See [ACS WhatsApp Pricing](https://learn.microsoft.com/en-us/azure/communication-services/concepts/advanced-messaging/whatsapp/pricing).

---

## Next Steps

1. [ ] Complete Meta Business verification
2. [ ] Connect WhatsApp to ACS in Azure Portal
3. [ ] Create and approve message templates
4. [ ] Configure Event Grid subscription
5. [ ] Set `ACS_WHATSAPP_CHANNEL_ID` in App Configuration
6. [ ] Test with WhatsApp Sandbox
7. [ ] Deploy with `azd deploy`
8. [ ] Pilot with limited users

---

## Related Documentation

- [Omnichannel Architecture](../architecture/omnichannel-handoff/README.md)
- [ACS WhatsApp Overview](https://learn.microsoft.com/en-us/azure/communication-services/concepts/advanced-messaging/whatsapp/whatsapp-overview)
- [WhatsApp Sandbox Quickstart](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/advanced-messaging/whatsapp/whatsapp-sandbox-quickstart)
- [Handle WhatsApp Events](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/advanced-messaging/whatsapp/handle-advanced-messaging-events)
