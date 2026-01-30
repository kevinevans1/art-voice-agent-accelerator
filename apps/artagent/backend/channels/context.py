"""
Customer Context Manager
========================

Manages unified customer context across all channels.
Stores conversation history, collected data, and session state
in Cosmos DB for cross-channel continuity.

This ensures customers don't have to repeat themselves when
switching between voice, WhatsApp, and web chat.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from utils.ml_logging import get_logger

logger = get_logger("channels.context")


@dataclass
class SessionInfo:
    """Information about a single channel session."""

    channel: str
    session_id: str
    started_at: datetime
    ended_at: datetime | None = None
    status: str = "active"  # active, transferred, completed
    transcript_summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "channel": self.channel,
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "status": self.status,
            "transcript_summary": self.transcript_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionInfo:
        """Create from dictionary."""
        return cls(
            channel=data["channel"],
            session_id=data["session_id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            status=data.get("status", "active"),
            transcript_summary=data.get("transcript_summary"),
        )


@dataclass
class CustomerContext:
    """
    Unified customer context across all channels.

    This is the single source of truth for a customer's interaction
    history, collected information, and current state.

    Attributes:
        customer_id: Unique customer identifier (typically phone number)
        phone_number: Customer's phone number
        foundry_thread_id: Azure AI Foundry thread ID for shared agent memory
        sessions: List of all channel sessions
        collected_data: Information gathered across sessions
        conversation_summary: AI-generated summary of all interactions
        preferences: Customer preferences
        created_at: First interaction timestamp
        updated_at: Last update timestamp
    """

    customer_id: str
    phone_number: str | None = None
    email: str | None = None
    name: str | None = None
    foundry_thread_id: str | None = None
    sessions: list[SessionInfo] = field(default_factory=list)
    collected_data: dict[str, Any] = field(default_factory=dict)
    conversation_summary: str | None = None
    preferences: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to Cosmos DB document format."""
        return {
            "id": self.customer_id,
            "partitionKey": self.customer_id,
            "customer_id": self.customer_id,
            "phone_number": self.phone_number,
            "email": self.email,
            "name": self.name,
            "foundry_thread_id": self.foundry_thread_id,
            "sessions": [s.to_dict() for s in self.sessions],
            "collected_data": self.collected_data,
            "conversation_summary": self.conversation_summary,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CustomerContext:
        """Create from Cosmos DB document."""
        return cls(
            customer_id=data["customer_id"],
            phone_number=data.get("phone_number"),
            email=data.get("email"),
            name=data.get("name"),
            foundry_thread_id=data.get("foundry_thread_id"),
            sessions=[SessionInfo.from_dict(s) for s in data.get("sessions", [])],
            collected_data=data.get("collected_data", {}),
            conversation_summary=data.get("conversation_summary"),
            preferences=data.get("preferences", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(UTC),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(UTC),
        )

    def add_session(
        self,
        channel: str,
        session_id: str,
    ) -> SessionInfo:
        """Add a new session to the customer context."""
        session = SessionInfo(
            channel=channel,
            session_id=session_id,
            started_at=datetime.now(UTC),
        )
        self.sessions.append(session)
        self.updated_at = datetime.now(UTC)
        return session

    def get_active_session(self, channel: str | None = None) -> SessionInfo | None:
        """Get the most recent active session, optionally filtered by channel."""
        for session in reversed(self.sessions):
            if session.status == "active":
                if channel is None or session.channel == channel:
                    return session
        return None

    def end_session(
        self,
        session_id: str,
        status: str = "completed",
        summary: str | None = None,
    ) -> None:
        """Mark a session as ended."""
        for session in self.sessions:
            if session.session_id == session_id:
                session.ended_at = datetime.now(UTC)
                session.status = status
                if summary:
                    session.transcript_summary = summary
                self.updated_at = datetime.now(UTC)
                break

    def update_collected_data(self, data: dict[str, Any]) -> None:
        """Merge new collected data into existing."""
        self.collected_data.update(data)
        self.updated_at = datetime.now(UTC)

    def get_context_for_handoff(self) -> dict[str, Any]:
        """
        Get context summary for handoff to another channel.

        Returns a dict suitable for passing to the new channel's agent.
        """
        # Get summaries from recent sessions
        recent_summaries = []
        for session in reversed(self.sessions[-5:]):  # Last 5 sessions
            if session.transcript_summary:
                recent_summaries.append(f"[{session.channel}] {session.transcript_summary}")

        return {
            "customer_id": self.customer_id,
            "customer_name": self.name,
            "collected_data": self.collected_data,
            "conversation_summary": self.conversation_summary or "\n".join(recent_summaries),
            "previous_channels": [s.channel for s in self.sessions],
            "preferences": self.preferences,
        }


class CustomerContextManager:
    """
    Manages customer context persistence in Cosmos DB.

    Provides CRUD operations for CustomerContext with caching
    via Redis for fast lookups during active conversations.
    """

    def __init__(
        self,
        cosmos_manager: Any = None,
        redis_manager: Any = None,
    ):
        """
        Initialize the context manager.

        Args:
            cosmos_manager: Cosmos DB manager instance
            redis_manager: Redis manager instance for caching
        """
        self.cosmos = cosmos_manager
        self.redis = redis_manager
        self._collection_name = os.getenv("COSMOS_CUSTOMER_CONTEXT_COLLECTION", "customer_contexts")
        self._cache_ttl = 3600  # 1 hour cache TTL
        logger.info("CustomerContextManager initialized")

    async def get_or_create(
        self,
        customer_id: str,
        phone_number: str | None = None,
    ) -> CustomerContext:
        """
        Get existing customer context or create new one.

        Args:
            customer_id: Unique customer identifier
            phone_number: Optional phone number

        Returns:
            CustomerContext instance
        """
        # Try cache first
        cached = await self._get_from_cache(customer_id)
        if cached:
            logger.debug("Customer context cache hit: %s", customer_id)
            return cached

        # Try Cosmos DB
        if self.cosmos:
            doc = await self._get_from_cosmos(customer_id)
            if doc:
                context = CustomerContext.from_dict(doc)
                await self._set_cache(context)
                logger.debug("Customer context loaded from Cosmos: %s", customer_id)
                return context

        # Create new context
        context = CustomerContext(
            customer_id=customer_id,
            phone_number=phone_number or customer_id,
        )
        await self.save(context)
        logger.info("Created new customer context: %s", customer_id)
        return context

    async def save(self, context: CustomerContext) -> None:
        """
        Save customer context to Cosmos DB and cache.

        Args:
            context: CustomerContext to save
        """
        context.updated_at = datetime.now(UTC)

        # Save to Cosmos DB
        if self.cosmos:
            await self._save_to_cosmos(context)

        # Update cache
        await self._set_cache(context)
        logger.debug("Saved customer context: %s", context.customer_id)

    async def get_by_phone(self, phone_number: str) -> CustomerContext | None:
        """
        Look up customer context by phone number.

        Args:
            phone_number: Phone number to search

        Returns:
            CustomerContext if found, None otherwise
        """
        # Normalize phone number (remove spaces, ensure + prefix)
        normalized = phone_number.replace(" ", "").replace("-", "")
        if not normalized.startswith("+"):
            normalized = f"+{normalized}"

        # Try with normalized number as customer_id
        return await self.get_or_create(normalized, phone_number=normalized)

    async def add_session_to_customer(
        self,
        customer_id: str,
        channel: str,
        session_id: str,
    ) -> CustomerContext:
        """
        Add a new session to a customer's context.

        Args:
            customer_id: Customer identifier
            channel: Channel type (voice, whatsapp, webchat)
            session_id: New session identifier

        Returns:
            Updated CustomerContext
        """
        context = await self.get_or_create(customer_id)
        context.add_session(channel, session_id)
        await self.save(context)
        return context

    async def end_customer_session(
        self,
        customer_id: str,
        session_id: str,
        status: str = "completed",
        summary: str | None = None,
    ) -> CustomerContext | None:
        """
        End a customer's session.

        Args:
            customer_id: Customer identifier
            session_id: Session to end
            status: End status (completed, transferred, abandoned)
            summary: Optional conversation summary

        Returns:
            Updated CustomerContext or None if not found
        """
        context = await self.get_or_create(customer_id)
        context.end_session(session_id, status, summary)
        await self.save(context)
        return context

    async def update_customer_data(
        self,
        customer_id: str,
        data: dict[str, Any],
    ) -> CustomerContext:
        """
        Update collected data for a customer.

        Args:
            customer_id: Customer identifier
            data: Data to merge into collected_data

        Returns:
            Updated CustomerContext
        """
        context = await self.get_or_create(customer_id)
        context.update_collected_data(data)
        await self.save(context)
        return context

    async def set_foundry_thread(
        self,
        customer_id: str,
        thread_id: str,
    ) -> CustomerContext:
        """
        Set the Foundry thread ID for a customer.

        Args:
            customer_id: Customer identifier
            thread_id: Azure AI Foundry thread ID

        Returns:
            Updated CustomerContext
        """
        context = await self.get_or_create(customer_id)
        context.foundry_thread_id = thread_id
        await self.save(context)
        return context

    # ─────────────────────────────────────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────────────────────────────────────

    async def _get_from_cache(self, customer_id: str) -> CustomerContext | None:
        """Get context from Redis cache."""
        if not self.redis:
            return None
        try:
            key = f"customer_context:{customer_id}"
            data = self.redis.get(key)
            if data:
                import json
                return CustomerContext.from_dict(json.loads(data))
        except Exception as e:
            logger.warning("Cache get failed: %s", e)
        return None

    async def _set_cache(self, context: CustomerContext) -> None:
        """Set context in Redis cache."""
        if not self.redis:
            return
        try:
            import json
            key = f"customer_context:{context.customer_id}"
            self.redis.set(key, json.dumps(context.to_dict()), ex=self._cache_ttl)
        except Exception as e:
            logger.warning("Cache set failed: %s", e)

    async def _get_from_cosmos(self, customer_id: str) -> dict[str, Any] | None:
        """Get context from Cosmos DB."""
        if not self.cosmos:
            return None
        try:
            return self.cosmos.find_one({"customer_id": customer_id})
        except Exception as e:
            logger.warning("Cosmos get failed: %s", e)
        return None

    async def _save_to_cosmos(self, context: CustomerContext) -> None:
        """Save context to Cosmos DB."""
        if not self.cosmos:
            return
        try:
            doc = context.to_dict()
            self.cosmos.upsert_one({"customer_id": context.customer_id}, doc)
        except Exception as e:
            logger.error("Cosmos save failed: %s", e)
            raise
