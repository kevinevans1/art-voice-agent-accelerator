"""
Channel Handoff Tool
====================

Tool for offering and executing channel switches during voice calls.
Used when call volume is high or customer requests alternative channel.

This tool:
    1. Offers WhatsApp or Web chat as alternatives
    2. Captures conversation context for handoff
    3. Initiates handoff notification to target channel
    4. Ends the voice call gracefully

Usage in agent YAML:
    tools:
      - offer_channel_switch
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from apps.artagent.backend.registries.toolstore.registry import register_tool
from utils.ml_logging import get_logger

logger = get_logger("tools.channel_handoff")

# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

offer_channel_switch_schema: dict[str, Any] = {
    "name": "offer_channel_switch",
    "description": (
        "Offer the customer an alternative channel (WhatsApp or Web Chat) to continue the conversation. "
        "Use when: (1) call wait times are high, (2) customer needs to share documents/images, "
        "(3) customer requests text-based communication, or (4) issue requires async follow-up. "
        "The conversation context will be preserved - customer won't need to repeat themselves."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Why channel switch is being offered",
                "enum": ["high_volume", "document_needed", "customer_request", "async_followup", "complex_issue"],
            },
            "preferred_channel": {
                "type": "string",
                "description": "Suggested channel for the customer",
                "enum": ["whatsapp", "webchat", "either"],
            },
            "conversation_summary": {
                "type": "string",
                "description": "Brief summary of the conversation so far (what was discussed, what customer needs)",
            },
            "collected_info": {
                "type": "object",
                "description": "Key information already collected from customer",
                "properties": {
                    "customer_name": {"type": "string"},
                    "account_verified": {"type": "boolean"},
                    "issue_type": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                },
            },
        },
        "required": ["reason", "preferred_channel", "conversation_summary"],
    },
}

execute_channel_handoff_schema: dict[str, Any] = {
    "name": "execute_channel_handoff",
    "description": (
        "Execute the channel handoff after customer confirms they want to switch. "
        "This will send a message to their chosen channel with conversation context "
        "and gracefully end the voice call. ONLY call this after customer confirms."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "target_channel": {
                "type": "string",
                "description": "Channel the customer chose",
                "enum": ["whatsapp", "webchat"],
            },
            "customer_phone": {
                "type": "string",
                "description": "Customer's phone number (for WhatsApp)",
            },
            "handoff_message": {
                "type": "string",
                "description": "Message to send on the new channel summarizing context",
            },
            "end_call_message": {
                "type": "string",
                "description": "Final message to say before ending the call",
            },
        },
        "required": ["target_channel", "handoff_message"],
    },
}

check_queue_status_schema: dict[str, Any] = {
    "name": "check_queue_status",
    "description": (
        "Check current call queue status to determine if channel switch should be offered. "
        "Returns queue depth and estimated wait time. Use this proactively during high-volume periods."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTORS
# ═══════════════════════════════════════════════════════════════════════════════


async def offer_channel_switch_executor(
    reason: str,
    preferred_channel: str,
    conversation_summary: str,
    collected_info: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Offer channel switch to customer.

    This prepares the offer but doesn't execute the switch.
    Returns a response for the agent to present to the customer.
    """
    logger.info(
        "Channel switch offered: reason=%s, channel=%s",
        reason,
        preferred_channel,
    )

    # Build offer message based on reason
    if reason == "high_volume":
        offer_text = (
            "I notice we have high call volumes right now. "
            "Would you like to continue our conversation on {channel}? "
            "I'll transfer all our conversation details so you won't have to repeat anything."
        )
    elif reason == "document_needed":
        offer_text = (
            "To help you further, I'll need you to share some documents. "
            "Would you like to continue on {channel} where you can easily send images or files?"
        )
    elif reason == "customer_request":
        offer_text = (
            "I can definitely help you continue via {channel}. "
            "All your information will be transferred - you won't need to repeat anything."
        )
    elif reason == "async_followup":
        offer_text = (
            "This might take some time to resolve. Would you prefer to continue on {channel}? "
            "I can send you updates there and you can respond when convenient."
        )
    else:
        offer_text = (
            "Would you like to continue on {channel}? "
            "Your conversation will be transferred seamlessly."
        )

    # Format channel name for display
    channel_display = "WhatsApp" if preferred_channel == "whatsapp" else "our web chat"
    if preferred_channel == "either":
        channel_display = "WhatsApp or our web chat"

    return {
        "status": "offer_pending",
        "offer_text": offer_text.format(channel=channel_display),
        "reason": reason,
        "preferred_channel": preferred_channel,
        "conversation_summary": conversation_summary,
        "collected_info": collected_info or {},
        "available_channels": ["whatsapp", "webchat"],
        "instructions": "Present this offer to the customer and wait for their response. If they accept, use execute_channel_handoff.",
    }


async def execute_channel_handoff_executor(
    target_channel: str,
    handoff_message: str,
    customer_phone: str | None = None,
    end_call_message: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Execute the channel handoff.

    This actually sends the message to the target channel and
    signals the orchestrator to end the voice call.
    """
    logger.info(
        "Executing channel handoff: target=%s, phone=%s",
        target_channel,
        customer_phone,
    )

    # Get session context from kwargs (passed by orchestrator)
    session_id = kwargs.get("session_id", "unknown")
    customer_id = customer_phone or kwargs.get("customer_id", "unknown")

    # Prepare handoff context
    handoff_context = {
        "source_channel": "voice",
        "source_session_id": session_id,
        "handoff_time": datetime.now(UTC).isoformat(),
        "handoff_message": handoff_message,
        "customer_id": customer_id,
    }

    # In a real implementation, this would:
    # 1. Save context to CustomerContextManager
    # 2. Send notification to target channel adapter
    # 3. Signal the voice orchestrator to end the call

    # For now, return the handoff payload for the orchestrator to handle
    return {
        "handoff": True,
        "handoff_type": "channel_switch",
        "target_channel": target_channel,
        "customer_id": customer_id,
        "handoff_context": handoff_context,
        "end_call": True,
        "end_call_message": end_call_message or "I've sent you a message on {channel}. You can continue there at your convenience. Thank you for calling!".format(
            channel="WhatsApp" if target_channel == "whatsapp" else "web chat"
        ),
        "message": f"Channel handoff to {target_channel} initiated",
    }


async def check_queue_status_executor(**kwargs: Any) -> dict[str, Any]:
    """
    Check current call queue status.

    In production, this would query ACS or a queue management system.
    """
    # Simulated queue metrics - in production, query actual queue
    # These thresholds can be configured via App Configuration
    wait_time_threshold = int(os.getenv("HANDOFF_WAIT_TIME_THRESHOLD_SECONDS", "120"))
    queue_depth_threshold = int(os.getenv("HANDOFF_QUEUE_DEPTH_THRESHOLD", "50"))

    # TODO: Integrate with actual queue metrics from ACS or custom tracking
    # For now, return configurable test values
    simulated_wait_time = int(os.getenv("SIMULATED_QUEUE_WAIT_TIME", "30"))
    simulated_queue_depth = int(os.getenv("SIMULATED_QUEUE_DEPTH", "10"))

    is_high_volume = (
        simulated_wait_time > wait_time_threshold or 
        simulated_queue_depth > queue_depth_threshold
    )

    return {
        "queue_depth": simulated_queue_depth,
        "estimated_wait_seconds": simulated_wait_time,
        "is_high_volume": is_high_volume,
        "should_offer_alternative": is_high_volume,
        "wait_time_threshold": wait_time_threshold,
        "queue_depth_threshold": queue_depth_threshold,
        "recommendation": "offer_channel_switch" if is_high_volume else "continue_call",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════


def register_channel_handoff_tools() -> None:
    """Register all channel handoff tools."""
    register_tool(
        name="offer_channel_switch",
        schema=offer_channel_switch_schema,
        executor=offer_channel_switch_executor,
        is_handoff=False,  # Not a handoff until executed
        tags={"omnichannel", "handoff"},
    )

    register_tool(
        name="execute_channel_handoff",
        schema=execute_channel_handoff_schema,
        executor=execute_channel_handoff_executor,
        is_handoff=True,  # This triggers actual handoff
        tags={"omnichannel", "handoff"},
    )

    register_tool(
        name="check_queue_status",
        schema=check_queue_status_schema,
        executor=check_queue_status_executor,
        is_handoff=False,
        tags={"omnichannel", "queue"},
    )

    logger.info("Channel handoff tools registered")


# Auto-register on import
register_channel_handoff_tools()
