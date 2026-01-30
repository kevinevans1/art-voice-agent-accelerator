"""
WhatsApp Channel Adapter
========================

Adapter for WhatsApp messaging via Azure Communication Services.
Handles incoming webhooks and outgoing messages.

Prerequisites:
    - ACS resource with WhatsApp channel enabled
    - WhatsApp Business Account connected to ACS
    - Webhook endpoint configured in Azure Portal

Environment Variables:
    - ACS_CONNECTION_STRING: ACS connection string
    - ACS_WHATSAPP_CHANNEL_ID: WhatsApp channel registration ID
"""

from __future__ import annotations

import os
from typing import Any

from apps.artagent.backend.channels.base import (
    BaseChannelAdapter,
    ChannelMessage,
    ChannelType,
)
from utils.ml_logging import get_logger

logger = get_logger("channels.whatsapp")


class WhatsAppAdapter(BaseChannelAdapter):
    """
    WhatsApp channel adapter using Azure Communication Services.

    Provides bidirectional messaging with WhatsApp users through
    the ACS Advanced Messaging API.
    """

    channel_type = ChannelType.WHATSAPP

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize WhatsApp adapter.

        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        self.connection_string = config.get("connection_string") if config else None
        self.connection_string = self.connection_string or os.getenv("ACS_CONNECTION_STRING")
        self.channel_id = config.get("channel_id") if config else None
        self.channel_id = self.channel_id or os.getenv("ACS_WHATSAPP_CHANNEL_ID")
        self._client = None

    async def initialize(self) -> None:
        """
        Initialize the ACS Messages client.

        Raises:
            ValueError: If connection string or channel ID not configured
        """
        if not self.connection_string:
            raise ValueError("ACS_CONNECTION_STRING not configured for WhatsApp adapter")

        if not self.channel_id:
            logger.warning("ACS_WHATSAPP_CHANNEL_ID not configured - WhatsApp sending disabled")

        try:
            from azure.communication.messages import NotificationMessagesClient

            self._client = NotificationMessagesClient.from_connection_string(
                self.connection_string
            )
            self._initialized = True
            logger.info("WhatsApp adapter initialized successfully")
        except ImportError:
            logger.error("azure-communication-messages package not installed")
            raise
        except Exception as e:
            logger.error("Failed to initialize WhatsApp adapter: %s", e)
            raise

    async def send_message(
        self,
        customer_id: str,
        message: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send a WhatsApp message to a customer.

        Args:
            customer_id: Customer's WhatsApp phone number (with country code)
            message: Text message to send
            session_id: Optional session ID for tracking
            metadata: Optional metadata (not used for WhatsApp)

        Returns:
            True if message sent successfully
        """
        if not self._initialized or not self._client:
            logger.error("WhatsApp adapter not initialized")
            return False

        if not self.channel_id:
            logger.error("WhatsApp channel ID not configured")
            return False

        try:
            from azure.communication.messages.models import TextNotificationContent

            # Normalize phone number
            phone = customer_id.replace(" ", "").replace("-", "")
            if not phone.startswith("+"):
                phone = f"+{phone}"

            # Create and send message
            content = TextNotificationContent(
                channel_registration_id=self.channel_id,
                to=[phone],
                content=message,
            )

            response = self._client.send(content)
            
            # Check response
            if response and hasattr(response, "receipts"):
                for receipt in response.receipts:
                    if receipt.message_id:
                        logger.info(
                            "WhatsApp message sent: %s -> %s (id: %s)",
                            phone,
                            message[:50],
                            receipt.message_id,
                        )
                        return True

            logger.warning("WhatsApp message may not have been delivered: %s", phone)
            return True  # ACS accepted the message

        except Exception as e:
            logger.error("Failed to send WhatsApp message to %s: %s", customer_id, e)
            return False

    async def handle_incoming(
        self,
        raw_message: dict[str, Any],
    ) -> ChannelMessage:
        """
        Process an incoming WhatsApp message from ACS webhook.

        Expected webhook payload structure (ACS Event Grid):
        {
            "from": "+1234567890",
            "to": "channel_registration_id",
            "receivedTimestamp": "2026-01-29T10:00:00Z",
            "message": {
                "text": "Hello!",
                "messageId": "msg_123"
            }
        }

        Args:
            raw_message: Raw webhook payload

        Returns:
            Normalized ChannelMessage
        """
        from datetime import datetime

        # Extract message details
        sender = raw_message.get("from", "")
        message_content = raw_message.get("message", {})
        text = message_content.get("text", "")
        message_id = message_content.get("messageId", "")
        timestamp_str = raw_message.get("receivedTimestamp")

        # Parse timestamp
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                from datetime import UTC
                timestamp = datetime.now(UTC)
        else:
            from datetime import UTC
            timestamp = datetime.now(UTC)

        # Normalize phone number as customer_id
        customer_id = sender.replace(" ", "").replace("-", "")
        if not customer_id.startswith("+"):
            customer_id = f"+{customer_id}"

        # Generate session ID from phone number (consistent per customer)
        session_id = f"wa_{customer_id.replace('+', '')}"

        logger.info(
            "WhatsApp message received: %s -> %s",
            customer_id,
            text[:50] if text else "(empty)",
        )

        return ChannelMessage(
            channel=ChannelType.WHATSAPP,
            customer_id=customer_id,
            session_id=session_id,
            content=text,
            timestamp=timestamp,
            metadata={
                "message_id": message_id,
                "raw_payload": raw_message,
            },
            is_from_customer=True,
        )

    async def send_template_message(
        self,
        customer_id: str,
        template_name: str,
        template_values: list[str] | None = None,
        language: str = "en_US",
    ) -> bool:
        """
        Send a WhatsApp template message (for initiating conversations).

        WhatsApp requires template messages for business-initiated conversations.

        Args:
            customer_id: Customer's phone number
            template_name: Name of the approved template
            template_values: Values to substitute in template
            language: Template language code

        Returns:
            True if sent successfully
        """
        if not self._initialized or not self._client:
            logger.error("WhatsApp adapter not initialized")
            return False

        if not self.channel_id:
            logger.error("WhatsApp channel ID not configured")
            return False

        try:
            from azure.communication.messages.models import (
                MessageTemplate,
                MessageTemplateText,
                TemplateNotificationContent,
            )

            phone = customer_id.replace(" ", "").replace("-", "")
            if not phone.startswith("+"):
                phone = f"+{phone}"

            # Build template
            template = MessageTemplate(
                name=template_name,
                language=language,
            )

            # Add template values if provided
            if template_values:
                template.values = [
                    MessageTemplateText(name=f"value{i}", text=val)
                    for i, val in enumerate(template_values)
                ]

            content = TemplateNotificationContent(
                channel_registration_id=self.channel_id,
                to=[phone],
                template=template,
            )

            response = self._client.send(content)
            logger.info("WhatsApp template '%s' sent to %s", template_name, phone)
            return bool(response)

        except Exception as e:
            logger.error("Failed to send WhatsApp template: %s", e)
            return False

    async def close(self) -> None:
        """Close the WhatsApp adapter."""
        await super().close()
        self._client = None
