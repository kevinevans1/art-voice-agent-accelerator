#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Phone Number Configuration Helper
# ═══════════════════════════════════════════════════════════════════════════════
# Helps configure Azure Communication Services phone number after deployment.
#
# Usage:
#   ./devops/scripts/configure-phone-number.sh [phone_number]
#
# Examples:
#   ./devops/scripts/configure-phone-number.sh              # Interactive mode
#   ./devops/scripts/configure-phone-number.sh +14165551234 # Direct set
#
# Prerequisites:
#   - azd environment initialized
#   - Azure infrastructure provisioned (azd provision completed)
#   - Phone number acquired from Azure Communication Services
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

echo ""
echo -e "${BOLD}${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║     Phone Number Configuration Helper                         ║${NC}"
echo -e "${BOLD}${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
if ! command -v azd &> /dev/null; then
    echo -e "${RED}Error: azd not found. Install Azure Developer CLI first.${NC}"
    exit 1
fi

if ! azd env list &> /dev/null; then
    echo -e "${RED}Error: No azd environment found. Run 'azd init' first.${NC}"
    exit 1
fi

# Get current environment
CURRENT_ENV=$(azd env list 2>/dev/null | grep -E '^\*' | awk '{print $2}' || echo "")
if [[ -z "$CURRENT_ENV" ]]; then
    echo -e "${RED}Error: No active azd environment. Run 'azd env select <env>' first.${NC}"
    exit 1
fi

echo -e "Current environment: ${GREEN}$CURRENT_ENV${NC}"
echo ""

# Check current phone number
CURRENT_PHONE=$(azd env get-values 2>/dev/null | grep ACS_SOURCE_PHONE_NUMBER | cut -d'=' -f2 | tr -d '"' || echo "")
if [[ -n "$CURRENT_PHONE" && "$CURRENT_PHONE" != "placeholder" && "$CURRENT_PHONE" != "+1" ]]; then
    echo -e "Current phone number: ${GREEN}$CURRENT_PHONE${NC}"
    echo ""
    read -p "Replace existing phone number? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing configuration."
        exit 0
    fi
fi

# Get phone number
PHONE_NUMBER="${1:-}"
if [[ -z "$PHONE_NUMBER" ]]; then
    echo -e "${CYAN}How to get a phone number:${NC}"
    echo "  1. Go to Azure Portal: https://portal.azure.com"
    echo "  2. Navigate to Azure Communication Services"
    echo "  3. Select 'Phone numbers' → 'Get'"
    echo "  4. Choose country, number type (toll-free or geographic)"
    echo "  5. Select features: Voice (inbound/outbound)"
    echo "  6. Complete purchase"
    echo ""
    echo -e "${YELLOW}Note: Phone numbers require a verified Azure account and may incur charges.${NC}"
    echo ""
    
    read -p "Enter phone number (E.164 format, e.g., +14165551234): " PHONE_NUMBER
fi

# Validate format
if [[ ! "$PHONE_NUMBER" =~ ^\+[0-9]{10,15}$ ]]; then
    echo -e "${RED}Error: Invalid phone number format.${NC}"
    echo "Phone number must be in E.164 format: +[country code][number]"
    echo "Examples: +14165551234, +442071234567, +61412345678"
    exit 1
fi

echo ""
echo -e "Setting phone number: ${GREEN}$PHONE_NUMBER${NC}"

# Set the environment variable
if azd env set ACS_SOURCE_PHONE_NUMBER "$PHONE_NUMBER"; then
    echo -e "${GREEN}✓${NC} Phone number set in azd environment"
else
    echo -e "${RED}✗${NC} Failed to set phone number"
    exit 1
fi

# Check if App Configuration needs updating
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo ""
echo "  To update the deployed application with the new phone number:"
echo ""
echo -e "  ${CYAN}azd provision${NC}"
echo "    This will update App Configuration with the new phone number."
echo ""
echo "  The backend will automatically pick up the new configuration."
echo ""

# Optionally run provision
read -p "Run 'azd provision' now to update Azure? [y/N] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Running azd provision..."
    echo ""
    if azd provision; then
        echo ""
        echo -e "${GREEN}✓${NC} Azure infrastructure updated with new phone number"
        echo ""
        echo -e "${CYAN}Voice telephony is now enabled!${NC}"
        echo "  Inbound/outbound calls will use: $PHONE_NUMBER"
    else
        echo -e "${RED}✗${NC} Provision failed. Check the error above."
        exit 1
    fi
else
    echo ""
    echo "Run 'azd provision' when ready to update Azure."
fi

echo ""
echo -e "${GREEN}Done!${NC}"
