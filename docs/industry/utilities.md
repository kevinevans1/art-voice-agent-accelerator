# Utilities Scenario

> **Industry:** Electric & Natural Gas  
> **Entry Agent:** UtilitiesConcierge  
> **Model:** Service-first routing with omnichannel support

---

## Overview

The Utilities scenario provides AI-powered customer service for **domestic electric and natural gas providers**. It handles billing inquiries, outage reporting, service changes, and usage analysis with omnichannel support for high-volume situations.

---

## Architecture

```
                    ┌─────────────────────────┐
                    │   UtilitiesConcierge    │ ← Entry Point
                    │   (Primary Router)      │
                    └───────────┬─────────────┘
                                │
          ┌─────────────┬───────┴───────┬─────────────┐
          ▼             ▼               ▼             ▼
    ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
    │  Billing  │ │  Outage   │ │  Service  │ │   Usage   │
    │   Agent   │ │   Agent   │ │   Agent   │ │   Agent   │
    └───────────┘ └───────────┘ └───────────┘ └───────────┘
         │              │             │             │
         │         DISCRETE           │             │
         │       (Safety-first)       │             │
         │              │             │             │
         └──────────────┴─────────────┴─────────────┘
                        │
                  ANNOUNCED
              (Specialist greeting)
```

---

## Multi-Agent Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     UTILITIES MULTI-AGENT ORCHESTRATION                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  📞 INBOUND CALL                                                             │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                   UtilitiesConcierge                           │         │
│  │  • Verify account                                              │         │
│  │  • Quick lookups (balance, due date)                          │         │
│  │  • Route to specialist if needed                              │         │
│  └─────────────────────────┬──────────────────────────────────────┘         │
│                            │                                                 │
│    ┌───────────────────────┼───────────────────────┐                        │
│    │                       │                       │                        │
│    ▼                       ▼                       ▼                        │
│  ┌─────────────┐    ┌─────────────┐        ┌─────────────┐                  │
│  │ "Payment    │    │ "Power is   │        │ "I'm        │                  │
│  │  plan?"     │    │  out!"      │        │  moving"    │                  │
│  └──────┬──────┘    └──────┬──────┘        └──────┬──────┘                  │
│         │                  │                      │                         │
│         ▼                  ▼                      ▼                         │
│  ┌─────────────┐    ┌─────────────┐        ┌─────────────┐                  │
│  │   Billing   │    │   Outage    │        │   Service   │                  │
│  │    Agent    │    │    Agent    │        │    Agent    │                  │
│  │             │    │             │        │             │                  │
│  │ • Plans     │    │ • Safety    │        │ • Transfer  │                  │
│  │ • Disputes  │    │ • Reporting │        │ • Start/Stop│                  │
│  │ • Credits   │    │ • Status    │        │ • Scheduling│                  │
│  └─────────────┘    └─────────────┘        └─────────────┘                  │
│                                                                              │
│  ⚡ HIGH VOLUME?                                                             │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                   ChannelRouter (Supervisor)                    │         │
│  │  • Monitor queue depth                                         │         │
│  │  • Offer WhatsApp/WebChat for non-urgent                       │         │
│  │  • Preserve context across channels                            │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Agents

| Agent | Role | Handoff Type | Tools |
|:------|:-----|:-------------|:------|
| **UtilitiesConcierge** | Primary router, quick lookups | — | `get_account_info`, channel handoffs |
| **BillingAgent** | Payments, disputes, credits | ANNOUNCED | `get_current_bill`, `process_payment`, `setup_payment_plan` |
| **OutageAgent** | Outages, emergencies | DISCRETE | `check_outage_status`, `report_outage`, `report_downed_wire` |
| **ServiceAgent** | Start/stop/transfer | ANNOUNCED | `transfer_service`, scheduling |
| **UsageAgent** | Consumption, efficiency | ANNOUNCED | `get_usage_history`, `get_efficiency_tips` |

---

## Outage Handling (Safety-First)

```
┌─────────────────────────────────────────────────────────────────┐
│                    OUTAGE TRIAGE FLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Customer: "I smell gas"                                        │
│        │                                                         │
│        ▼                                                         │
│   ┌────────────────────────────────────────┐                    │
│   │  🚨 EMERGENCY PROTOCOL                  │                    │
│   │  1. "Leave immediately"                 │                    │
│   │  2. "Don't use electronics inside"      │                    │
│   │  3. "Call 911 from outside"             │                    │
│   │  4. Dispatch emergency crew             │                    │
│   └────────────────────────────────────────┘                    │
│                                                                  │
│   Customer: "My power is out"                                    │
│        │                                                         │
│        ▼                                                         │
│   ┌────────────────────────────────────────┐                    │
│   │  check_outage_status(address)          │                    │
│   └─────────────────┬──────────────────────┘                    │
│                     │                                            │
│        ┌────────────┴────────────┐                              │
│        ▼                         ▼                              │
│   ┌──────────────┐       ┌──────────────┐                       │
│   │ KNOWN OUTAGE │       │  NEW REPORT  │                       │
│   │              │       │              │                       │
│   │ • Show ETA   │       │ • Create tkt │                       │
│   │ • # affected │       │ • Dispatch   │                       │
│   │ • Offer SMS  │       │ • Confirm    │                       │
│   └──────────────┘       └──────────────┘                       │
│                                                                  │
│   Outage Credits (Auto-applied):                                │
│   ├── > 4 hours  → $25 credit                                   │
│   ├── > 8 hours  → $50 credit                                   │
│   └── > 24 hours → Full day credited                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Omnichannel Integration

During high call volume (storm outages, rate changes), the system offers channel alternatives:

```
┌─────────────────────────────────────────────────────────────────┐
│               OMNICHANNEL DURING OUTAGE EVENTS                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   📞 Voice Call                                                  │
│   ┌──────────────────────────────────────────────┐              │
│   │  "We're experiencing high call volume due    │              │
│   │   to the storm. Would you like me to send    │              │
│   │   updates to WhatsApp instead?"              │              │
│   └──────────────────────┬───────────────────────┘              │
│                          │                                       │
│                          ▼                                       │
│   📱 WhatsApp            💻 WebChat                              │
│   ┌──────────────┐      ┌──────────────┐                        │
│   │ • Outage map │      │ • Self-serve │                        │
│   │ • Push ETAs  │      │ • Bill pay   │                        │
│   │ • Crew GPS   │      │ • Usage view │                        │
│   └──────────────┘      └──────────────┘                        │
│                                                                  │
│   Context Preserved:                                             │
│   ┌──────────────────────────────────────────────┐              │
│   │  customer_id: "cust_12345"                   │              │
│   │  account_verified: true                      │              │
│   │  service_address: "123 Oak St"               │              │
│   │  active_outage: {...}                        │              │
│   │  conversation_summary: "..."                 │              │
│   └──────────────────────────────────────────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Handoff Patterns

### Discrete (Outage)

Used for urgency — no delay for greetings:

```python
handoff_outage_agent_executor() → {
    "handoff": True,
    "target_agent": "OutageAgent",
    "handoff_type": "discrete",  # Immediate
    ...
}
```

### Announced (Billing, Service, Usage)

Specialist introduces themselves:

```python
handoff_billing_agent_executor() → {
    "handoff": True,
    "target_agent": "BillingAgent", 
    "handoff_type": "announced",  # Greeting
    ...
}
```

---

## Azure AI Foundry Integration

All agents deploy under a single Foundry project:

```yaml
# foundry-project.yaml
foundry:
  project_name: "powergas-voice-agent"
  unified_project: true
  
  models:
    primary:
      name: "gpt-4o"
      capacity: 100
    fallback:
      name: "gpt-4o-mini"
      capacity: 200
      
  agents:
    utilities_concierge:
      model: primary
    billing_agent:
      model: primary
    outage_agent:
      model: primary
    service_agent:
      model: primary
    usage_agent:
      model: primary
    channel_router:
      model: fallback  # Lighter weight
      is_supervisor: true
```

---

## Tools

### Billing Tools

| Tool | Description |
|------|-------------|
| `get_current_bill` | Current balance, due date, last payment |
| `get_bill_breakdown` | Line-item breakdown by service |
| `process_payment` | Make one-time payment |
| `setup_payment_plan` | Create installment plan |

### Outage Tools

| Tool | Description |
|------|-------------|
| `check_outage_status` | Known outages at address |
| `report_outage` | Create new outage ticket |
| `report_downed_wire` | Emergency dispatch |

### Service Tools

| Tool | Description |
|------|-------------|
| `transfer_service` | Move service to new address |

### Usage Tools

| Tool | Description |
|------|-------------|
| `get_usage_history` | Historical consumption |
| `get_efficiency_tips` | Personalized savings tips |

---

## Example Conversations

### Billing Inquiry

```
Customer: "Why is my bill so high this month?"

Concierge: [calls get_current_bill]
           "Your current balance is $247.83, due February 15th.
            That's about $80 higher than last month. Would you 
            like me to look at a detailed breakdown?"

Customer: "Yes please"

Concierge: [calls get_bill_breakdown]
           "I can see your electric usage increased by 400 kWh.
            This is common with colder weather. Would you like
            tips on reducing your bill, or help setting up a
            budget billing plan?"
```

### Outage Report

```
Customer: "My power just went out"

Concierge: [handoff_outage_agent → DISCRETE]

OutageAgent: [calls check_outage_status]
             "I see there's an outage affecting your area.
              2,400 customers are affected. Crews are on site.
              Restoration estimated by 4 PM. Would you like
              text updates as we get more information?"
```

### Gas Emergency

```
Customer: "I smell gas in my house"

Concierge: [handoff_outage_agent → DISCRETE, is_emergency: true]

OutageAgent: "This is urgent. Please leave your home immediately.
              Don't use any electrical switches or your phone inside.
              Once you're safely outside, call 911.
              I'm dispatching our emergency gas crew to your address now.
              Is everyone safely outside?"
```

---

## Configuration

```yaml
# orchestration.yaml
name: utilities
description: Electric & natural gas customer service
industry: utilities

start_agent: UtilitiesConcierge

omnichannel:
  enabled: true
  primary_channel: voice
  alternate_channels: [whatsapp, webchat]
  
  triggers:
    queue_wait_threshold_seconds: 120
    outage_event_threshold: 1000
    
foundry:
  project_name: powergas-voice-agent
  unified_project: true
```

---

## Files

| Component | Location |
|-----------|----------|
| Scenario Config | `registries/scenariostore/utilities/orchestration.yaml` |
| Foundry Project | `registries/scenariostore/utilities/foundry-project.yaml` |
| Concierge Agent | `registries/agentstore/utilities_concierge/` |
| Billing Agent | `registries/agentstore/billing_agent/` |
| Outage Agent | `registries/agentstore/outage_agent/` |
| Service Agent | `registries/agentstore/service_agent/` |
| Usage Agent | `registries/agentstore/usage_agent/` |
| Tools | `registries/toolstore/utilities/` |

---

## Quick Start

```python
from registries.scenariostore.loader import load_scenario

# Load utilities scenario
scenario = load_scenario("utilities")

# Get entry agent
entry = scenario.start_agent  # "UtilitiesConcierge"
```
