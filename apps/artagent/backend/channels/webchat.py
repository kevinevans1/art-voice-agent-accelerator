"""
Web Chat Channel Adapter
========================

Adapter for web-based chat via WebSocket connections.
Enables real-time bidirectional messaging with web clients.

The web chat uses a simple WebSocket protocol:
    - Client connects to /api/v1/channels/webchat/ws/{customer_id}
    - Messages are JSON: {"type": "message", "content": "Hello"}
    - Server responds with: {"type": "message", "content": "Response", "agent": "Concierge"}
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket

from apps.artagent.backend.channels.base import (
    BaseChannelAdapter,
    ChannelMessage,
    ChannelType,
)
from utils.ml_logging import get_logger

logger = get_logger("channels.webchat")


class WebChatConnectionManager:
    """
    Manages active WebSocket connections for web chat.

    Tracks connected clients and provides methods to send messages
    to specific customers or broadcast to groups.
    """

    def __init__(self):
        """Initialize connection manager."""
        # Map customer_id -> WebSocket connection
        self._connections: dict[str, WebSocket] = {}
        # Map customer_id -> session_id
        self._sessions: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        customer_id: str,
        session_id: str,
    ) -> None:
        """
        Register a new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            customer_id: Customer identifier
            session_id: Session identifier
        """
        await websocket.accept()
        async with self._lock:
            # Close existing connection if any
            if customer_id in self._connections:
                try:
                    await self._connections[customer_id].close()
                except Exception:
                    pass
            self._connections[customer_id] = websocket
            self._sessions[customer_id] = session_id
        logger.info("WebChat connected: %s (session: %s)", customer_id, session_id)

    async def disconnect(self, customer_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            customer_id: Customer identifier
        """
        async with self._lock:
            self._connections.pop(customer_id, None)
            self._sessions.pop(customer_id, None)
        logger.info("WebChat disconnected: %s", customer_id)

    async def send_message(
        self,
        customer_id: str,
        message: dict[str, Any],
    ) -> bool:
        """
        Send a message to a specific customer.

        Args:
            customer_id: Customer identifier
            message: Message payload to send

        Returns:
            True if sent successfully, False if customer not connected
        """
        async with self._lock:
            websocket = self._connections.get(customer_id)

        if not websocket:
            logger.warning("No WebChat connection for customer: %s", customer_id)
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error("Failed to send WebChat message to %s: %s", customer_id, e)
            await self.disconnect(customer_id)
            return False

    def get_session_id(self, customer_id: str) -> str | None:
        """Get session ID for a customer."""
        return self._sessions.get(customer_id)

    def is_connected(self, customer_id: str) -> bool:
        """Check if a customer is connected."""
        return customer_id in self._connections

    @property
    def connected_count(self) -> int:
        """Get number of connected clients."""
        return len(self._connections)


# Global connection manager instance
_connection_manager = WebChatConnectionManager()


def get_connection_manager() -> WebChatConnectionManager:
    """Get the global WebChat connection manager."""
    return _connection_manager


class WebChatAdapter(BaseChannelAdapter):
    """
    Web chat channel adapter using WebSocket connections.

    Provides real-time messaging with web-based clients.
    """

    channel_type = ChannelType.WEBCHAT

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize WebChat adapter.

        Args:
            config: Optional configuration overrides
        """
        super().__init__(config)
        self._manager = get_connection_manager()

    async def initialize(self) -> None:
        """Initialize the WebChat adapter."""
        self._initialized = True
        logger.info("WebChat adapter initialized")

    async def send_message(
        self,
        customer_id: str,
        message: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send a message to a web chat customer.

        Args:
            customer_id: Customer identifier
            message: Text message to send
            session_id: Optional session ID
            metadata: Optional metadata (agent name, etc.)

        Returns:
            True if sent successfully
        """
        if not self._initialized:
            logger.error("WebChat adapter not initialized")
            return False

        payload = {
            "type": "message",
            "content": message,
            "timestamp": datetime.now(UTC).isoformat(),
            "agent": metadata.get("agent_name", "Assistant") if metadata else "Assistant",
        }

        if metadata:
            payload["metadata"] = metadata

        return await self._manager.send_message(customer_id, payload)

    async def handle_incoming(
        self,
        raw_message: dict[str, Any],
    ) -> ChannelMessage:
        """
        Process an incoming WebChat message.

        Expected message format:
        {
            "type": "message",
            "content": "Hello!",
            "customer_id": "user_123",
            "session_id": "web_abc"
        }

        Args:
            raw_message: Raw message payload

        Returns:
            Normalized ChannelMessage
        """
        customer_id = raw_message.get("customer_id", "")
        session_id = raw_message.get("session_id", f"web_{customer_id}")
        content = raw_message.get("content", "")
        timestamp_str = raw_message.get("timestamp")

        # Parse timestamp
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                timestamp = datetime.now(UTC)
        else:
            timestamp = datetime.now(UTC)

        logger.debug("WebChat message: %s -> %s", customer_id, content[:50] if content else "(empty)")

        return ChannelMessage(
            channel=ChannelType.WEBCHAT,
            customer_id=customer_id,
            session_id=session_id,
            content=content,
            timestamp=timestamp,
            metadata=raw_message.get("metadata", {}),
            is_from_customer=True,
        )

    async def send_typing_indicator(self, customer_id: str, is_typing: bool = True) -> bool:
        """
        Send a typing indicator to the customer.

        Args:
            customer_id: Customer identifier
            is_typing: True to show typing, False to hide

        Returns:
            True if sent successfully
        """
        payload = {
            "type": "typing",
            "is_typing": is_typing,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        return await self._manager.send_message(customer_id, payload)

    async def send_system_message(
        self,
        customer_id: str,
        message: str,
        message_type: str = "info",
    ) -> bool:
        """
        Send a system message (not from an agent).

        Args:
            customer_id: Customer identifier
            message: System message content
            message_type: Type: info, warning, error, success

        Returns:
            True if sent successfully
        """
        payload = {
            "type": "system",
            "content": message,
            "message_type": message_type,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        return await self._manager.send_message(customer_id, payload)

    async def send_handoff_notification(
        self,
        customer_id: str,
        source_channel: ChannelType,
        context_summary: str,
        handoff_link: str | None = None,
    ) -> bool:
        """
        Send handoff notification with context.

        For web chat, we send a rich system message with the context.
        """
        payload = {
            "type": "handoff",
            "source_channel": source_channel.value,
            "context_summary": context_summary,
            "message": f"Continuing from {source_channel.value}. I have your context - no need to repeat yourself!",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        return await self._manager.send_message(customer_id, payload)

    def is_customer_connected(self, customer_id: str) -> bool:
        """Check if a customer is currently connected."""
        return self._manager.is_connected(customer_id)

    @property
    def connected_count(self) -> int:
        """Get number of connected clients."""
        return self._manager.connected_count

    async def close(self) -> None:
        """Close the WebChat adapter."""
        await super().close()
        # Note: We don't close individual connections here as they may be
        # managed by the FastAPI WebSocket handler
