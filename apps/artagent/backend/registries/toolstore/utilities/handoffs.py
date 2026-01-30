"""
Utilities Handoff Tools
=======================

Agent handoff tools for utilities multi-agent orchestration.
"""

from __future__ import annotations

from typing import Any

from apps.artagent.backend.registries.toolstore.registry import register_tool
from utils.ml_logging import get_logger

logger = get_logger("tools.utilities.handoffs")

SILENT_HANDOFF_NOTE = " IMPORTANT: Call this tool immediately without saying anything first. The target agent will greet the customer."


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

handoff_billing_agent_schema: dict[str, Any] = {
    "name": "handoff_billing_agent",
    "description": (
        "Transfer to Billing Specialist for payment plans, bill disputes, credits, and complex billing questions."
        + SILENT_HANDOFF_NOTE
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {"type": "string", "description": "Customer account number"},
            "reason": {"type": "string", "description": "Why customer needs billing help"},
            "current_balance": {"type": "number", "description": "Current account balance if known"},
        },
        "required": [],
    },
}


handoff_outage_agent_schema: dict[str, Any] = {
    "name": "handoff_outage_agent",
    "description": (
        "Transfer to Outage Specialist for power outages, gas leaks, or service interruptions. URGENT priority."
        + SILENT_HANDOFF_NOTE
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {"type": "string"},
            "service_address": {"type": "string"},
            "outage_type": {"type": "string", "enum": ["electric", "gas"]},
            "is_emergency": {"type": "boolean", "description": "True for downed wires, gas smell"},
        },
        "required": [],
    },
}


handoff_service_agent_schema: dict[str, Any] = {
    "name": "handoff_service_agent",
    "description": (
        "Transfer to Service Specialist for new service, transfers, disconnections, and service changes."
        + SILENT_HANDOFF_NOTE
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {"type": "string"},
            "service_type": {"type": "string", "enum": ["new_service", "transfer", "stop_service", "upgrade"]},
            "move_date": {"type": "string", "description": "Move date if applicable"},
            "new_address": {"type": "string", "description": "New address if moving"},
        },
        "required": [],
    },
}


handoff_usage_agent_schema: dict[str, Any] = {
    "name": "handoff_usage_agent",
    "description": (
        "Transfer to Usage Analyst for usage questions, efficiency tips, meter issues, and rate optimization."
        + SILENT_HANDOFF_NOTE
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "account_number": {"type": "string"},
            "concern": {"type": "string", "description": "What usage concern the customer has"},
        },
        "required": [],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTORS
# ═══════════════════════════════════════════════════════════════════════════════

async def handoff_billing_agent_executor(**kwargs: Any) -> dict[str, Any]:
    """Execute handoff to Billing Agent."""
    return {
        "handoff": True,
        "target_agent": "BillingAgent",
        "handoff_type": "announced",
        "handoff_context": {
            "account_number": kwargs.get("account_number"),
            "reason": kwargs.get("reason"),
            "current_balance": kwargs.get("current_balance"),
        },
    }


async def handoff_outage_agent_executor(**kwargs: Any) -> dict[str, Any]:
    """Execute handoff to Outage Agent - discrete for urgency."""
    return {
        "handoff": True,
        "target_agent": "OutageAgent",
        "handoff_type": "discrete",  # No greeting delay for outages
        "handoff_context": {
            "account_number": kwargs.get("account_number"),
            "service_address": kwargs.get("service_address"),
            "outage_type": kwargs.get("outage_type", "electric"),
            "is_emergency": kwargs.get("is_emergency", False),
        },
    }


async def handoff_service_agent_executor(**kwargs: Any) -> dict[str, Any]:
    """Execute handoff to Service Agent."""
    return {
        "handoff": True,
        "target_agent": "ServiceAgent",
        "handoff_type": "announced",
        "handoff_context": {
            "account_number": kwargs.get("account_number"),
            "service_type": kwargs.get("service_type"),
            "move_date": kwargs.get("move_date"),
            "new_address": kwargs.get("new_address"),
        },
    }


async def handoff_usage_agent_executor(**kwargs: Any) -> dict[str, Any]:
    """Execute handoff to Usage Agent."""
    return {
        "handoff": True,
        "target_agent": "UsageAgent",
        "handoff_type": "announced",
        "handoff_context": {
            "account_number": kwargs.get("account_number"),
            "concern": kwargs.get("concern"),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════

def register_utilities_handoff_tools() -> None:
    """Register utilities handoff tools."""
    
    register_tool(
        "handoff_billing_agent",
        handoff_billing_agent_schema,
        handoff_billing_agent_executor,
        is_handoff=True,
        tags={"utilities", "handoff"},
    )
    
    register_tool(
        "handoff_outage_agent",
        handoff_outage_agent_schema,
        handoff_outage_agent_executor,
        is_handoff=True,
        tags={"utilities", "handoff", "urgent"},
    )
    
    register_tool(
        "handoff_service_agent",
        handoff_service_agent_schema,
        handoff_service_agent_executor,
        is_handoff=True,
        tags={"utilities", "handoff"},
    )
    
    register_tool(
        "handoff_usage_agent",
        handoff_usage_agent_schema,
        handoff_usage_agent_executor,
        is_handoff=True,
        tags={"utilities", "handoff"},
    )
    
    logger.info("Utilities handoff tools registered")


# Auto-register on import
register_utilities_handoff_tools()
