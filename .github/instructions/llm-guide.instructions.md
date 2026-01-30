---
applyTo: "**"
---

# LLM Guide: Real-Time Voice Agent Accelerator

> **Purpose:** This document provides context for LLMs (GitHub Copilot, Claude, GPT, etc.) working with this codebase. It explains what the system does, how it's structured, and how to make effective changes.

---

## What This System Is

**Real-Time Voice Agent Accelerator** — An enterprise platform for building AI-powered voice agents using Azure services.

```
Phone Call → Azure Communication Services → WebSocket → [Orchestrator] → AI Agent → Voice Response
```

### Core Capabilities

| Feature | Implementation |
|---------|----------------|
| **Real-time voice** | Sub-second latency conversations via ACS + Speech Services |
| **Multi-agent AI** | YAML-driven agents with tool calling and handoffs |
| **Dual orchestration** | SpeechCascade (control) or VoiceLive (low latency) |
| **Channel support** | Voice, with planned WhatsApp + Web chat |
| **Enterprise Azure** | Container Apps, Managed Identity, App Configuration |

---

## Repository Structure

```
art-voice-agent-accelerator/
├── apps/artagent/
│   ├── backend/              # FastAPI voice service (Python 3.11)
│   │   ├── api/v1/           # REST + WebSocket endpoints
│   │   ├── voice/            # Orchestrators (cascade, voicelive)
│   │   ├── registries/       # Agents, tools, scenarios (YAML-driven)
│   │   └── config/           # Settings, feature flags
│   └── frontend/             # React UI
├── src/                      # Core libraries (reusable across apps)
│   ├── acs/                  # Azure Communication Services
│   ├── aoai/                 # Azure OpenAI client
│   ├── speech/               # STT/TTS processing
│   ├── redis/                # Session state (MemoManager)
│   ├── cosmosdb/             # Persistent storage
│   └── pools/                # Connection pooling
├── infra/terraform/          # Infrastructure as Code
├── tests/                    # Unit, integration, load tests
├── docs/                     # Architecture documentation
└── utils/                    # Cross-cutting (logging, telemetry)
```

---

## Key Design Decisions

### 1. YAML-First Agents
Agents are defined in YAML, not Python classes:
```yaml
# registries/agentstore/concierge/agent.yaml
name: concierge
model: gpt-4o
tools: [transfer_call, check_balance]
```
**Impact:** Don't create agent subclasses. Extend via YAML configuration.

### 2. Scenario-Based Handoffs
Handoff routing is defined in scenarios, not embedded in agents:
```yaml
# registries/scenariostore/banking/orchestration.yaml
handoffs:
  concierge → fraud_agent: when fraud detected
  fraud_agent → concierge: when cleared
```
**Impact:** To change routing, modify scenario YAML, not agent code.

### 3. Connection Pooling
STT, TTS, and AOAI clients are pooled in `src/pools/`:
```python
# ✅ Correct
client = await get_tts_client()

# ❌ Wrong - creates new client per request
client = SpeechSynthesizer(...)
```

### 4. MemoManager for State
Session state managed by Redis-backed `MemoManager`:
```python
# ✅ Correct
await memo_manager.set("customer_id", value)

# ❌ Wrong - in-memory state doesn't survive container restarts
global_state["customer_id"] = value
```

### 5. Async Everything
All HTTP/WebSocket handlers must be async:
```python
# ✅ Correct
async def handle_message(websocket: WebSocket):
    await websocket.send_text(response)

# ❌ Wrong - blocks event loop
def handle_message(websocket: WebSocket):
    websocket.send_text(response)
```

---

## Deployment with Azure Developer CLI

This project uses `azd` for all infrastructure operations.

### Quick Commands

| Action | Command |
|--------|---------|
| **Full deploy** | `azd up` |
| **Infrastructure only** | `azd provision` |
| **Apps only** | `azd deploy` |
| **Teardown** | `azd down --force --purge` |
| **Switch environment** | `azd env select <name>` |
| **View config** | `azd env get-values` |

### Deployment Lifecycle

```
1. azd down --force --purge    # Teardown existing (if any)
2. <make code changes>         # Implement features
3. azd up                      # Deploy to Azure
4. <validate & remediate>      # Test, fix issues
5. azd deploy                  # Redeploy apps (faster)
6. azd down --force --purge    # Cleanup when done
```

### Infrastructure Location

- **Terraform:** `infra/terraform/`
- **Variables:** `infra/terraform/variables.tf`
- **Outputs:** `infra/terraform/outputs.tf`
- **azd hooks:** `devops/scripts/azd/`

---

## Common Tasks

### Adding a New Tool

```python
# apps/artagent/backend/registries/toolstore/my_tool.py
from apps.artagent.backend.registries.toolstore.registry import register_tool

@register_tool
async def my_tool(param: str) -> str:
    """Tool description for the LLM."""
    return result
```

Then add to agent YAML:
```yaml
tools:
  - my_tool
```

### Adding a New Agent

1. Create folder: `registries/agentstore/my_agent/`
2. Add `agent.yaml` with configuration
3. Add `prompt.jinja` with system prompt
4. Register in scenario if needed

### Adding an API Endpoint

```python
# apps/artagent/backend/api/v1/endpoints/my_endpoint.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint():
    return {"status": "ok"}
```

Register in `apps/artagent/backend/api/v1/__init__.py`.

---

## Environment Configuration

### Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `ACS_ENDPOINT` | Azure Communication Services endpoint |
| `ACS_SOURCE_PHONE_NUMBER` | Phone number for outbound calls |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint |
| `AZURE_SPEECH_REGION` | Speech Services region |
| `REDIS_HOST` | Redis cache host |
| `AZURE_COSMOS_ENDPOINT` | Cosmos DB endpoint |
| `AZURE_APPCONFIG_ENDPOINT` | App Configuration endpoint |

### Configuration Files

| File | Purpose | Git Status |
|------|---------|------------|
| `.env.local` | Local dev with Azure resources | Ignored |
| `config/appconfig.json` | Default app settings | Tracked |
| `.azure/<env>/.env` | azd environment state | Ignored |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_handoff_service.py -v

# Run with coverage
pytest tests/ --cov=apps --cov-report=term-missing

# Load testing
make run_load_test_acs_media USERS=10 TIME=60s
```

---

## Code Quality

```bash
# Format code
black . && isort .

# Lint
ruff .

# Type check
mypy apps/ src/

# All checks
make check_code_quality
```

---

## What NOT to Do

| Anti-Pattern | Why It's Bad | Do This Instead |
|--------------|--------------|-----------------|
| Create new SDK clients per request | 100-500ms overhead | Use `src/pools/` |
| Store state in global variables | Doesn't survive restarts | Use `MemoManager` |
| Add `pip install` without approval | Breaks dependency management | Discuss first |
| Create wrapper classes | Adds complexity | Use existing services directly |
| Hardcode handoff logic in agents | Inflexible | Use scenario YAML |
| Synchronous I/O in handlers | Blocks event loop | Always use `async/await` |

---

## Performance Constraints

This is a **real-time voice system**. Latency kills user experience.

| Operation | Target Latency |
|-----------|----------------|
| STT recognition | < 200ms |
| LLM first token | < 500ms |
| TTS synthesis | < 150ms |
| End-to-end turn | < 1 second |
| Agent handoff | < 50ms |

---

## Getting Help

| Topic | Resource |
|-------|----------|
| Architecture | `docs/architecture/README.md` |
| Deployment | `docs/getting-started/quickstart.md` |
| API Reference | `docs/api/README.md` |
| Troubleshooting | `TROUBLESHOOTING.md` |
| Coding Standards | `.github/instructions/coding-standards.instructions.md` |

---

## Summary for LLMs

When working with this codebase:

1. **Read the architecture first** — Understand before implementing
2. **Use existing modules** — Check `src/`, `utils/`, `registries/` before creating new
3. **Follow YAML patterns** — Agents, tools, scenarios are declarative
4. **Respect async** — All I/O must be non-blocking
5. **Use azd for deployment** — `azd up` deploys, `azd down --force --purge` tears down
6. **Think about latency** — Every millisecond matters in voice
