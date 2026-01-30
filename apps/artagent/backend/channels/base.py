"""
Base Channel Adapter
====================

Abstract base class for all channel adapters.
Defines the interface for sending/receiving messages across channels.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from utils.ml_logging import get_logger

logger = get_logger("channels.base")


class ChannelType(str, Enum):
    """Supported communication channels."""

    VOICE = "voice"
    WHATSAPP = "whatsapp"
    WEBCHAT = "webchat"
    SMS = "sms"  # Future support


@dataclass
class ChannelMessage:
    """
    Unified message format across all channels.

    Attributes:
        channel: Source/destination channel type
        customer_id: Unique customer identifier (phone number or user ID)
        session_id: Current session identifier
        content: Message text content
        timestamp: UTC timestamp of message
        metadata: Channel-specific metadata
        is_from_customer: True if message is from customer, False if from agent
    """

    channel: ChannelType
    customer_id: str
    session_id: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)
    is_from_customer: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "channel": self.channel.value,
            "customer_id": self.customer_id,
            "session_id": self.session_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "is_from_customer": self.is_from_customer,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChannelMessage:
        """Create from dictionary."""
        return cls(
            channel=ChannelType(data["channel"]),
            customer_id=data["customer_id"],
            session_id=data["session_id"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
            is_from_customer=data.get("is_from_customer", True),
        )


class BaseChannelAdapter(ABC):
    """
    Abstract base class for channel adapters.

    Each channel (WhatsApp, WebChat, etc.) implements this interface
    to provide consistent message handling across channels.
    """

    channel_type: ChannelType

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize channel adapter.

        Args:
            config: Channel-specific configuration
        """
        self.config = config or {}
        self._initialized = False
        logger.info("Initializing %s channel adapter", self.channel_type.value)

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize channel connections and resources.

        Called during application startup.
        """
        pass

    @abstractmethod
    async def send_message(
        self,
        customer_id: str,
        message: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send a message to a customer via this channel.

        Args:
            customer_id: Customer identifier (phone number for WhatsApp)
            message: Text content to send
            session_id: Optional session identifier for tracking
            metadata: Optional channel-specific metadata

        Returns:
            True if message sent successfully, False otherwise
        """
        pass

    @abstractmethod
    async def handle_incoming(
        self,
        raw_message: dict[str, Any],
    ) -> ChannelMessage:
        """
        Process an incoming message from this channel.

        Args:
            raw_message: Raw message payload from channel webhook/socket

        Returns:
            Normalized ChannelMessage object
        """
        pass

    async def send_handoff_notification(
        self,
        customer_id: str,
        source_channel: ChannelType,
        context_summary: str,
        handoff_link: str | None = None,
    ) -> bool:
        """
        Send a notification that conversation is being handed off.

        Args:
            customer_id: Customer identifier
            source_channel: Channel the customer is coming from
            context_summary: Brief summary of conversation so far
            handoff_link: Optional deep link for web chat

        Returns:
            True if notification sent successfully
        """
        if source_channel == ChannelType.VOICE:
            message = (
                f"Hi! I'm continuing our phone conversation here. "
                f"Here's what we discussed: {context_summary}\n\n"
                f"How can I help you further?"
            )
        else:
            message = (
                f"Continuing from {source_channel.value}. "
                f"Context: {context_summary}\n\n"
                f"How can I help?"
            )

        if handoff_link:
            message += f"\n\nOr continue on web: {handoff_link}"

        return await self.send_message(customer_id, message)

    async def close(self) -> None:
        """
        Close channel connections and cleanup resources.

        Called during application shutdown.
        """
        logger.info("Closing %s channel adapter", self.channel_type.value)
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if adapter is initialized."""
        return self._initialized
