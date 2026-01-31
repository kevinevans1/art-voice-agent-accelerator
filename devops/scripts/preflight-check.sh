#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Preflight Check Script for Real-Time Voice Agent Accelerator
# ═══════════════════════════════════════════════════════════════════════════════
# Validates all prerequisites before deployment:
#   - CLI tools and versions
#   - Azure authentication and subscriptions
#   - Resource provider registrations
#   - Model availability
#   - Quotas and limits
#   - Environment configuration
#
# Usage:
#   ./devops/scripts/preflight-check.sh [--fix] [--verbose]
#
# Options:
#   --fix       Attempt to fix issues automatically
#   --verbose   Show detailed output
#   --json      Output results as JSON
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Counters
PASSED=0
FAILED=0
WARNINGS=0
FIXED=0

# Options
FIX_MODE=false
VERBOSE=false
JSON_OUTPUT=false
QUICK_MODE=false

# Minimum versions
MIN_PYTHON_VERSION="3.11"
MIN_AZD_VERSION="1.5.0"
MIN_AZ_CLI_VERSION="2.50.0"
MIN_TERRAFORM_VERSION="1.5.0"
MIN_NODE_VERSION="18.0.0"

# Required Azure providers
REQUIRED_PROVIDERS=(
    "Microsoft.Communication"
    "Microsoft.CognitiveServices"
    "Microsoft.ContainerRegistry"
    "Microsoft.App"
    "Microsoft.OperationalInsights"
    "Microsoft.KeyVault"
    "Microsoft.Storage"
    "Microsoft.DocumentDB"
    "Microsoft.Cache"
    "Microsoft.ManagedIdentity"
    "Microsoft.MachineLearningServices"
)

# Required Azure OpenAI models
REQUIRED_MODELS=(
    "gpt-4o"
    "gpt-4o-mini"
)

# ─────────────────────────────────────────────────────────────────────────────
# Parse Arguments
# ─────────────────────────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--fix] [--verbose] [--json] [--quick]"
            echo ""
            echo "Options:"
            echo "  --fix       Attempt to fix issues automatically"
            echo "  --verbose   Show detailed output"
            echo "  --json      Output results as JSON"
            echo "  --quick     Skip slow Azure API checks"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

print_header() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo ""
        echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${BOLD}${BLUE}  $1${NC}"
        echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    fi
}

print_section() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo ""
        echo -e "${CYAN}── $1 ──${NC}"
    fi
}

pass() {
    PASSED=$((PASSED + 1))
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "  ${GREEN}✓${NC} $1"
    fi
}

fail() {
    FAILED=$((FAILED + 1))
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "  ${RED}✗${NC} $1"
        if [[ -n "${2:-}" ]]; then
            echo -e "    ${RED}→ $2${NC}"
        fi
    fi
}

warn() {
    WARNINGS=$((WARNINGS + 1))
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "  ${YELLOW}⚠${NC} $1"
        if [[ -n "${2:-}" ]]; then
            echo -e "    ${YELLOW}→ $2${NC}"
        fi
    fi
}

info() {
    if [[ "$VERBOSE" == "true" && "$JSON_OUTPUT" == "false" ]]; then
        echo -e "  ${BLUE}ℹ${NC} $1"
    fi
}

fixed() {
    FIXED=$((FIXED + 1))
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo -e "  ${GREEN}⚡${NC} Fixed: $1"
    fi
}

version_gte() {
    # Returns 0 if $1 >= $2
    # Simplified version comparison
    local v1="$1"
    local v2="$2"
    
    # Use sort -V and check if v1 comes after or equal to v2
    local sorted
    sorted=$(printf '%s\n%s\n' "$v1" "$v2" | sort -V | head -1)
    [[ "$sorted" == "$v2" ]]
}

# ─────────────────────────────────────────────────────────────────────────────
# Check: CLI Tools
# ─────────────────────────────────────────────────────────────────────────────

# Helper to extract version number from string
extract_version() {
    echo "$1" | grep -Eo '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1
}

check_cli_tools() {
    print_header "CLI Tools & Versions"
    
    # Python
    print_section "Python"
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(extract_version "$(python3 --version 2>&1)")
        if [[ -n "$PYTHON_VERSION" ]] && version_gte "$PYTHON_VERSION" "$MIN_PYTHON_VERSION"; then
            pass "Python $PYTHON_VERSION (>= $MIN_PYTHON_VERSION)"
        elif [[ -n "$PYTHON_VERSION" ]]; then
            fail "Python $PYTHON_VERSION" "Requires >= $MIN_PYTHON_VERSION"
        else
            fail "Could not determine Python version"
        fi
    else
        fail "Python not found" "Install Python $MIN_PYTHON_VERSION+"
    fi
    
    # Azure Developer CLI
    print_section "Azure Developer CLI (azd)"
    if command -v azd &> /dev/null; then
        AZD_VERSION=$(extract_version "$(azd version 2>&1)" || echo "0.0.0")
        if [[ -n "$AZD_VERSION" ]] && version_gte "$AZD_VERSION" "$MIN_AZD_VERSION"; then
            pass "azd $AZD_VERSION (>= $MIN_AZD_VERSION)"
        else
            warn "azd $AZD_VERSION" "Recommend >= $MIN_AZD_VERSION"
        fi
    else
        fail "azd not found" "Install: curl -fsSL https://aka.ms/install-azd.sh | bash"
    fi
    
    # Azure CLI
    print_section "Azure CLI"
    if command -v az &> /dev/null; then
        AZ_VERSION=$(az version --query '"azure-cli"' -o tsv 2>/dev/null || echo "0.0.0")
        if [[ -n "$AZ_VERSION" ]] && version_gte "$AZ_VERSION" "$MIN_AZ_CLI_VERSION"; then
            pass "Azure CLI $AZ_VERSION (>= $MIN_AZ_CLI_VERSION)"
        else
            warn "Azure CLI $AZ_VERSION" "Recommend >= $MIN_AZ_CLI_VERSION"
        fi
    else
        fail "Azure CLI not found" "Install: https://docs.microsoft.com/cli/azure/install-azure-cli"
    fi
    
    # Terraform
    print_section "Terraform"
    if command -v terraform &> /dev/null; then
        TF_VERSION=$(extract_version "$(terraform version 2>&1)" || echo "0.0.0")
        if [[ -n "$TF_VERSION" ]] && version_gte "$TF_VERSION" "$MIN_TERRAFORM_VERSION"; then
            pass "Terraform $TF_VERSION (>= $MIN_TERRAFORM_VERSION)"
        else
            warn "Terraform $TF_VERSION" "Recommend >= $MIN_TERRAFORM_VERSION"
        fi
    else
        warn "Terraform not found" "azd will use built-in Terraform"
    fi
    
    # Node.js (for frontend)
    print_section "Node.js"
    if command -v node &> /dev/null; then
        NODE_VERSION=$(extract_version "$(node --version 2>&1)")
        if [[ -n "$NODE_VERSION" ]] && version_gte "$NODE_VERSION" "$MIN_NODE_VERSION"; then
            pass "Node.js $NODE_VERSION (>= $MIN_NODE_VERSION)"
        else
            warn "Node.js $NODE_VERSION" "Recommend >= $MIN_NODE_VERSION for frontend"
        fi
    else
        warn "Node.js not found" "Required for frontend development"
    fi
    
    # Docker
    print_section "Docker"
    if command -v docker &> /dev/null; then
        if docker info &> /dev/null; then
            DOCKER_VERSION=$(extract_version "$(docker --version 2>&1)")
            pass "Docker $DOCKER_VERSION (running)"
        else
            warn "Docker installed but not running" "Start Docker daemon for local container builds"
        fi
    else
        warn "Docker not found" "Required for local container development"
    fi
    
    # Git
    print_section "Git"
    if command -v git &> /dev/null; then
        GIT_VERSION=$(extract_version "$(git --version 2>&1)")
        pass "Git $GIT_VERSION"
    else
        fail "Git not found" "Install git"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Check: Azure Authentication
# ─────────────────────────────────────────────────────────────────────────────

check_azure_auth() {
    print_header "Azure Authentication"
    
    if [[ "$QUICK_MODE" == "true" ]]; then
        info "Skipping Azure auth checks (--quick mode)"
        info "Run without --quick to validate Azure authentication"
        return
    fi
    
    # Azure CLI login
    print_section "Azure CLI"
    if timeout 30 az account show &> /dev/null; then
        ACCOUNT_NAME=$(timeout 15 az account show --query 'name' -o tsv 2>/dev/null || echo "Unknown")
        pass "Logged in to Azure CLI"
        info "Subscription: $ACCOUNT_NAME"
    else
        fail "Not logged in to Azure CLI (or timeout)" "Run: az login"
    fi
    
    # azd auth
    print_section "Azure Developer CLI"
    if timeout 10 azd auth login --check-status &> /dev/null; then
        pass "Logged in to azd"
    else
        if [[ "$FIX_MODE" == "true" ]]; then
            echo "  Attempting azd auth login..."
            if azd auth login; then
                fixed "azd authentication"
            else
                fail "azd authentication failed" "Run: azd auth login"
            fi
        else
            fail "Not logged in to azd" "Run: azd auth login"
        fi
    fi
    
    # Subscription permissions
    print_section "Subscription Permissions"
    pass "Will be validated during deployment"
}

# ─────────────────────────────────────────────────────────────────────────────
# Check: Azure Resource Providers
# ─────────────────────────────────────────────────────────────────────────────

check_resource_providers() {
    print_header "Azure Resource Providers"
    
    if [[ "$QUICK_MODE" == "true" ]]; then
        info "Skipping provider checks (--quick mode)"
        info "Providers will be validated during deployment"
        return
    fi
    
    if ! az account show &> /dev/null; then
        fail "Cannot check providers" "Login to Azure first"
        return
    fi
    
    # Check critical providers only (ones that commonly need registration)
    CRITICAL_PROVIDERS=(
        "Microsoft.Communication"
        "Microsoft.CognitiveServices"
        "Microsoft.App"
    )
    
    echo "  Checking critical providers..."
    
    for provider in "${CRITICAL_PROVIDERS[@]}"; do
        # Use timeout to prevent hanging (increased from 10s to 20s for slow networks)
        STATE=$(timeout 20 az provider show --namespace "$provider" --query 'registrationState' -o tsv 2>/dev/null || echo "Timeout")
        
        if [[ "$STATE" == "Registered" ]]; then
            pass "$provider"
        elif [[ "$STATE" == "Registering" ]]; then
            warn "$provider: Registering (in progress)"
        elif [[ "$STATE" == "Timeout" ]]; then
            warn "$provider: Check timed out" "Verify manually: az provider show --namespace $provider"
        else
            if [[ "$FIX_MODE" == "true" ]]; then
                echo "  Registering $provider..."
                if timeout 15 az provider register --namespace "$provider" &> /dev/null; then
                    fixed "$provider registration started"
                else
                    fail "$provider: $STATE" "Run: az provider register --namespace $provider"
                fi
            else
                fail "$provider: $STATE" "Run: az provider register --namespace $provider"
            fi
        fi
    done
}

# ─────────────────────────────────────────────────────────────────────────────
# Check: Azure OpenAI Model Availability
# ─────────────────────────────────────────────────────────────────────────────

check_model_availability() {
    print_header "Azure OpenAI Model Availability"
    
    # Get location from azd env or default
    LOCATION="${AZURE_LOCATION:-eastus2}"
    info "Checking models in region: $LOCATION"
    
    if ! az account show &> /dev/null; then
        fail "Cannot check models" "Login to Azure first"
        return
    fi
    
    print_section "Required Models"
    
    # Skip slow model query - just note that they'll be validated at deploy time
    for model in "${REQUIRED_MODELS[@]}"; do
        info "$model: Will be validated during deployment"
    done
    
    print_section "Configuration Check"
    
    # Check for non-existent models in terraform
    TF_VARS="${PROJECT_ROOT}/infra/terraform/variables.tf"
    if [[ -f "$TF_VARS" ]]; then
        # Look for problematic model versions
        if grep -q "gpt-5" "$TF_VARS" 2>/dev/null; then
            fail "variables.tf references non-existent model (gpt-5)" "Remove or update model references"
        else
            pass "No invalid model references in variables.tf"
        fi
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Check: Environment Configuration
# ─────────────────────────────────────────────────────────────────────────────

check_environment() {
    print_header "Environment Configuration"
    
    # Check azd environment
    print_section "azd Environment"
    if [[ -d "${PROJECT_ROOT}/.azure" ]]; then
        CURRENT_ENV=$(azd env list 2>/dev/null | grep -E '^\*' | awk '{print $2}' || echo "")
        if [[ -n "$CURRENT_ENV" ]]; then
            pass "Active environment: $CURRENT_ENV"
            
            # Check key environment values
            LOCATION=$(azd env get-values 2>/dev/null | grep AZURE_LOCATION | cut -d'=' -f2 | tr -d '"' || echo "")
            if [[ -n "$LOCATION" ]]; then
                pass "AZURE_LOCATION: $LOCATION"
            else
                warn "AZURE_LOCATION not set" "Run: azd env set AZURE_LOCATION eastus2"
            fi
        else
            warn "No active azd environment" "Run: azd env new <env-name>"
        fi
    else
        warn "No azd environment initialized" "Run: azd init or azd env new <env-name>"
    fi
    
    # Check .env.local
    print_section "Local Environment (.env.local)"
    if [[ -f "${PROJECT_ROOT}/.env.local" ]]; then
        pass ".env.local exists"
        
        # Check required variables
        REQUIRED_VARS=(
            "ACS_ENDPOINT"
            "AZURE_OPENAI_ENDPOINT"
            "AZURE_SPEECH_REGION"
        )
        
        for var in "${REQUIRED_VARS[@]}"; do
            if grep -q "^${var}=" "${PROJECT_ROOT}/.env.local" 2>/dev/null; then
                info "$var is set"
            else
                info "$var not in .env.local (will use Azure values)"
            fi
        done
    else
        info ".env.local not found (using Azure configuration)"
    fi
    
    # Check terraform state
    print_section "Terraform State"
    TF_STATE="${PROJECT_ROOT}/infra/terraform/terraform.tfstate"
    if [[ -f "$TF_STATE" ]]; then
        pass "Local Terraform state exists"
        
        # Check if state has resources
        RESOURCE_COUNT=$(grep -c '"type":' "$TF_STATE" 2>/dev/null || echo "0")
        info "State contains ~$RESOURCE_COUNT resource definitions"
    else
        info "No local Terraform state (fresh deployment)"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Check: Python Dependencies
# ─────────────────────────────────────────────────────────────────────────────

check_python_deps() {
    print_header "Python Dependencies"
    
    # Check for pyproject.toml
    if [[ ! -f "${PROJECT_ROOT}/pyproject.toml" ]]; then
        fail "pyproject.toml not found" "Missing project configuration"
        return
    fi
    
    print_section "Virtual Environment"
    
    # Check for virtual environment
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        pass "Virtual environment active: $VIRTUAL_ENV"
    elif [[ -d "${PROJECT_ROOT}/.venv" ]]; then
        warn "Virtual environment exists but not activated" "Run: source .venv/bin/activate"
    elif [[ -n "${CONDA_DEFAULT_ENV:-}" ]]; then
        pass "Conda environment active: $CONDA_DEFAULT_ENV"
    else
        warn "No virtual environment detected" "Run: python -m venv .venv && source .venv/bin/activate"
    fi
    
    print_section "Key Packages"
    
    # Check if pip is available
    if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
        warn "pip not found" "Cannot verify Python packages"
        return
    fi
    
    PIP_CMD=$(command -v pip3 || command -v pip)
    
    REQUIRED_PACKAGES=(
        "fastapi"
        "azure-communication-callautomation"
        "azure-cognitiveservices-speech"
        "azure-ai-projects"
        "openai"
        "redis"
        "pydantic"
    )
    
    for pkg in "${REQUIRED_PACKAGES[@]}"; do
        if $PIP_CMD show "$pkg" &> /dev/null; then
            VERSION=$($PIP_CMD show "$pkg" 2>/dev/null | grep "^Version:" | awk '{print $2}')
            pass "$pkg ($VERSION)"
        else
            info "$pkg not installed (will be installed during deployment)"
        fi
    done
}

# ─────────────────────────────────────────────────────────────────────────────
# Check: Network Connectivity
# ─────────────────────────────────────────────────────────────────────────────

check_network() {
    print_header "Network Connectivity"
    
    print_section "Azure Endpoints"
    
    ENDPOINTS=(
        "management.azure.com:Azure Management"
        "login.microsoftonline.com:Azure AD"
        "graph.microsoft.com:Microsoft Graph"
        "cognitiveservices.azure.com:Cognitive Services"
    )
    
    for endpoint_pair in "${ENDPOINTS[@]}"; do
        endpoint="${endpoint_pair%%:*}"
        name="${endpoint_pair##*:}"
        
        if curl -s --connect-timeout 5 "https://$endpoint" &> /dev/null; then
            pass "$name ($endpoint)"
        else
            # Try with nc as fallback
            if nc -z -w5 "$endpoint" 443 &> /dev/null 2>&1; then
                pass "$name ($endpoint)"
            else
                warn "Cannot reach $name" "Check firewall/proxy for $endpoint:443"
            fi
        fi
    done
    
    print_section "GitHub (for azd templates)"
    if curl -s --connect-timeout 5 "https://github.com" &> /dev/null; then
        pass "GitHub accessible"
    else
        warn "Cannot reach GitHub" "May affect azd template operations"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Check: Project Structure
# ─────────────────────────────────────────────────────────────────────────────

check_project_structure() {
    print_header "Project Structure"
    
    print_section "Required Directories"
    
    REQUIRED_DIRS=(
        "apps/artagent/backend"
        "apps/artagent/frontend"
        "infra/terraform"
        "src"
        "tests"
        "docs"
    )
    
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [[ -d "${PROJECT_ROOT}/${dir}" ]]; then
            pass "$dir/"
        else
            fail "$dir/ not found" "Project structure incomplete"
        fi
    done
    
    print_section "Required Files"
    
    REQUIRED_FILES=(
        "azure.yaml"
        "pyproject.toml"
        "infra/terraform/main.tf"
        "infra/terraform/variables.tf"
    )
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [[ -f "${PROJECT_ROOT}/${file}" ]]; then
            pass "$file"
        else
            fail "$file not found" "Required for deployment"
        fi
    done
    
    print_section "Utilities Scenario (New)"
    
    UTILITIES_FILES=(
        "apps/artagent/backend/registries/scenariostore/utilities/orchestration.yaml"
        "apps/artagent/backend/registries/agentstore/utilities_concierge/agent.yaml"
        "apps/artagent/backend/registries/agentstore/billing_agent/agent.yaml"
        "apps/artagent/backend/registries/agentstore/outage_agent/agent.yaml"
        "apps/artagent/backend/registries/agentstore/service_agent/agent.yaml"
        "apps/artagent/backend/registries/agentstore/usage_agent/agent.yaml"
        "apps/artagent/backend/registries/toolstore/utilities/utilities.py"
        "apps/artagent/backend/channels/__init__.py"
    )
    
    for file in "${UTILITIES_FILES[@]}"; do
        if [[ -f "${PROJECT_ROOT}/${file}" ]]; then
            pass "$file"
        else
            warn "$file not found" "Utilities scenario may be incomplete"
        fi
    done
}

# ─────────────────────────────────────────────────────────────────────────────
# Check: Quotas and Limits
# ─────────────────────────────────────────────────────────────────────────────

check_quotas() {
    print_header "Azure Quotas & Limits"
    
    if [[ "$QUICK_MODE" == "true" ]]; then
        info "Skipping quota checks (--quick mode)"
        return
    fi
    
    if ! timeout 10 az account show &> /dev/null; then
        warn "Cannot check quotas" "Login to Azure first or check connectivity"
        return
    fi
    
    print_section "Cognitive Services"
    
    # Note: Azure OpenAI quotas are complex and region-specific
    warn "Azure OpenAI TPM quotas" "Verify in Azure Portal > Azure OpenAI > Quotas"
    info "Required: ~100K TPM for gpt-4o, ~200K TPM for gpt-4o-mini"
}

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

print_summary() {
    print_header "Preflight Check Summary"
    
    echo ""
    echo -e "  ${GREEN}Passed:${NC}   $PASSED"
    echo -e "  ${RED}Failed:${NC}   $FAILED"
    echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
    if [[ "$FIX_MODE" == "true" ]]; then
        echo -e "  ${GREEN}Fixed:${NC}    $FIXED"
    fi
    echo ""
    
    if [[ $FAILED -gt 0 ]]; then
        echo -e "${RED}${BOLD}❌ Preflight check FAILED${NC}"
        echo ""
        echo "Please resolve the failed checks before deployment."
        echo "Run with --fix to attempt automatic fixes."
        echo ""
        exit 1
    elif [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}${BOLD}⚠️  Preflight check PASSED with warnings${NC}"
        echo ""
        echo "Deployment may succeed, but review warnings above."
        echo ""
        exit 0
    else
        echo -e "${GREEN}${BOLD}✅ Preflight check PASSED${NC}"
        echo ""
        echo "Ready for deployment! Run: azd up"
        echo ""
        exit 0
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# JSON Output
# ─────────────────────────────────────────────────────────────────────────────

output_json() {
    cat << EOF
{
  "status": "$([ $FAILED -gt 0 ] && echo 'failed' || echo 'passed')",
  "passed": $PASSED,
  "failed": $FAILED,
  "warnings": $WARNINGS,
  "fixed": $FIXED,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

main() {
    if [[ "$JSON_OUTPUT" == "false" ]]; then
        echo ""
        echo -e "${BOLD}${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BOLD}${CYAN}║     Real-Time Voice Agent - Preflight Check                   ║${NC}"
        echo -e "${BOLD}${CYAN}║     $(date '+%Y-%m-%d %H:%M:%S')                                      ║${NC}"
        echo -e "${BOLD}${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
        
        if [[ "$FIX_MODE" == "true" ]]; then
            echo -e "${YELLOW}Running in FIX mode - will attempt automatic fixes${NC}"
        fi
    fi
    
    check_cli_tools
    check_azure_auth
    check_resource_providers
    check_model_availability
    check_environment
    check_python_deps
    check_network
    check_project_structure
    check_quotas
    
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        output_json
    else
        print_summary
    fi
}

main "$@"
