#!/bin/bash
# ============================================================================
# Omnichannel WebChat Demo - Local Testing Script
# ============================================================================
# This script helps test the webchat demo locally before deploying to Azure.
#
# Prerequisites:
#   - Python 3.11+
#   - Node.js 18+
#   - Redis running locally (or Azure Redis connection)
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╭─────────────────────────────────────────────────────╮${NC}"
echo -e "${BLUE}│    Omnichannel WebChat Demo - Local Testing         │${NC}"
echo -e "${BLUE}╰─────────────────────────────────────────────────────╯${NC}"
echo ""

# ============================================================================
# Step 1: Check Prerequisites
# ============================================================================
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "  ✓ $1 found"
        return 0
    else
        echo -e "  ✗ $1 not found"
        return 1
    fi
}

check_command python3 || exit 1
check_command node || exit 1
check_command npm || exit 1

echo ""

# ============================================================================
# Step 2: Start Backend (if not running)
# ============================================================================
echo -e "${YELLOW}Step 2: Checking backend status...${NC}"

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
if curl -s "$BACKEND_URL/health" > /dev/null 2>&1; then
    echo -e "  ✓ Backend is running at $BACKEND_URL"
else
    echo -e "  ! Backend not running at $BACKEND_URL"
    echo ""
    echo -e "  ${YELLOW}To start the backend:${NC}"
    echo "    cd $PROJECT_ROOT"
    echo "    make run_server"
    echo ""
    echo "  Or with environment variables:"
    echo "    REDIS_HOST=localhost REDIS_PORT=6379 make run_server"
    echo ""
    read -p "  Start backend in background? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "  Starting backend..."
        cd "$PROJECT_ROOT"
        make run_server &
        BACKEND_PID=$!
        echo "  Backend starting (PID: $BACKEND_PID)..."
        sleep 5
    fi
fi

echo ""

# ============================================================================
# Step 3: Seed Test Context (simulate voice call data)
# ============================================================================
echo -e "${YELLOW}Step 3: Setting up test customer context...${NC}"

TEST_CUSTOMER_ID="+15551234567"

# Create Python script to seed context
cat > /tmp/seed_context.py << 'PYTHON_SCRIPT'
import asyncio
import sys
sys.path.insert(0, '.')

from apps.artagent.backend.channels.context import CustomerContext, CustomerContextManager

async def seed_test_context():
    """Seed test customer context as if they called via voice."""
    
    # For local testing, use in-memory context
    context = CustomerContext(
        customer_id="+15551234567",
        phone_number="+15551234567",
    )
    
    # Add a completed voice session
    context.add_session("voice", "voice-session-001")
    
    # Set conversation summary (from voice call)
    context.conversation_summary = (
        "Customer called about a power outage at 123 Oak Street. "
        "Reported the outage started around 2pm. Agent verified account "
        "and dispatched a crew. ETA provided as within 2 hours."
    )
    
    # Add collected data
    context.update_collected_data({
        "service_address": "123 Oak Street, Springfield",
        "account_number": "ACCT-12345678",
        "account_verified": True,
        "outage_reported": True,
        "outage_ticket": "OUT-2024-001234",
        "outage_eta": "within 2 hours",
        "crew_dispatched": True,
    })
    
    # End voice session
    context.end_session(
        session_id="voice-session-001",
        status="transferred",
        summary=context.conversation_summary,
    )
    
    print(f"✓ Created test context for customer: {context.customer_id}")
    print(f"  Summary: {context.conversation_summary[:80]}...")
    print(f"  Collected Data: {list(context.collected_data.keys())}")
    
    return context

if __name__ == "__main__":
    asyncio.run(seed_test_context())
PYTHON_SCRIPT

cd "$PROJECT_ROOT"
python3 /tmp/seed_context.py 2>/dev/null || echo "  Note: Context will be created when webchat connects"

echo ""

# ============================================================================
# Step 4: Start WebChat Demo
# ============================================================================
echo -e "${YELLOW}Step 4: Starting WebChat Demo...${NC}"

WEBCHAT_DIR="$PROJECT_ROOT/apps/webchat-demo"

cd "$WEBCHAT_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "  Installing dependencies..."
    npm install
fi

# Start the development server
echo -e "  Starting WebChat demo at ${GREEN}http://localhost:3001${NC}"
echo ""
echo -e "${BLUE}╭─────────────────────────────────────────────────────╮${NC}"
echo -e "${BLUE}│    Demo Instructions                                │${NC}"
echo -e "${BLUE}├─────────────────────────────────────────────────────┤${NC}"
echo -e "${BLUE}│  1. Open ${GREEN}http://localhost:3001${BLUE}                    │${NC}"
echo -e "${BLUE}│  2. Enter Customer ID: ${GREEN}+15551234567${BLUE}               │${NC}"
echo -e "${BLUE}│  3. Click 'Start Chat'                              │${NC}"
echo -e "${BLUE}│  4. You should see context from 'voice call'        │${NC}"
echo -e "${BLUE}│  5. Try messages like:                              │${NC}"
echo -e "${BLUE}│     - 'What's the status of my outage?'             │${NC}"
echo -e "${BLUE}│     - 'When will the crew arrive?'                  │${NC}"
echo -e "${BLUE}│     - 'I called earlier about power'                │${NC}"
echo -e "${BLUE}╰─────────────────────────────────────────────────────╯${NC}"
echo ""

# Set backend URL for vite dev server
export VITE_BACKEND_URL="$BACKEND_URL"
npm run dev -- --port 3001 --host

