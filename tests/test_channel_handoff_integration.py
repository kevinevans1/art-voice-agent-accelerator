"""
Channel Handoff Integration Tests
=================================

Tests the end-to-end channel handoff flow:
1. Tool detection in orchestrator
2. Tool execution via agent
3. Context persistence via ChannelHandoffHandler
4. Call end signal returned

These tests validate the omnichannel handoff feature for utilities demo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# TEST FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_context_manager():
    """Create a mock CustomerContextManager."""
    manager = MagicMock()
    manager.get_or_create = AsyncMock()
    manager.save = AsyncMock()
    
    # Create a mock context that's returned
    mock_context = MagicMock()
    mock_context.customer_id = "test-customer-123"
    mock_context.conversation_summary = ""
    mock_context.update_collected_data = MagicMock()
    mock_context.get_active_session = MagicMock(return_value=None)
    mock_context.add_session = MagicMock()
    mock_context.end_session = MagicMock()
    
    manager.get_or_create.return_value = mock_context
    manager._mock_context = mock_context
    
    return manager


@pytest.fixture
def channel_handoff_handler(mock_context_manager):
    """Create a ChannelHandoffHandler with mocked dependencies."""
    from apps.artagent.backend.voice.shared.channel_handoff import ChannelHandoffHandler
    
    return ChannelHandoffHandler(
        context_manager=mock_context_manager,
        whatsapp_adapter=None,  # No adapter for test
        webchat_adapter=None,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CHANNEL HANDOFF HANDLER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestChannelHandoffHandler:
    """Tests for ChannelHandoffHandler."""

    @pytest.mark.asyncio
    async def test_execute_handoff_returns_success(self, channel_handoff_handler):
        """
        BASELINE: execute_handoff should return success with handoff details.
        """
        result = await channel_handoff_handler.execute_handoff(
            target_channel="whatsapp",
            customer_id="+1234567890",
            conversation_summary="Customer inquired about billing",
            collected_data={"account_number": "12345"},
            session_id="test-session-123",
        )

        assert result.success is True
        assert result.target_channel == "whatsapp"
        assert result.handoff_id is not None
        assert "WhatsApp" in result.end_call_message

    @pytest.mark.asyncio
    async def test_execute_handoff_saves_context(self, channel_handoff_handler, mock_context_manager):
        """
        BASELINE: execute_handoff should save context to CustomerContextManager.
        """
        await channel_handoff_handler.execute_handoff(
            target_channel="webchat",
            customer_id="customer-123",
            conversation_summary="Discussed outage status",
            collected_data={"outage_id": "OUT-001"},
            session_id="voice-session-456",
        )

        # Verify context manager was called
        mock_context_manager.get_or_create.assert_called_once()
        mock_context_manager.save.assert_called_once()
        
        # Verify context was updated
        mock_context = mock_context_manager._mock_context
        assert mock_context.conversation_summary == "Discussed outage status"
        mock_context.update_collected_data.assert_called_with({"outage_id": "OUT-001"})

    @pytest.mark.asyncio
    async def test_execute_handoff_webchat_message(self, channel_handoff_handler):
        """
        BASELINE: WebChat handoff should have appropriate end call message.
        """
        result = await channel_handoff_handler.execute_handoff(
            target_channel="webchat",
            customer_id="customer-123",
            conversation_summary="Test",
        )

        assert "web chat" in result.end_call_message.lower()

    def test_is_channel_handoff_tool(self, channel_handoff_handler):
        """
        BASELINE: is_channel_handoff_tool should detect execute_channel_handoff.
        """
        assert channel_handoff_handler.is_channel_handoff_tool("execute_channel_handoff") is True
        assert channel_handoff_handler.is_channel_handoff_tool("handoff_to_agent") is False
        assert channel_handoff_handler.is_channel_handoff_tool("check_queue_status") is False

    def test_parse_channel_handoff_result(self, channel_handoff_handler):
        """
        BASELINE: parse_channel_handoff_result should detect channel_switch handoffs.
        """
        # Valid channel handoff
        is_handoff, channel = channel_handoff_handler.parse_channel_handoff_result({
            "handoff": True,
            "handoff_type": "channel_switch",
            "target_channel": "whatsapp",
        })
        assert is_handoff is True
        assert channel == "whatsapp"

        # Not a channel handoff
        is_handoff, channel = channel_handoff_handler.parse_channel_handoff_result({
            "success": True,
            "message": "Regular tool result",
        })
        assert is_handoff is False
        assert channel is None


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def tool_registry():
    """Import tool registry after tools are registered."""
    # Import the registry module which triggers auto-registration
    from apps.artagent.backend.registries.toolstore import registry as tool_module
    
    # Ensure tools are initialized
    tool_module.initialize_tools()
    
    return {
        "list_tools": tool_module.list_tools,
        "execute_tool": tool_module.execute_tool,
        "is_handoff_tool": tool_module.is_handoff_tool,
    }


class TestChannelHandoffToolRegistration:
    """Tests for channel handoff tool registration."""

    def test_execute_channel_handoff_is_registered(self, tool_registry):
        """
        BASELINE: execute_channel_handoff should be in the tool registry.
        """
        all_tools = tool_registry["list_tools"]()
        assert "execute_channel_handoff" in all_tools

    def test_execute_channel_handoff_is_marked_as_handoff(self, tool_registry):
        """
        BASELINE: execute_channel_handoff should be marked as a handoff tool.
        """
        is_handoff = tool_registry["is_handoff_tool"]
        assert is_handoff("execute_channel_handoff") is True

    def test_offer_channel_switch_is_not_handoff(self, tool_registry):
        """
        BASELINE: offer_channel_switch should NOT be marked as a handoff tool.
        
        It only offers the option - the actual handoff is execute_channel_handoff.
        """
        is_handoff = tool_registry["is_handoff_tool"]
        assert is_handoff("offer_channel_switch") is False

    def test_check_queue_status_is_not_handoff(self, tool_registry):
        """
        BASELINE: check_queue_status should NOT be marked as a handoff tool.
        """
        is_handoff = tool_registry["is_handoff_tool"]
        assert is_handoff("check_queue_status") is False

    @pytest.mark.asyncio
    async def test_execute_channel_handoff_returns_handoff_signal(self, tool_registry):
        """
        BASELINE: execute_channel_handoff should return handoff signal.
        """
        execute = tool_registry["execute_tool"]
        result = await execute("execute_channel_handoff", {
            "target_channel": "whatsapp",
            "handoff_message": "Test handoff",
            "customer_phone": "+1234567890",
        })

        assert result.get("handoff") is True
        assert result.get("handoff_type") == "channel_switch"
        assert result.get("target_channel") == "whatsapp"
        assert result.get("end_call") is True
        assert "end_call_message" in result


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR RESULT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestOrchestratorResultFields:
    """Tests for OrchestratorResult dataclass fields."""

    def test_orchestrator_result_has_should_end_call(self):
        """
        BASELINE: OrchestratorResult should have should_end_call field.
        """
        from apps.artagent.backend.voice.shared.base import OrchestratorResult

        result = OrchestratorResult(
            response_text="Thank you for calling",
            should_end_call=True,
        )

        assert result.should_end_call is True

    def test_orchestrator_result_has_metadata(self):
        """
        BASELINE: OrchestratorResult should have metadata field.
        """
        from apps.artagent.backend.voice.shared.base import OrchestratorResult

        result = OrchestratorResult(
            response_text="Thank you",
            metadata={"channel_handoff": True, "target_channel": "whatsapp"},
        )

        assert result.metadata.get("channel_handoff") is True
        assert result.metadata.get("target_channel") == "whatsapp"

    def test_orchestrator_result_defaults(self):
        """
        BASELINE: OrchestratorResult should have sensible defaults.
        """
        from apps.artagent.backend.voice.shared.base import OrchestratorResult

        result = OrchestratorResult()

        assert result.should_end_call is False
        assert result.metadata == {}


# ═══════════════════════════════════════════════════════════════════════════════
# ADAPTER INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestCascadeAdapterChannelHandoff:
    """Tests for CascadeOrchestratorAdapter channel handoff integration."""

    def test_adapter_has_set_channel_handoff_handler(self):
        """
        BASELINE: CascadeOrchestratorAdapter should have set_channel_handoff_handler method.
        """
        from apps.artagent.backend.voice.speech_cascade.orchestrator import (
            CascadeOrchestratorAdapter,
        )

        adapter = CascadeOrchestratorAdapter.create(
            start_agent="UtilitiesConcierge",
            session_id="test-session",
        )

        assert hasattr(adapter, "set_channel_handoff_handler")

    def test_adapter_accepts_channel_handoff_handler(self, channel_handoff_handler):
        """
        BASELINE: set_channel_handoff_handler should accept ChannelHandoffHandler.
        """
        from apps.artagent.backend.voice.speech_cascade.orchestrator import (
            CascadeOrchestratorAdapter,
        )

        adapter = CascadeOrchestratorAdapter.create(
            start_agent="UtilitiesConcierge",
            session_id="test-session",
        )

        # Should not raise
        adapter.set_channel_handoff_handler(channel_handoff_handler)
        
        assert adapter._channel_handoff_handler is not None

    def test_get_cascade_orchestrator_wires_handler_from_app_state(self, mock_context_manager):
        """
        BASELINE: get_cascade_orchestrator should wire ChannelHandoffHandler from app_state.
        """
        from apps.artagent.backend.voice.speech_cascade.orchestrator import (
            get_cascade_orchestrator,
        )

        # Create mock app_state
        app_state = MagicMock()
        app_state.customer_context_manager = mock_context_manager

        adapter = get_cascade_orchestrator(
            start_agent="UtilitiesConcierge",
            session_id="test-session",
            app_state=app_state,
        )

        # Handler should be wired
        assert adapter._channel_handoff_handler is not None


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT PERSISTENCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestCustomerContextManagerLifecycle:
    """Tests for CustomerContextManager initialization in app lifecycle."""

    def test_lifecycle_steps_has_customer_context_manager_init(self):
        """
        BASELINE: Lifecycle steps should initialize CustomerContextManager.
        """
        # Import the lifecycle module
        import apps.artagent.backend.lifecycle.steps as steps

        # Check the init function exists and mentions context manager
        source = steps.__file__
        assert source is not None
        
        # Read the file to verify the initialization exists
        with open(source) as f:
            content = f.read()
        
        assert "customer_context_manager" in content
        assert "CustomerContextManager" in content


class TestChannelsEndpointIntegration:
    """Tests for channels endpoint integration with CustomerContextManager."""

    def test_channels_module_imports_correctly(self):
        """
        BASELINE: Channels module should import without errors.
        """
        # This should not raise
        from apps.artagent.backend.api.v1.endpoints import channels
        
        assert channels is not None

    def test_channels_has_handoff_endpoint(self):
        """
        BASELINE: Channels module should have handoff endpoint.
        """
        from apps.artagent.backend.api.v1.endpoints.channels import router
        
        # Check for handoff route
        routes = [route.path for route in router.routes]
        assert "/handoff" in routes or any("handoff" in route for route in routes)
