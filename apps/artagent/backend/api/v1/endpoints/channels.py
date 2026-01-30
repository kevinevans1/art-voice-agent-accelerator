"""
Channel API Endpoints
=====================

REST and WebSocket endpoints for omnichannel communication.

Endpoints:
    - POST /api/v1/channels/whatsapp/webhook - WhatsApp incoming messages
    - GET  /api/v1/channels/webchat/ws/{customer_id} - WebChat WebSocket
    - POST /api/v1/channels/handoff - Initiate channel handoff
    - GET  /api/v1/channels/customer/{customer_id}/context - Get customer context
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from apps.artagent.backend.channels.base import ChannelType
from apps.artagent.backend.channels.context import CustomerContext, CustomerContextManager
from apps.artagent.backend.channels.webchat import WebChatAdapter, get_connection_manager
from apps.artagent.backend.channels.whatsapp import WhatsAppAdapter
from utils.ml_logging import get_logger

logger = get_logger("api.channels")

router = APIRouter(tags=["Channels"])

# ═══════════════════════════════════════════════════════════════════════════════
# Adapters (lazily initialized)
# ═══════════════════════════════════════════════════════════════════════════════

_whatsapp_adapter: WhatsAppAdapter | None = None
_webchat_adapter: WebChatAdapter | None = None
_context_manager: CustomerContextManager | None = None


async def get_whatsapp_adapter() -> WhatsAppAdapter:
    """Get or create WhatsApp adapter."""
    global _whatsapp_adapter
    if _whatsapp_adapter is None:
        _whatsapp_adapter = WhatsAppAdapter()
        await _whatsapp_adapter.initialize()
    return _whatsapp_adapter


async def get_webchat_adapter() -> WebChatAdapter:
    """Get or create WebChat adapter."""
    global _webchat_adapter
    if _webchat_adapter is None:
        _webchat_adapter = WebChatAdapter()
        await _webchat_adapter.initialize()
    return _webchat_adapter


def get_context_manager() -> CustomerContextManager:
    """Get or create context manager."""
    global _context_manager
    if _context_manager is None:
        # TODO: Inject actual Cosmos and Redis managers from app state
        _context_manager = CustomerContextManager()
    return _context_manager


# ═══════════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════════════════


class HandoffRequest(BaseModel):
    """Request to initiate a channel handoff."""

    customer_id: str = Field(..., description="Customer identifier (phone number)")
    source_channel: str = Field(..., description="Current channel: voice, whatsapp, webchat")
    target_channel: str = Field(..., description="Target channel: whatsapp, webchat")
    conversation_summary: str = Field(..., description="Summary of conversation so far")
    collected_data: dict[str, Any] = Field(default_factory=dict, description="Data collected from customer")
    session_id: str | None = Field(None, description="Current session ID")


class HandoffResponse(BaseModel):
    """Response from handoff initiation."""

    success: bool
    handoff_id: str
    target_channel: str
    message: str
    handoff_link: str | None = None


class CustomerContextResponse(BaseModel):
    """Customer context response."""

    customer_id: str
    phone_number: str | None
    name: str | None
    foundry_thread_id: str | None
    session_count: int
    conversation_summary: str | None
    collected_data: dict[str, Any]
    last_channel: str | None


class WebChatMessage(BaseModel):
    """WebChat message format."""

    type: str = "message"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# WhatsApp Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request) -> dict[str, Any]:
    """
    Handle incoming WhatsApp messages from ACS Event Grid.

    This endpoint receives webhook notifications from Azure Communication Services
    when a WhatsApp message is received.
    """
    try:
        # Parse incoming webhook payload
        body = await request.json()
        logger.info("WhatsApp webhook received: %s", json.dumps(body)[:200])

        # Handle Event Grid validation
        if isinstance(body, list) and len(body) > 0:
            event = body[0]
            # Event Grid subscription validation
            if event.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
                validation_code = event.get("data", {}).get("validationCode")
                logger.info("Event Grid validation request")
                return {"validationResponse": validation_code}

            # Process actual message
            event_type = event.get("eventType", "")
            if "ChatMessageReceivedInThread" in event_type or "AdvancedMessage" in event_type:
                data = event.get("data", {})
                await process_whatsapp_message(data)

        return {"status": "ok"}

    except Exception as e:
        logger.error("WhatsApp webhook error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


async def process_whatsapp_message(data: dict[str, Any]) -> None:
    """Process an incoming WhatsApp message."""
    adapter = await get_whatsapp_adapter()
    context_mgr = get_context_manager()

    # Parse the message
    message = await adapter.handle_incoming(data)

    # Get or create customer context
    context = await context_mgr.get_or_create(
        customer_id=message.customer_id,
        phone_number=message.customer_id,
    )

    # Add session if not exists
    active_session = context.get_active_session("whatsapp")
    if not active_session:
        context.add_session("whatsapp", message.session_id)
        await context_mgr.save(context)

    # TODO: Route message to appropriate agent via Foundry
    # For now, just log it
    logger.info(
        "WhatsApp message from %s: %s",
        message.customer_id,
        message.content[:100],
    )

    # Echo response for testing
    await adapter.send_message(
        customer_id=message.customer_id,
        message=f"Thanks for your message! I received: {message.content[:50]}...",
        session_id=message.session_id,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# WebChat Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.websocket("/webchat/ws/{customer_id}")
async def webchat_websocket(websocket: WebSocket, customer_id: str):
    """
    WebSocket endpoint for web chat.

    Protocol:
        - Connect to /api/v1/channels/webchat/ws/{customer_id}
        - Send: {"type": "message", "content": "Hello"}
        - Receive: {"type": "message", "content": "Response", "agent": "Concierge"}
    """
    connection_manager = get_connection_manager()
    session_id = f"web_{customer_id}_{uuid.uuid4().hex[:8]}"

    try:
        # Accept connection
        await connection_manager.connect(websocket, customer_id, session_id)

        # Get customer context
        context_mgr = get_context_manager()
        context = await context_mgr.get_or_create(customer_id)

        # Check if this is a handoff (context exists with conversation)
        if context.conversation_summary:
            # Send handoff context
            await websocket.send_json({
                "type": "handoff",
                "source_channel": context.sessions[-1].channel if context.sessions else "unknown",
                "context_summary": context.conversation_summary,
                "message": "Welcome! I have your conversation history - no need to repeat yourself.",
                "timestamp": datetime.now(UTC).isoformat(),
            })
        else:
            # Send welcome message
            await websocket.send_json({
                "type": "system",
                "content": "Welcome to web chat! How can I help you today?",
                "timestamp": datetime.now(UTC).isoformat(),
            })

        # Add session
        context.add_session("webchat", session_id)
        await context_mgr.save(context)

        # Message loop
        while True:
            try:
                # Receive message
                data = await websocket.receive_json()
                logger.debug("WebChat message from %s: %s", customer_id, data)

                if data.get("type") == "message":
                    content = data.get("content", "")

                    # TODO: Route to Foundry agent for processing
                    # For now, echo with agent simulation
                    response = f"I received your message: '{content[:50]}'. How can I help further?"

                    await websocket.send_json({
                        "type": "message",
                        "content": response,
                        "agent": "Concierge",
                        "timestamp": datetime.now(UTC).isoformat(),
                    })

                elif data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid message format",
                })

    except WebSocketDisconnect:
        logger.info("WebChat disconnected: %s", customer_id)
    except Exception as e:
        logger.error("WebChat error for %s: %s", customer_id, e)
    finally:
        await connection_manager.disconnect(customer_id)

        # End session
        context_mgr = get_context_manager()
        await context_mgr.end_customer_session(
            customer_id=customer_id,
            session_id=session_id,
            status="completed",
        )


@router.get("/webchat/status")
async def webchat_status() -> dict[str, Any]:
    """Get WebChat connection status."""
    manager = get_connection_manager()
    return {
        "connected_clients": manager.connected_count,
        "status": "ok",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Handoff Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/handoff", response_model=HandoffResponse)
async def initiate_handoff(request: HandoffRequest) -> HandoffResponse:
    """
    Initiate a channel handoff.

    This endpoint is called by the voice orchestrator when a customer
    accepts a channel switch offer.
    """
    logger.info(
        "Handoff requested: %s -> %s for customer %s",
        request.source_channel,
        request.target_channel,
        request.customer_id,
    )

    try:
        # Get context manager
        context_mgr = get_context_manager()

        # Update customer context
        context = await context_mgr.get_or_create(
            customer_id=request.customer_id,
            phone_number=request.customer_id,
        )

        # Update with conversation data
        context.conversation_summary = request.conversation_summary
        context.update_collected_data(request.collected_data)

        # End source channel session
        if request.session_id:
            context.end_session(
                session_id=request.session_id,
                status="transferred",
                summary=request.conversation_summary,
            )

        await context_mgr.save(context)

        # Generate handoff ID
        handoff_id = f"hoff_{uuid.uuid4().hex[:12]}"

        # Initiate target channel notification
        if request.target_channel == "whatsapp":
            adapter = await get_whatsapp_adapter()
            success = await adapter.send_handoff_notification(
                customer_id=request.customer_id,
                source_channel=ChannelType(request.source_channel),
                context_summary=request.conversation_summary,
            )
            handoff_link = None

        elif request.target_channel == "webchat":
            # Generate web chat link
            # In production, this would be a proper deep link
            handoff_link = f"/chat?customer_id={request.customer_id}&handoff={handoff_id}"
            success = True

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported target channel: {request.target_channel}",
            )

        return HandoffResponse(
            success=success,
            handoff_id=handoff_id,
            target_channel=request.target_channel,
            message=f"Handoff initiated to {request.target_channel}",
            handoff_link=handoff_link,
        )

    except Exception as e:
        logger.error("Handoff failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# Customer Context Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/customer/{customer_id}/context", response_model=CustomerContextResponse)
async def get_customer_context(customer_id: str) -> CustomerContextResponse:
    """
    Get customer context for a given customer ID.

    Returns conversation history, collected data, and session information.
    """
    context_mgr = get_context_manager()
    context = await context_mgr.get_or_create(customer_id)

    return CustomerContextResponse(
        customer_id=context.customer_id,
        phone_number=context.phone_number,
        name=context.name,
        foundry_thread_id=context.foundry_thread_id,
        session_count=len(context.sessions),
        conversation_summary=context.conversation_summary,
        collected_data=context.collected_data,
        last_channel=context.sessions[-1].channel if context.sessions else None,
    )


@router.post("/customer/{customer_id}/context")
async def update_customer_context(
    customer_id: str,
    data: dict[str, Any],
) -> dict[str, str]:
    """
    Update customer context with additional data.

    Body should contain data to merge into collected_data.
    """
    context_mgr = get_context_manager()
    await context_mgr.update_customer_data(customer_id, data)
    return {"status": "updated"}
