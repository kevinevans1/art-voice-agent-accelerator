"""
Channel Handoff Handler
=======================

Handles the execution of channel handoffs in voice orchestrators.
This integrates with the channel adapters and context manager
to provide seamless transitions between Voice, WhatsApp, and WebChat.

Usage:
    from apps.artagent.backend.voice.shared.channel_handoff import ChannelHandoffHandler

    handler = ChannelHandoffHandler(context_manager, whatsapp_adapter, webchat_adapter)
    result = await handler.execute_handoff(
        target_channel="whatsapp",
        customer_id="+1234567890",
        conversation_summary="Customer inquired about account balance...",
        collected_data={"name": "John", "verified": True},
    )
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from apps.artagent.backend.channels.base import ChannelType
from apps.artagent.backend.channels.context import CustomerContext, CustomerContextManager
from utils.ml_logging import get_logger

if TYPE_CHECKING:
    from apps.artagent.backend.channels.whatsapp import WhatsAppAdapter
    from apps.artagent.backend.channels.webchat import WebChatAdapter

logger = get_logger("voice.shared.channel_handoff")


class ChannelHandoffResult:
    """Result of a channel handoff operation."""

    def __init__(
        self,
        success: bool,
        target_channel: str,
        handoff_id: str | None = None,
        message: str = "",
        end_call_message: str = "",
        error: str | None = None,
    ):
        self.success = success
        self.target_channel = target_channel
        self.handoff_id = handoff_id
        self.message = message
        self.end_call_message = end_call_message
        self.error = error


class ChannelHandoffHandler:
    """
    Handles channel handoffs from voice to messaging channels.

    This handler:
    1. Saves the current conversation context
    2. Sends a handoff notification to the target channel
    3. Returns a message for the voice agent to speak before ending the call
    """

    def __init__(
        self,
        context_manager: CustomerContextManager | None = None,
        whatsapp_adapter: Any | None = None,
        webchat_adapter: Any | None = None,
    ):
        """
        Initialize the handler.

        Args:
            context_manager: Manager for customer context persistence
            whatsapp_adapter: Adapter for WhatsApp messaging
            webchat_adapter: Adapter for WebChat messaging
        """
        self._context_manager = context_manager
        self._whatsapp_adapter = whatsapp_adapter
        self._webchat_adapter = webchat_adapter

    async def execute_handoff(
        self,
        target_channel: str,
        customer_id: str,
        conversation_summary: str,
        collected_data: dict[str, Any] | None = None,
        session_id: str | None = None,
        handoff_message: str | None = None,
        end_call_message: str | None = None,
    ) -> ChannelHandoffResult:
        """
        Execute a channel handoff from voice to messaging.

        Args:
            target_channel: "whatsapp" or "webchat"
            customer_id: Customer identifier (phone number for WhatsApp)
            conversation_summary: Summary of the voice conversation
            collected_data: Data collected during the call
            session_id: Current voice session ID
            handoff_message: Custom message to send on target channel
            end_call_message: Custom message to speak before ending call

        Returns:
            ChannelHandoffResult with success status and messages
        """
        import uuid

        handoff_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now(UTC).isoformat()

        logger.info(
            "Executing channel handoff | target=%s customer=%s handoff_id=%s",
            target_channel,
            customer_id,
            handoff_id,
        )

        try:
            # 1. Save context for continuity
            if self._context_manager:
                context = CustomerContext(
                    customer_id=customer_id,
                    phone_number=customer_id if target_channel == "whatsapp" else None,
                    current_channel=ChannelType.VOICE,
                    foundry_thread_id=session_id,
                    conversation_summary=conversation_summary,
                    collected_data=collected_data or {},
                    active=True,
                )
                await self._context_manager.save_context(context)
                logger.debug("Saved customer context for handoff")

            # 2. Build handoff message for target channel
            channel_display = "WhatsApp" if target_channel == "whatsapp" else "web chat"
            default_handoff_message = (
                f"Hi! I'm continuing our conversation from the phone call.\n\n"
                f"Here's what we discussed: {conversation_summary}\n\n"
                f"How can I help you further?"
            )
            
            final_handoff_message = handoff_message or default_handoff_message

            # 3. Send notification to target channel
            notification_sent = False
            if target_channel == "whatsapp" and self._whatsapp_adapter:
                try:
                    await self._whatsapp_adapter.send_message(
                        recipient=customer_id,
                        content=final_handoff_message,
                        metadata={"handoff_id": handoff_id, "source": "voice"},
                    )
                    notification_sent = True
                except Exception as e:
                    logger.warning("Failed to send WhatsApp handoff message: %s", e)
            elif target_channel == "webchat" and self._webchat_adapter:
                try:
                    await self._webchat_adapter.send_message(
                        recipient=customer_id,
                        content=final_handoff_message,
                        metadata={"handoff_id": handoff_id, "source": "voice"},
                    )
                    notification_sent = True
                except Exception as e:
                    logger.warning("Failed to send WebChat handoff message: %s", e)

            # 4. Build end call message
            default_end_message = (
                f"I've sent you a message on {channel_display}. "
                f"You can continue there at your convenience. "
                f"Thank you for calling!"
            )
            final_end_message = end_call_message or default_end_message

            logger.info(
                "Channel handoff complete | handoff_id=%s notification_sent=%s",
                handoff_id,
                notification_sent,
            )

            return ChannelHandoffResult(
                success=True,
                target_channel=target_channel,
                handoff_id=handoff_id,
                message=f"Handoff to {channel_display} initiated",
                end_call_message=final_end_message,
            )

        except Exception as e:
            logger.error("Channel handoff failed: %s", e, exc_info=True)
            return ChannelHandoffResult(
                success=False,
                target_channel=target_channel,
                error=str(e),
                message="Failed to complete channel handoff",
                end_call_message="I'm sorry, I couldn't complete the transfer. Please try again.",
            )

    def is_channel_handoff_tool(self, tool_name: str) -> bool:
        """Check if a tool triggers a channel handoff."""
        return tool_name in ("execute_channel_handoff",)

    def parse_channel_handoff_result(
        self, tool_result: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """
        Parse a tool result to check if it's a channel handoff.

        Returns:
            Tuple of (is_channel_handoff, target_channel)
        """
        if not isinstance(tool_result, dict):
            return False, None

        # Check for channel handoff markers
        if tool_result.get("handoff_type") == "channel_switch":
            return True, tool_result.get("target_channel")

        if tool_result.get("handoff") and tool_result.get("target_channel"):
            return True, tool_result.get("target_channel")

        return False, None
