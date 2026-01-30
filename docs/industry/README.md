# Industry Scenarios

> **TL;DR:** A scenario = which agents + how they connect + when to greet

---

## The Pattern

```yaml
scenario.yaml
├── start_agent      # Entry point
├── agents[]         # Who participates  
├── handoffs[]       # How they connect
└── agent_defaults   # Shared variables
```

---

## Available Scenarios

| Scenario | Entry | Model | Agents |
|:---------|:------|:------|:-------|
| [**Banking**](banking.md) | BankingConcierge | Service-first | Cards, Investments |
| [**Insurance**](insurance.md) | AuthAgent | Security-first | Policy, FNOL, Subro |
| [**Utilities**](utilities.md) | UtilitiesConcierge | Omnichannel | Billing, Outage, Service, Usage |

---

## Architecture Comparison

=== "Banking: Hub & Spoke"

    ```
           ┌──────────────────┐
           │ BankingConcierge │ ← Entry
           └────────┬─────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
    ┌──────────┐       ┌──────────────┐
    │  Cards   │ ◄───► │ Investments  │
    └──────────┘       └──────────────┘
    
    All handoffs: DISCRETE (seamless)
    ```

=== "Insurance: Security Gate"

    ```
              ┌───────────┐
              │ AuthAgent │ ← Entry (gate)
              └─────┬─────┘
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
    ┌────────┐ ┌────────┐ ┌──────────┐
    │ Policy │ │  FNOL  │ │  Subro   │
    └────────┘ └────────┘ └──────────┘
        ◄──────────►          (B2B)
    
    B2C: ANNOUNCED | B2B: DISCRETE
    ```

=== "Utilities: Omnichannel"

    ```
              ┌────────────────────┐
              │ UtilitiesConcierge │ ← Entry
              └─────────┬──────────┘
                        │
          ┌─────────┬───┴───┬─────────┐
          ▼         ▼       ▼         ▼
    ┌─────────┐ ┌───────┐ ┌───────┐ ┌───────┐
    │ Billing │ │Outage │ │Service│ │ Usage │
    └─────────┘ └───────┘ └───────┘ └───────┘
                    │
              [DISCRETE]
           (Safety-first)
    
    Outage: DISCRETE | Others: ANNOUNCED
    📱 Omnichannel: Voice → WhatsApp → WebChat
    ```

---

## Handoff Types

| Type | Behavior | Use When |
|:-----|:---------|:---------|
| `discrete` | Silent transition | Same conversation continues |
| `announced` | Agent greets caller | New department / specialist |

---

## Quick Start

```python
from registries.scenariostore.loader import load_scenario

# Load scenario
scenario = load_scenario("banking")  # or "insurance"

# Get handoff routing
handoffs = scenario.build_handoff_map()
# → {"handoff_card_recommendation": "CardRecommendation", ...}
```

---

## Creating a New Scenario

```bash
# 1. Create directory
mkdir -p registries/scenariostore/retail

# 2. Create orchestration.yaml
cat > registries/scenariostore/retail/orchestration.yaml << 'EOF'
name: retail
start_agent: CustomerService
agents:
  - CustomerService
  - Returns
  - TechSupport
handoffs:
  - from: CustomerService
    to: Returns
    tool: handoff_returns
    type: discrete
EOF

# 3. Done. Scenario auto-discovered.
```
