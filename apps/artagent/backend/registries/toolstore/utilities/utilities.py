"""
Utilities Tools
===============

Tools for domestic utilities provider (electric, gas, water).
Handles billing, outages, service, and usage operations.

Usage in agent YAML:
    tools:
      - get_current_bill
      - check_outage_status
      - report_outage
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import Any

from apps.artagent.backend.registries.toolstore.registry import register_tool
from utils.ml_logging import get_logger

logger = get_logger("tools.utilities")


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

get_current_bill_schema: dict[str, Any] = {
    "name": "get_current_bill",
    "description": "Get the customer's current bill amount, due date, and basic details.",
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {
                "type": "string",
                "description": "Customer account number",
            },
        },
        "required": [],
    },
}


async def get_current_bill_executor(**kwargs: Any) -> dict[str, Any]:
    """Get current bill information."""
    account = kwargs.get("account_number", "demo_account")
    
    # Simulated bill data
    current_balance = round(random.uniform(75, 250), 2)
    due_date = (datetime.now(UTC) + timedelta(days=random.randint(5, 20))).strftime("%B %d, %Y")
    
    return {
        "success": True,
        "account_number": account,
        "current_balance": current_balance,
        "due_date": due_date,
        "last_payment": {
            "amount": round(random.uniform(100, 200), 2),
            "date": (datetime.now(UTC) - timedelta(days=30)).strftime("%B %d, %Y"),
        },
        "usage_kwh": random.randint(400, 1200),
        "billing_period": "January 1-31, 2026",
        "account_status": "Current",
    }


get_bill_breakdown_schema: dict[str, Any] = {
    "name": "get_bill_breakdown",
    "description": "Get itemized breakdown of charges on the bill.",
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {"type": "string"},
            "bill_date": {"type": "string", "description": "Optional: specific bill date"},
        },
        "required": [],
    },
}


async def get_bill_breakdown_executor(**kwargs: Any) -> dict[str, Any]:
    """Get detailed bill breakdown."""
    usage_kwh = random.randint(400, 1200)
    rate = 0.12
    
    return {
        "success": True,
        "charges": [
            {"description": "Electric Usage", "amount": round(usage_kwh * rate, 2), "details": f"{usage_kwh} kWh @ $0.12/kWh"},
            {"description": "Basic Service Charge", "amount": 12.50, "details": "Monthly fixed charge"},
            {"description": "Distribution Charge", "amount": round(usage_kwh * 0.03, 2), "details": f"$0.03/kWh"},
            {"description": "Taxes & Fees", "amount": round(usage_kwh * rate * 0.08, 2), "details": "8% of usage charges"},
        ],
        "subtotal": round(usage_kwh * rate + 12.50 + usage_kwh * 0.03, 2),
        "taxes": round(usage_kwh * rate * 0.08, 2),
        "total": round(usage_kwh * rate * 1.08 + 12.50 + usage_kwh * 0.03, 2),
    }


process_payment_schema: dict[str, Any] = {
    "name": "process_payment",
    "description": "Process a payment on the customer's account.",
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {"type": "string"},
            "amount": {"type": "number", "description": "Payment amount"},
            "payment_method": {
                "type": "string",
                "enum": ["bank_account", "credit_card", "debit_card"],
            },
        },
        "required": ["amount", "payment_method"],
    },
}


async def process_payment_executor(**kwargs: Any) -> dict[str, Any]:
    """Process a payment."""
    amount = kwargs.get("amount", 0)
    method = kwargs.get("payment_method", "bank_account")
    
    confirmation = f"PAY{random.randint(100000, 999999)}"
    
    return {
        "success": True,
        "confirmation_number": confirmation,
        "amount_paid": amount,
        "payment_method": method,
        "effective_date": datetime.now(UTC).strftime("%B %d, %Y"),
        "message": f"Payment of ${amount:.2f} processed successfully. Confirmation: {confirmation}",
    }


setup_payment_plan_schema: dict[str, Any] = {
    "name": "setup_payment_plan",
    "description": "Set up a payment arrangement for the customer's balance.",
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {"type": "string"},
            "total_amount": {"type": "number"},
            "months": {"type": "integer", "description": "Number of months to spread payments"},
            "down_payment": {"type": "number", "description": "Initial payment amount"},
        },
        "required": ["total_amount", "months"],
    },
}


async def setup_payment_plan_executor(**kwargs: Any) -> dict[str, Any]:
    """Set up payment arrangement."""
    total = kwargs.get("total_amount", 0)
    months = kwargs.get("months", 3)
    down_payment = kwargs.get("down_payment", 0)
    
    remaining = total - down_payment
    monthly = round(remaining / months, 2)
    
    return {
        "success": True,
        "plan_id": f"PLAN{random.randint(10000, 99999)}",
        "total_amount": total,
        "down_payment": down_payment,
        "monthly_payment": monthly,
        "number_of_payments": months,
        "first_payment_due": (datetime.now(UTC) + timedelta(days=30)).strftime("%B %d, %Y"),
        "message": f"Payment plan created: ${monthly:.2f}/month for {months} months.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# OUTAGE TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

check_outage_status_schema: dict[str, Any] = {
    "name": "check_outage_status",
    "description": "Check if there's a known outage affecting the customer's service address.",
    "parameters": {
        "type": "object",
        "properties": {
            "service_address": {"type": "string", "description": "Customer's service address"},
            "account_number": {"type": "string"},
        },
        "required": [],
    },
}


async def check_outage_status_executor(**kwargs: Any) -> dict[str, Any]:
    """Check outage status for an address."""
    address = kwargs.get("service_address", "123 Main St")
    
    # Simulate 30% chance of active outage for demo
    has_outage = random.random() < 0.3
    
    if has_outage:
        eta = datetime.now(UTC) + timedelta(hours=random.randint(1, 6))
        return {
            "success": True,
            "outage_active": True,
            "outage_id": f"OUT{random.randint(100000, 999999)}",
            "cause": random.choice(["Tree contact", "Equipment failure", "Storm damage", "Under investigation"]),
            "affected_customers": random.randint(50, 5000),
            "reported_time": (datetime.now(UTC) - timedelta(hours=random.randint(1, 4))).isoformat(),
            "estimated_restoration": eta.strftime("%B %d, %Y at %I:%M %p"),
            "crew_dispatched": True,
            "crew_status": "On site",
        }
    else:
        return {
            "success": True,
            "outage_active": False,
            "service_address": address,
            "message": "No known outage at this address. Service should be active.",
        }


report_outage_schema: dict[str, Any] = {
    "name": "report_outage",
    "description": "Report a new outage at customer's service address.",
    "parameters": {
        "type": "object",
        "properties": {
            "service_address": {"type": "string"},
            "account_number": {"type": "string"},
            "outage_type": {
                "type": "string",
                "enum": ["electric", "gas", "water"],
            },
            "description": {"type": "string", "description": "Customer's description of the issue"},
        },
        "required": ["outage_type"],
    },
}


async def report_outage_executor(**kwargs: Any) -> dict[str, Any]:
    """Report a new outage."""
    outage_type = kwargs.get("outage_type", "electric")
    
    ticket_id = f"OUT{random.randint(100000, 999999)}"
    
    return {
        "success": True,
        "ticket_id": ticket_id,
        "outage_type": outage_type,
        "status": "Reported",
        "priority": "Normal",
        "estimated_response": "A crew will investigate within 2-4 hours",
        "message": f"Outage reported. Ticket: {ticket_id}. You'll receive updates as crews respond.",
    }


report_downed_wire_schema: dict[str, Any] = {
    "name": "report_downed_wire",
    "description": "EMERGENCY: Report a downed power line. Dispatches crews immediately.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "Location of downed wire"},
            "is_arcing": {"type": "boolean", "description": "Is the wire sparking/arcing?"},
        },
        "required": ["location"],
    },
}


async def report_downed_wire_executor(**kwargs: Any) -> dict[str, Any]:
    """Report downed power line - emergency."""
    location = kwargs.get("location", "Unknown")
    
    return {
        "success": True,
        "emergency_ticket": f"EMRG{random.randint(10000, 99999)}",
        "priority": "CRITICAL",
        "status": "Emergency crew dispatched",
        "estimated_arrival": "15-30 minutes",
        "safety_message": "Stay at least 35 feet away. Assume all wires are live. Keep others away.",
        "911_notified": True,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

transfer_service_schema: dict[str, Any] = {
    "name": "transfer_service",
    "description": "Transfer service from one address to another (customer moving).",
    "parameters": {
        "type": "object",
        "properties": {
            "from_address": {"type": "string"},
            "to_address": {"type": "string"},
            "transfer_date": {"type": "string", "description": "Date to transfer (YYYY-MM-DD)"},
        },
        "required": ["from_address", "to_address", "transfer_date"],
    },
}


async def transfer_service_executor(**kwargs: Any) -> dict[str, Any]:
    """Transfer service between addresses."""
    from_addr = kwargs.get("from_address", "")
    to_addr = kwargs.get("to_address", "")
    date = kwargs.get("transfer_date", "")
    
    return {
        "success": True,
        "transfer_id": f"TRF{random.randint(10000, 99999)}",
        "from_address": from_addr,
        "to_address": to_addr,
        "stop_date": date,
        "start_date": date,
        "final_bill_date": (datetime.now(UTC) + timedelta(days=7)).strftime("%B %d, %Y"),
        "message": f"Service transfer scheduled for {date}. Final bill for old address will be sent within 7 days.",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# USAGE TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

get_usage_history_schema: dict[str, Any] = {
    "name": "get_usage_history",
    "description": "Get usage history for the past months.",
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {"type": "string"},
            "months": {"type": "integer", "description": "Number of months of history"},
        },
        "required": [],
    },
}


async def get_usage_history_executor(**kwargs: Any) -> dict[str, Any]:
    """Get usage history."""
    months = kwargs.get("months", 12)
    
    history = []
    base_usage = random.randint(500, 800)
    for i in range(months):
        month_date = datetime.now(UTC) - timedelta(days=30 * i)
        # Seasonal variation
        seasonal_factor = 1.0 + 0.3 * abs(6 - month_date.month) / 6
        usage = int(base_usage * seasonal_factor * random.uniform(0.9, 1.1))
        history.append({
            "month": month_date.strftime("%B %Y"),
            "usage_kwh": usage,
            "cost": round(usage * 0.12, 2),
        })
    
    return {
        "success": True,
        "history": history,
        "average_monthly_usage": int(sum(h["usage_kwh"] for h in history) / len(history)),
        "average_monthly_cost": round(sum(h["cost"] for h in history) / len(history), 2),
    }


get_efficiency_tips_schema: dict[str, Any] = {
    "name": "get_efficiency_tips",
    "description": "Get personalized energy efficiency tips based on usage patterns.",
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {"type": "string"},
            "focus_area": {
                "type": "string",
                "enum": ["heating", "cooling", "water_heating", "appliances", "general"],
            },
        },
        "required": [],
    },
}


async def get_efficiency_tips_executor(**kwargs: Any) -> dict[str, Any]:
    """Get energy efficiency tips."""
    focus = kwargs.get("focus_area", "general")
    
    tips = {
        "general": [
            "Replace incandescent bulbs with LEDs - saves $75/year",
            "Unplug devices when not in use - phantom load costs $100/year",
            "Use power strips to easily cut power to multiple devices",
        ],
        "cooling": [
            "Set thermostat to 78°F when home - each degree lower adds 3% to cooling costs",
            "Use ceiling fans counterclockwise in summer",
            "Close blinds on south-facing windows during afternoon",
        ],
        "heating": [
            "Set thermostat to 68°F when home, 60°F when sleeping",
            "Seal drafts around windows and doors",
            "Reverse ceiling fans to clockwise in winter",
        ],
        "water_heating": [
            "Lower water heater to 120°F - default 140°F wastes energy",
            "Insulate hot water pipes",
            "Fix dripping faucets - a drip wastes 3,000 gallons/year",
        ],
        "appliances": [
            "Run dishwasher and laundry with full loads only",
            "Clean refrigerator coils annually",
            "Replace appliances older than 10-15 years with ENERGY STAR models",
        ],
    }
    
    return {
        "success": True,
        "focus_area": focus,
        "tips": tips.get(focus, tips["general"]),
        "estimated_annual_savings": f"${random.randint(50, 200)}",
        "rebates_available": True,
        "rebate_link": "https://example.com/rebates",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════

def register_utilities_tools() -> None:
    """Register all utilities tools."""
    
    # Billing
    register_tool("get_current_bill", get_current_bill_schema, get_current_bill_executor, tags={"utilities", "billing"})
    register_tool("get_bill_breakdown", get_bill_breakdown_schema, get_bill_breakdown_executor, tags={"utilities", "billing"})
    register_tool("process_payment", process_payment_schema, process_payment_executor, tags={"utilities", "billing", "payment"})
    register_tool("setup_payment_plan", setup_payment_plan_schema, setup_payment_plan_executor, tags={"utilities", "billing", "payment"})
    
    # Outage
    register_tool("check_outage_status", check_outage_status_schema, check_outage_status_executor, tags={"utilities", "outage"})
    register_tool("report_outage", report_outage_schema, report_outage_executor, tags={"utilities", "outage"})
    register_tool("report_downed_wire", report_downed_wire_schema, report_downed_wire_executor, tags={"utilities", "outage", "emergency"})
    
    # Service
    register_tool("transfer_service", transfer_service_schema, transfer_service_executor, tags={"utilities", "service"})
    
    # Usage
    register_tool("get_usage_history", get_usage_history_schema, get_usage_history_executor, tags={"utilities", "usage"})
    register_tool("get_efficiency_tips", get_efficiency_tips_schema, get_efficiency_tips_executor, tags={"utilities", "usage", "tips"})
    
    logger.info("Utilities tools registered")


# Auto-register on import
register_utilities_tools()
