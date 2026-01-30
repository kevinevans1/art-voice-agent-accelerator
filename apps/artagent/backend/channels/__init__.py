"""
Omnichannel Support
===================

Channel adapters for multi-channel customer interactions.
Enables seamless handoff between Voice, WhatsApp, and Web Chat
while preserving conversation context.

Channels:
    - Voice: Azure Communication Services (existing)
    - WhatsApp: ACS WhatsApp integration
    - WebChat: WebSocket-based web interface

Usage:
    from apps.artagent.backend.channels import (
        ChannelType,
        get_channel_adapter,
        CustomerContext,
        WhatsAppAdapter,
        WebChatAdapter,
    )
"""

from apps.artagent.backend.channels.base import (
    BaseChannelAdapter,
    ChannelMessage,
    ChannelType,
)
from apps.artagent.backend.channels.context import (
    CustomerContext,
    CustomerContextManager,
)
from apps.artagent.backend.channels.whatsapp import WhatsAppAdapter
from apps.artagent.backend.channels.webchat import WebChatAdapter, get_connection_manager


def get_channel_adapter(channel_type: ChannelType) -> BaseChannelAdapter:
    """
    Factory function to get the appropriate channel adapter.

    Args:
        channel_type: Type of channel to get adapter for

    Returns:
        Instance of the appropriate channel adapter

    Raises:
        ValueError: If channel type is not supported
    """
    adapters = {
        ChannelType.WHATSAPP: WhatsAppAdapter,
        ChannelType.WEBCHAT: WebChatAdapter,
    }

    adapter_class = adapters.get(channel_type)
    if adapter_class is None:
        raise ValueError(f"Unsupported channel type: {channel_type}")

    return adapter_class()


__all__ = [
    # Base classes
    "BaseChannelAdapter",
    "ChannelMessage",
    "ChannelType",
    # Context
    "CustomerContext",
    "CustomerContextManager",
    # Adapters
    "WhatsAppAdapter",
    "WebChatAdapter",
    # Factory
    "get_channel_adapter",
    "get_connection_manager",
]
