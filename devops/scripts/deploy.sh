#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Deployment Script for Real-Time Voice Agent Accelerator
# ═══════════════════════════════════════════════════════════════════════════════
# Complete deployment workflow including:
#   - Azure login and subscription selection
#   - Preflight checks (optional)
#   - Environment setup
#   - Infrastructure provisioning
#   - Application deployment
#
# Usage:
#   ./devops/scripts/deploy.sh [options]
#
# Options:
#   --skip-preflight    Skip preflight checks
#   --skip-login        Skip Azure login prompts (assume already logged in)
#   --env <name>        Use specific azd environment name
#   --location <region> Azure region (default: eastus2)
#   --subscription <id> Azure subscription ID to use
#   --provision-only    Only provision infrastructure, don't deploy apps
#   --deploy-only       Only deploy apps (infrastructure must exist)
#   --destroy           Teardown the deployment
#   -y, --yes           Skip confirmation prompts
#   -h, --help          Show this help
# ═══════════════════════════════════════════════════════════════════════════════

set -eo pipefail

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
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Default options
SKIP_PREFLIGHT=false
SKIP_LOGIN=false
ENV_NAME=""
LOCATION="eastus2"
SUBSCRIPTION_ID=""
PROVISION_ONLY=false
DEPLOY_ONLY=false
DESTROY_MODE=false
AUTO_YES=false

# ─────────────────────────────────────────────────────────────────────────────
# Parse Arguments
# ─────────────────────────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-preflight)
            SKIP_PREFLIGHT=true
            shift
            ;;
        --skip-login)
            SKIP_LOGIN=true
            shift
            ;;
        --env)
            ENV_NAME="$2"
            shift 2
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --subscription)
            SUBSCRIPTION_ID="$2"
            shift 2
            ;;
        --provision-only)
            PROVISION_ONLY=true
            shift
            ;;
        --deploy-only)
            DEPLOY_ONLY=true
            shift
            ;;
        --destroy)
            DESTROY_MODE=true
            shift
            ;;
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        -h|--help)
            cat << EOF
Real-Time Voice Agent Accelerator - Deployment Script

Usage: $0 [options]

Options:
  --skip-preflight    Skip preflight checks
  --skip-login        Skip Azure login prompts (assume already logged in)
  --env <name>        Use specific azd environment name
  --location <region> Azure region (default: eastus2)
  --subscription <id> Azure subscription ID to use
  --provision-only    Only provision infrastructure, don't deploy apps
  --deploy-only       Only deploy apps (infrastructure must exist)
  --destroy           Teardown the deployment
  -y, --yes           Skip confirmation prompts
  -h, --help          Show this help

Examples:
  # Full deployment with interactive prompts
  $0

  # Quick deployment (skip preflight, use defaults)
  $0 --skip-preflight -y

  # Deploy to specific environment and region
  $0 --env production --location westus2

  # Teardown existing deployment
  $0 --destroy -y

EOF
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

print_banner() {
    echo ""
    echo -e "${BOLD}${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║     Real-Time Voice Agent - Deployment                        ║${NC}"
    echo -e "${BOLD}${CYAN}║     $(date '+%Y-%m-%d %H:%M:%S')                                      ║${NC}"
    echo -e "${BOLD}${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE}  STEP $1: $2${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

confirm() {
    if [[ "$AUTO_YES" == "true" ]]; then
        return 0
    fi
    
    local prompt="${1:-Continue?}"
    echo -e -n "${YELLOW}$prompt [y/N]: ${NC}"
    read -r response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Azure Login
# ─────────────────────────────────────────────────────────────────────────────

azure_login() {
    print_step "1" "Azure Authentication"
    
    if [[ "$SKIP_LOGIN" == "true" ]]; then
        info "Skipping login checks (--skip-login)"
        return 0
    fi
    
    # Check Azure CLI login
    echo "Checking Azure CLI authentication..."
    if az account show &> /dev/null; then
        CURRENT_ACCOUNT=$(az account show --query 'user.name' -o tsv 2>/dev/null || echo "Unknown")
        CURRENT_SUB=$(az account show --query 'name' -o tsv 2>/dev/null || echo "Unknown")
        success "Azure CLI: Logged in as $CURRENT_ACCOUNT"
        info "Current subscription: $CURRENT_SUB"
    else
        warn "Not logged in to Azure CLI"
        echo ""
        echo "Opening browser for Azure login..."
        if az login; then
            success "Azure CLI login successful"
        else
            error "Azure CLI login failed"
            exit 1
        fi
    fi
    
    # Check azd login
    echo ""
    echo "Checking Azure Developer CLI authentication..."
    if azd auth login --check-status &> /dev/null; then
        success "Azure Developer CLI: Logged in"
    else
        warn "Not logged in to Azure Developer CLI"
        echo ""
        echo "Logging in to azd..."
        if azd auth login; then
            success "azd login successful"
        else
            error "azd login failed"
            exit 1
        fi
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Subscription Selection
# ─────────────────────────────────────────────────────────────────────────────

select_subscription() {
    print_step "2" "Subscription Selection"
    
    if [[ "$SKIP_LOGIN" == "true" ]]; then
        info "Skipping subscription selection (--skip-login)"
        return 0
    fi
    
    # If subscription ID provided via CLI
    if [[ -n "$SUBSCRIPTION_ID" ]]; then
        info "Using subscription from command line: $SUBSCRIPTION_ID"
        if az account set --subscription "$SUBSCRIPTION_ID"; then
            success "Subscription set successfully"
        else
            error "Failed to set subscription: $SUBSCRIPTION_ID"
            exit 1
        fi
        return 0
    fi
    
    # List available subscriptions
    echo "Available subscriptions:"
    echo ""
    
    SUBS=$(az account list --query "[].{name:name, id:id, isDefault:isDefault}" -o json 2>/dev/null)
    
    if [[ -z "$SUBS" || "$SUBS" == "[]" ]]; then
        error "No subscriptions found"
        exit 1
    fi
    
    # Display subscriptions with numbers
    echo "$SUBS" | jq -r 'to_entries | .[] | "\(.key + 1)) \(.value.name) \(if .value.isDefault then "(current)" else "" end)"'
    
    echo ""
    CURRENT_SUB=$(az account show --query 'name' -o tsv 2>/dev/null)
    
    if confirm "Use current subscription '$CURRENT_SUB'?"; then
        success "Using current subscription"
    else
        echo ""
        echo -n "Enter subscription number (or 'q' to quit): "
        read -r choice
        
        if [[ "$choice" == "q" ]]; then
            echo "Deployment cancelled"
            exit 0
        fi
        
        # Get subscription ID by index
        SUB_ID=$(echo "$SUBS" | jq -r ".[$((choice - 1))].id" 2>/dev/null)
        
        if [[ -z "$SUB_ID" || "$SUB_ID" == "null" ]]; then
            error "Invalid selection"
            exit 1
        fi
        
        if az account set --subscription "$SUB_ID"; then
            NEW_SUB=$(az account show --query 'name' -o tsv)
            success "Switched to: $NEW_SUB"
        else
            error "Failed to switch subscription"
            exit 1
        fi
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Preflight Checks
# ─────────────────────────────────────────────────────────────────────────────

run_preflight() {
    print_step "3" "Preflight Checks"
    
    if [[ "$SKIP_PREFLIGHT" == "true" ]]; then
        info "Skipping preflight checks (--skip-preflight)"
        return 0
    fi
    
    PREFLIGHT_SCRIPT="${SCRIPT_DIR}/preflight-check.sh"
    
    if [[ ! -f "$PREFLIGHT_SCRIPT" ]]; then
        warn "Preflight script not found: $PREFLIGHT_SCRIPT"
        if confirm "Continue without preflight checks?"; then
            return 0
        else
            exit 1
        fi
    fi
    
    echo "Running preflight checks..."
    echo ""
    
    # Run preflight in quick mode
    if bash "$PREFLIGHT_SCRIPT" --quick; then
        success "Preflight checks passed"
    else
        EXIT_CODE=$?
        if [[ $EXIT_CODE -eq 0 ]]; then
            # Passed with warnings
            if confirm "Preflight passed with warnings. Continue deployment?"; then
                return 0
            else
                exit 1
            fi
        else
            error "Preflight checks failed"
            echo ""
            warn "You can skip preflight with --skip-preflight, but deployment may fail"
            
            if confirm "Continue anyway?"; then
                return 0
            else
                exit 1
            fi
        fi
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Environment Setup
# ─────────────────────────────────────────────────────────────────────────────

setup_environment() {
    print_step "4" "Environment Setup"
    
    cd "$PROJECT_ROOT"
    
    # Check for existing environment
    CURRENT_ENV=$(azd env list 2>/dev/null | grep -E '^\*' | awk '{print $2}' || echo "")
    
    if [[ -n "$ENV_NAME" ]]; then
        # Use provided environment name
        info "Using environment: $ENV_NAME"
        
        if azd env list 2>/dev/null | grep -q "$ENV_NAME"; then
            info "Environment exists, selecting it"
            azd env select "$ENV_NAME"
        else
            info "Creating new environment: $ENV_NAME"
            azd env new "$ENV_NAME"
        fi
    elif [[ -n "$CURRENT_ENV" ]]; then
        # Use existing environment
        success "Using existing environment: $CURRENT_ENV"
        
        if ! confirm "Continue with environment '$CURRENT_ENV'?"; then
            echo -n "Enter new environment name: "
            read -r new_env
            azd env new "$new_env"
            ENV_NAME="$new_env"
        else
            ENV_NAME="$CURRENT_ENV"
        fi
    else
        # No environment, create one
        if [[ "$AUTO_YES" == "true" ]]; then
            ENV_NAME="dev-$(date +%Y%m%d)"
        else
            echo -n "Enter environment name [dev]: "
            read -r env_input
            ENV_NAME="${env_input:-dev}"
        fi
        
        info "Creating environment: $ENV_NAME"
        azd env new "$ENV_NAME"
    fi
    
    # Set location
    info "Setting Azure location: $LOCATION"
    azd env set AZURE_LOCATION "$LOCATION"
    
    # Set local state for Terraform
    azd env set LOCAL_STATE true
    
    success "Environment configured: $ENV_NAME"
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Deployment
# ─────────────────────────────────────────────────────────────────────────────

run_deployment() {
    print_step "5" "Deployment"
    
    cd "$PROJECT_ROOT"
    
    if [[ "$DESTROY_MODE" == "true" ]]; then
        # Teardown mode
        echo -e "${RED}${BOLD}WARNING: This will destroy all Azure resources!${NC}"
        echo ""
        
        if confirm "Are you sure you want to destroy the deployment?"; then
            info "Starting teardown..."
            if azd down --force --purge; then
                success "Teardown complete"
            else
                error "Teardown failed"
                exit 1
            fi
        else
            echo "Teardown cancelled"
            exit 0
        fi
        return 0
    fi
    
    # Normal deployment
    echo "Deployment Summary:"
    echo "  Environment: $ENV_NAME"
    echo "  Location:    $LOCATION"
    echo "  Mode:        $(if [[ "$PROVISION_ONLY" == "true" ]]; then echo "Provision Only"; elif [[ "$DEPLOY_ONLY" == "true" ]]; then echo "Deploy Only"; else echo "Full (Provision + Deploy)"; fi)"
    echo ""
    
    if ! confirm "Start deployment?"; then
        echo "Deployment cancelled"
        exit 0
    fi
    
    echo ""
    START_TIME=$(date +%s)
    
    if [[ "$DEPLOY_ONLY" == "true" ]]; then
        info "Deploying applications..."
        if azd deploy; then
            success "Application deployment complete"
        else
            error "Application deployment failed"
            exit 1
        fi
    elif [[ "$PROVISION_ONLY" == "true" ]]; then
        info "Provisioning infrastructure..."
        if azd provision; then
            success "Infrastructure provisioning complete"
        else
            error "Infrastructure provisioning failed"
            exit 1
        fi
    else
        info "Running full deployment (provision + deploy)..."
        if azd up; then
            success "Full deployment complete"
        else
            error "Deployment failed"
            exit 1
        fi
    fi
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))
    
    echo ""
    success "Deployment completed in ${MINUTES}m ${SECONDS}s"
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Post-Deployment
# ─────────────────────────────────────────────────────────────────────────────

post_deployment() {
    if [[ "$DESTROY_MODE" == "true" ]]; then
        return 0
    fi
    
    print_step "6" "Post-Deployment"
    
    cd "$PROJECT_ROOT"
    
    # Get deployment outputs
    echo "Retrieving deployment information..."
    echo ""
    
    # Try to get endpoints from azd
    FRONTEND_URL=$(azd env get-values 2>/dev/null | grep "FRONTEND_URL" | cut -d'=' -f2 | tr -d '"' || echo "")
    BACKEND_URL=$(azd env get-values 2>/dev/null | grep "BACKEND_URL" | cut -d'=' -f2 | tr -d '"' || echo "")
    
    if [[ -n "$FRONTEND_URL" || -n "$BACKEND_URL" ]]; then
        echo -e "${BOLD}${GREEN}Deployment Endpoints:${NC}"
        echo ""
        if [[ -n "$FRONTEND_URL" ]]; then
            echo -e "  Frontend:  ${CYAN}$FRONTEND_URL${NC}"
        fi
        if [[ -n "$BACKEND_URL" ]]; then
            echo -e "  Backend:   ${CYAN}$BACKEND_URL${NC}"
        fi
    else
        info "Run 'azd env get-values' to see all deployment outputs"
    fi
    
    echo ""
    echo -e "${BOLD}Next Steps:${NC}"
    echo "  1. Configure phone number in ACS portal"
    echo "  2. Test the voice agent by calling the configured number"
    echo "  3. View logs: az containerapp logs show --name <app> --resource-group <rg>"
    echo "  4. Teardown when done: ./devops/scripts/deploy.sh --destroy"
    echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

main() {
    print_banner
    
    # Check for required tools
    if ! command -v az &> /dev/null; then
        error "Azure CLI (az) not found. Install from: https://docs.microsoft.com/cli/azure/install-azure-cli"
        exit 1
    fi
    
    if ! command -v azd &> /dev/null; then
        error "Azure Developer CLI (azd) not found. Install: curl -fsSL https://aka.ms/install-azd.sh | bash"
        exit 1
    fi
    
    # Run deployment steps
    azure_login
    select_subscription
    run_preflight
    setup_environment
    run_deployment
    post_deployment
    
    echo ""
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}  Deployment Complete!${NC}"
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

main "$@"
