# Deployment Lessons Learned

> Insights from the February 2026 deployment of the Real-Time Voice Agent Accelerator

## Overview

This document captures learnings from deploying the omnichannel voice agent to Azure using `azd`. These insights will help future deployments go more smoothly.

---

## Deployment Architecture

### 1. Two-Step Deployment Process

**Learning:** `azd provision` and `azd deploy` are separate steps.

- `azd provision` creates Azure infrastructure with **placeholder container images**
- `azd deploy` builds Docker images and deploys actual application code
- Container Apps show "Running" with placeholders but **fail health probes**
- Always run both steps (or use `azd up` which runs both)

**Symptoms if you only run `azd provision`:**
- Health check endpoint times out
- Container logs show: "startup probe failed: connection refused"
- Container image is: `mcr.microsoft.com/azuredocs/containerapps-helloworld:latest`

**Fix:** Run `azd deploy` after `azd provision`.

### 2. Phone Number Configuration

**Learning:** Phone numbers cannot be auto-provisioned via Terraform.

- Must be manually acquired from Azure Portal
- Voice telephony is disabled without a configured number
- Backend logs: "⚠️ ACS TELEPHONY DISABLED: Missing required environment variables"

**How to configure:**
```bash
# After deployment, configure phone number
./devops/scripts/configure-phone-number.sh +14165551234

# Update App Configuration
azd provision
```

### 3. Container App Startup Behavior

**Learning:** Initial startup probe failures are expected.

- After `azd provision`, containers use placeholder images
- Placeholder image listens on port 80, but ingress expects port 8000
- This causes "startup probe failed: connection refused"
- After `azd deploy`, probes succeed

**This is not an error** - it's expected behavior until the application is deployed.

---

## Testing Strategy

### 4. Unit Tests (610 total)

**Learning:** Use the correct Python version.

- All tests pass with Python 3.11 in virtual environment
- System Python (3.9 on macOS) causes import errors (`TypeAlias` not available)
- Always activate virtual environment before testing

```bash
source .venv/bin/activate
pytest tests/ -v --ignore=tests/load --ignore=tests/evaluation
```

### 5. Channel Handoff Tests (19 tests)

**Location:** `tests/test_channel_handoff_integration.py`

**What they test:**
- ChannelHandoffHandler context preservation
- Handoff execution returns proper signals
- Tool registration in registry
- Cascade orchestrator integration

```bash
pytest tests/test_channel_handoff_integration.py -v
```

### 6. Omnichannel Scenario Tests (4 scenarios)

**Location:** `tests/evaluation/test_omnichannel_scenarios.py`

**Scenarios:**
1. **Sarah/Toronto** - Power outage → WebChat follow-up
2. **Jean-Pierre/Montreal** - Billing dispute → WhatsApp (French)
3. **Raj/Vancouver** - New service setup → Multi-day journey
4. **Maria/Calgary** - Emergency gas leak → Escalation + follow-up

```bash
pytest tests/evaluation/test_omnichannel_scenarios.py -v
```

---

## Infrastructure Insights

### 7. Resource Naming Convention

**Pattern:** `{resource}-{env}-{token}`

- Example: `artagent-backend-hffwg8l2`
- Token is consistent across all resources in the same environment
- Makes resource identification easy in Azure Portal

### 8. App Configuration

**Stats:** 57 settings + 8 feature flags synced automatically

- Post-provisioning hook syncs config from `config/appconfig.json`
- Changes require `azd provision` to update
- Backend picks up changes on next container restart

### 9. EasyAuth on Frontend

**Behavior:**
- Automatically enabled during provisioning
- Returns 401 for unauthenticated requests
- Backend health endpoint (`/api/v1/health`) is public (no auth required)

---

## Recommended Workflow

### Development Cycle

```bash
# Make code changes
vim apps/artagent/backend/...

# Deploy changes only
azd deploy --no-prompt

# Verify
curl https://artagent-backend-XXXXX.azurecontainerapps.io/api/v1/health
```

### Full Deployment

```bash
# Preflight checks with auto-fix
./devops/scripts/preflight-check.sh --fix-all

# Deploy everything
azd up --no-prompt

# Configure phone number (optional)
./devops/scripts/configure-phone-number.sh +14165551234
azd provision --no-prompt
```

### Teardown

```bash
# Remove all resources
azd down --force --purge
```

---

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Health check times out | Container using placeholder image | Run `azd deploy` |
| "startup probe failed" | Application not deployed | Run `azd deploy` |
| Voice calls don't work | No phone number configured | Azure Portal + `configure-phone-number.sh` |
| webchat-demo deploy fails | ~~Missing infrastructure tag~~ **Fixed** | Tag added to Terraform |
| 401 on frontend | EasyAuth enabled | Login via Azure AD |
| Import errors in tests | Wrong Python version | Use `source .venv/bin/activate` |
| "TypeAlias not found" | Python < 3.10 | Use Python 3.11+ |

---

## Preflight Check Improvements

The preflight script was enhanced based on this deployment:

1. **Phone number check** - Warns if not configured
2. **Deployment workflow check** - Explains two-step process
3. **Auto-fix options** - `--fix` (interactive) and `--fix-all` (automatic)
4. **Container image check** - Detects placeholder images

Run preflight before deployment:
```bash
./devops/scripts/preflight-check.sh --fix-all --verbose
```

---

## Terraform/azd Optimizations Applied

### 10. Fixed: webchat-demo azd-service-name Tag

**Issue:** `azd deploy` failed for webchat-demo with error:
```
resource not found: unable to find a resource tagged with 'azd-service-name: webchat-demo'
```

**Root Cause:** The `infra/terraform/webchat-demo.tf` was missing the `azd-service-name` tag that azd uses to find the Container App resource.

**Fix Applied:** Updated webchat-demo.tf to include the tag:
```terraform
tags = merge(local.tags, {
  "azd-service-name" = "webchat-demo"
})
```

**Pattern:** All Container Apps must have `azd-service-name` matching the service name in `azure.yaml`:
- `rtaudio-client` → tag: `azd-service-name = "rtaudio-client"` ✅
- `rtaudio-server` → tag: `azd-service-name = "rtaudio-server"` ✅  
- `webchat-demo` → tag: `azd-service-name = "webchat-demo"` ✅ (fixed)

### 11. Deployment Already Optimized

The following optimizations were already in place:

| Feature | Status | Benefit |
|---------|--------|---------|
| `remoteBuild: true` | ✅ Enabled | Builds in Azure ACR, not locally |
| Lifecycle `ignore_changes` | ✅ Configured | Prevents Terraform drift on images |
| Placeholder images | ✅ Correct pattern | Fast initial provisioning |
| Parallel post-provision tasks | ✅ Possible | Tasks run independently |
| Auto-skip timeouts | ✅ 10-15 seconds | Non-blocking in CI/CD |

### 12. Recommended: Use azd up

**Optimization:** Use `azd up` instead of separate `provision` + `deploy`:

```bash
# Single command (recommended)
azd up --no-prompt

# Equivalent to:
azd provision --no-prompt && azd deploy --no-prompt
```

---

## Files Created/Updated

| File | Description |
|------|-------------|
| `devops/scripts/preflight-check.sh` | Enhanced with phone number and deployment checks |
| `devops/scripts/configure-phone-number.sh` | New helper for phone configuration |
| `tests/evaluation/test_omnichannel_scenarios.py` | 4 customer scenario tests |
| `infra/terraform/webchat-demo.tf` | Added missing `azd-service-name` tag |
| `docs/deployment/lessons-learned.md` | This document |

---

## Key Takeaways

1. **Always run both provision and deploy** - or use `azd up`
2. **Phone numbers are manual** - configure after deployment
3. **Health probe failures are normal** - until `azd deploy` completes
4. **Use Python 3.11** - not system Python
5. **610 tests passing** - run before deployment
6. **Preflight checks help** - use `--fix-all` for automation
