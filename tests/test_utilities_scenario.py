"""
Utilities Scenario Integration Tests
=====================================

Tests for the utilities scenario to verify:
1. Scenario loads correctly with all agents
2. All agents exist and are loadable
3. All tools referenced by agents are registered
4. All handoffs are properly configured
5. Connectivity between agents via handoffs works

Run with:
    pytest tests/test_utilities_scenario.py -v
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

SCENARIO_PATH = Path(__file__).parent.parent / "apps/artagent/backend/registries/scenariostore/utilities"
AGENTSTORE_PATH = Path(__file__).parent.parent / "apps/artagent/backend/registries/agentstore"

UTILITIES_AGENTS = [
    "UtilitiesConcierge",
    "BillingAgent", 
    "OutageAgent",
    "ServiceAgent",
    "UsageAgent",
]

# Tools that are always available (from common modules)
COMMON_TOOLS = {
    "verify_customer_identity",
    "get_account_info",
    "get_service_address",
    "check_queue_status",
    "offer_channel_switch",
    "execute_channel_handoff",
    "escalate_human",
    "handoff_concierge",
}

# Handoff tools expected in utilities scenario
UTILITIES_HANDOFF_TOOLS = {
    "handoff_billing_agent",
    "handoff_outage_agent",
    "handoff_service_agent",
    "handoff_usage_agent",
    "handoff_concierge",
}


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def utilities_orchestration() -> dict[str, Any]:
    """Load the utilities scenario orchestration YAML."""
    path = SCENARIO_PATH / "orchestration.yaml"
    assert path.exists(), f"Orchestration file not found: {path}"
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def agent_configs() -> dict[str, dict[str, Any]]:
    """Load all utilities agent YAML configs."""
    agents = {}
    agent_name_to_folder = {
        "UtilitiesConcierge": "utilities_concierge",
        "BillingAgent": "billing_agent",
        "OutageAgent": "outage_agent",
        "ServiceAgent": "service_agent",
        "UsageAgent": "usage_agent",
    }
    
    for agent_name, folder_name in agent_name_to_folder.items():
        agent_path = AGENTSTORE_PATH / folder_name / "agent.yaml"
        if agent_path.exists():
            with open(agent_path) as f:
                agents[agent_name] = yaml.safe_load(f)
    
    return agents


@pytest.fixture
def tool_registry():
    """Get the initialized tool registry."""
    # Import and initialize tools
    from apps.artagent.backend.registries.toolstore.registry import (
        _TOOL_DEFINITIONS,
        initialize_tools,
    )
    initialize_tools()
    return _TOOL_DEFINITIONS


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO STRUCTURE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestUtilitiesScenarioStructure:
    """Tests for utilities scenario structure and configuration."""
    
    def test_scenario_file_exists(self):
        """Verify the orchestration.yaml file exists."""
        path = SCENARIO_PATH / "orchestration.yaml"
        assert path.exists(), f"Utilities scenario orchestration not found at {path}"
    
    def test_scenario_loads_without_error(self, utilities_orchestration):
        """Verify the scenario YAML parses correctly."""
        assert utilities_orchestration is not None
        assert "name" in utilities_orchestration
        assert utilities_orchestration["name"] == "utilities"
    
    def test_scenario_has_start_agent(self, utilities_orchestration):
        """Verify scenario defines a starting agent."""
        assert "start_agent" in utilities_orchestration
        assert utilities_orchestration["start_agent"] == "UtilitiesConcierge"
    
    def test_scenario_lists_all_required_agents(self, utilities_orchestration):
        """Verify all expected agents are listed in scenario."""
        agents = utilities_orchestration.get("agents", [])
        for agent in UTILITIES_AGENTS:
            assert agent in agents, f"Agent {agent} not listed in scenario"
    
    def test_scenario_has_handoffs_defined(self, utilities_orchestration):
        """Verify handoffs are defined in the scenario."""
        handoffs = utilities_orchestration.get("handoffs", [])
        assert len(handoffs) > 0, "No handoffs defined in scenario"
    
    def test_scenario_handoff_structure(self, utilities_orchestration):
        """Verify each handoff has required fields."""
        handoffs = utilities_orchestration.get("handoffs", [])
        required_fields = {"from", "to", "tool"}
        
        for i, handoff in enumerate(handoffs):
            for field in required_fields:
                assert field in handoff, f"Handoff {i} missing required field: {field}"
    
    def test_handoffs_connect_valid_agents(self, utilities_orchestration):
        """Verify handoffs only reference agents in the scenario."""
        agents = set(utilities_orchestration.get("agents", []))
        handoffs = utilities_orchestration.get("handoffs", [])
        
        for handoff in handoffs:
            from_agent = handoff.get("from")
            to_agent = handoff.get("to")
            assert from_agent in agents, f"Handoff from unknown agent: {from_agent}"
            assert to_agent in agents, f"Handoff to unknown agent: {to_agent}"


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT EXISTENCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestUtilitiesAgentExistence:
    """Tests verifying all utilities agents exist and are valid."""
    
    @pytest.mark.parametrize("agent_name,folder_name", [
        ("UtilitiesConcierge", "utilities_concierge"),
        ("BillingAgent", "billing_agent"),
        ("OutageAgent", "outage_agent"),
        ("ServiceAgent", "service_agent"),
        ("UsageAgent", "usage_agent"),
    ])
    def test_agent_yaml_exists(self, agent_name: str, folder_name: str):
        """Verify each agent has a YAML configuration file."""
        path = AGENTSTORE_PATH / folder_name / "agent.yaml"
        assert path.exists(), f"Agent {agent_name} config not found at {path}"
    
    @pytest.mark.parametrize("agent_name,folder_name", [
        ("UtilitiesConcierge", "utilities_concierge"),
        ("BillingAgent", "billing_agent"),
        ("OutageAgent", "outage_agent"),
        ("ServiceAgent", "service_agent"),
        ("UsageAgent", "usage_agent"),
    ])
    def test_agent_prompt_exists(self, agent_name: str, folder_name: str):
        """Verify each agent has a prompt template file."""
        path = AGENTSTORE_PATH / folder_name / "prompt.jinja"
        assert path.exists(), f"Agent {agent_name} prompt not found at {path}"
    
    def test_all_agents_have_required_fields(self, agent_configs):
        """Verify all agents have required configuration fields."""
        required_fields = {"name", "description"}
        
        for agent_name, config in agent_configs.items():
            for field in required_fields:
                assert field in config, f"Agent {agent_name} missing required field: {field}"
    
    def test_all_agents_have_tools_defined(self, agent_configs):
        """Verify all agents define their tools."""
        for agent_name, config in agent_configs.items():
            assert "tools" in config, f"Agent {agent_name} has no tools defined"
            assert len(config["tools"]) > 0, f"Agent {agent_name} has empty tools list"
    
    def test_all_agents_have_voice_config(self, agent_configs):
        """Verify all agents have voice configuration for TTS."""
        for agent_name, config in agent_configs.items():
            assert "voice" in config, f"Agent {agent_name} missing voice config"
            assert "name" in config["voice"], f"Agent {agent_name} missing voice name"


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestUtilitiesToolRegistration:
    """Tests verifying all tools used by utilities agents are registered."""
    
    def test_utilities_tools_module_imports(self):
        """Verify utilities tools module imports without error."""
        try:
            from apps.artagent.backend.registries.toolstore.utilities import utilities
            from apps.artagent.backend.registries.toolstore.utilities import handoffs
        except ImportError as e:
            pytest.fail(f"Failed to import utilities tools: {e}")
    
    def test_core_utilities_tools_registered(self, tool_registry):
        """Verify core utilities tools are registered."""
        expected_tools = [
            "get_current_bill",
            "get_bill_breakdown",
            "process_payment",
            "setup_payment_plan",
            "check_outage_status",
            "report_outage",
            "report_downed_wire",
            "transfer_service",
            "get_usage_history",
            "get_efficiency_tips",
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tool_registry, f"Tool {tool_name} not registered"
    
    def test_handoff_tools_registered(self, tool_registry):
        """Verify all handoff tools are registered."""
        for tool_name in UTILITIES_HANDOFF_TOOLS:
            assert tool_name in tool_registry, f"Handoff tool {tool_name} not registered"
    
    def test_handoff_tools_marked_as_handoff(self, tool_registry):
        """Verify handoff tools are marked with is_handoff=True."""
        for tool_name in UTILITIES_HANDOFF_TOOLS:
            if tool_name in tool_registry:
                defn = tool_registry[tool_name]
                assert defn.is_handoff, f"Tool {tool_name} not marked as handoff"
    
    def test_agent_tools_exist_in_registry(self, agent_configs, tool_registry):
        """Verify all tools referenced by agents exist in registry."""
        missing_tools = []
        
        for agent_name, config in agent_configs.items():
            agent_tools = config.get("tools", [])
            for tool_name in agent_tools:
                if tool_name not in tool_registry:
                    missing_tools.append(f"{agent_name}: {tool_name}")
        
        if missing_tools:
            pytest.fail(
                f"The following tools are referenced by agents but not registered:\n"
                + "\n".join(f"  - {t}" for t in missing_tools)
            )


# ═══════════════════════════════════════════════════════════════════════════════
# HANDOFF CONNECTIVITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestUtilitiesHandoffConnectivity:
    """Tests verifying handoff routing between agents works correctly."""
    
    def test_concierge_can_handoff_to_all_specialists(self, utilities_orchestration):
        """Verify concierge has routes to all specialist agents."""
        handoffs = utilities_orchestration.get("handoffs", [])
        concierge_targets = {
            h["to"] for h in handoffs if h.get("from") == "UtilitiesConcierge"
        }
        
        expected_targets = {"BillingAgent", "OutageAgent", "ServiceAgent", "UsageAgent"}
        for target in expected_targets:
            assert target in concierge_targets, f"Concierge cannot handoff to {target}"
    
    def test_all_specialists_can_return_to_concierge(self, utilities_orchestration):
        """Verify all specialist agents can handoff back to concierge."""
        handoffs = utilities_orchestration.get("handoffs", [])
        
        specialists = ["BillingAgent", "OutageAgent", "ServiceAgent", "UsageAgent"]
        for specialist in specialists:
            can_return = any(
                h.get("from") == specialist and h.get("to") == "UtilitiesConcierge"
                for h in handoffs
            )
            assert can_return, f"{specialist} cannot handoff back to UtilitiesConcierge"
    
    def test_outage_agent_uses_discrete_handoff(self, utilities_orchestration):
        """Verify outage handoffs are discrete (urgent, no greeting delay)."""
        handoffs = utilities_orchestration.get("handoffs", [])
        
        outage_handoffs = [
            h for h in handoffs 
            if h.get("to") == "OutageAgent"
        ]
        
        for handoff in outage_handoffs:
            assert handoff.get("type") == "discrete", (
                f"Handoff to OutageAgent should be discrete for urgency"
            )
    
    @pytest.mark.asyncio
    async def test_handoff_tool_execution_returns_handoff_signal(self, tool_registry):
        """Verify handoff tool executors return correct handoff signals."""
        from apps.artagent.backend.registries.toolstore.registry import execute_tool
        
        # Test billing agent handoff
        result = await execute_tool("handoff_billing_agent", {
            "account_number": "12345",
            "reason": "payment plan request",
        })
        
        assert result.get("handoff") is True
        assert result.get("target_agent") == "BillingAgent"
    
    @pytest.mark.asyncio
    async def test_outage_handoff_returns_discrete_type(self, tool_registry):
        """Verify outage handoff returns discrete type for urgent handling."""
        from apps.artagent.backend.registries.toolstore.registry import execute_tool
        
        result = await execute_tool("handoff_outage_agent", {
            "outage_type": "electric",
            "is_emergency": True,
        })
        
        assert result.get("handoff") is True
        assert result.get("target_agent") == "OutageAgent"
        assert result.get("handoff_type") == "discrete"


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO LOADER INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestUtilitiesScenarioLoader:
    """Tests verifying the scenario loader correctly processes utilities scenario."""
    
    def test_scenario_loader_can_load_utilities(self):
        """Verify scenario loader can load utilities scenario."""
        from apps.artagent.backend.registries.scenariostore.loader import (
            load_scenario,
        )
        
        scenario = load_scenario("utilities")
        assert scenario is not None
        assert scenario.name == "utilities"
    
    def test_loaded_scenario_has_agents(self):
        """Verify loaded scenario includes agent configurations."""
        from apps.artagent.backend.registries.scenariostore.loader import (
            load_scenario,
        )
        
        scenario = load_scenario("utilities")
        assert hasattr(scenario, "agents") or hasattr(scenario, "agent_names")
    
    def test_loaded_scenario_has_handoffs(self):
        """Verify loaded scenario includes handoff routes."""
        from apps.artagent.backend.registries.scenariostore.loader import (
            load_scenario,
        )
        
        scenario = load_scenario("utilities")
        assert hasattr(scenario, "handoffs")
        assert len(scenario.handoffs) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# END-TO-END AGENT LOADING TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestUtilitiesAgentLoading:
    """Tests verifying agents can be fully loaded and instantiated."""
    
    @pytest.fixture
    def all_agents(self):
        """Load all agents using discover_agents."""
        from apps.artagent.backend.registries.agentstore.loader import discover_agents
        return discover_agents()
    
    def _get_agent(self, agents: dict, name: str):
        """Helper to get agent by name (case-insensitive)."""
        from apps.artagent.backend.src.orchestration.naming import find_agent_by_name
        _, agent = find_agent_by_name(agents, name)
        return agent
    
    def test_unified_agent_can_load_utilities_concierge(self, all_agents):
        """Verify UtilitiesConcierge can be loaded as UnifiedAgent."""
        agent = self._get_agent(all_agents, "UtilitiesConcierge")
        assert agent is not None
        assert agent.name == "UtilitiesConcierge"
    
    def test_unified_agent_can_load_all_utilities_agents(self, all_agents):
        """Verify all utilities agents can be loaded."""
        for agent_name in UTILITIES_AGENTS:
            try:
                agent = self._get_agent(all_agents, agent_name)
                assert agent is not None, f"Agent {agent_name} not found"
                assert agent.name == agent_name
            except Exception as e:
                pytest.fail(f"Failed to load agent {agent_name}: {e}")
    
    def test_loaded_agents_have_tools(self, all_agents):
        """Verify loaded agents have their tools resolved."""
        for agent_name in UTILITIES_AGENTS:
            agent = self._get_agent(all_agents, agent_name)
            assert agent is not None, f"Agent {agent_name} not found"
            assert hasattr(agent, "tool_names") or hasattr(agent, "tools")
    
    def test_agents_can_render_greetings(self, all_agents):
        """Verify agents can render their Jinja greeting templates."""
        for agent_name in UTILITIES_AGENTS:
            agent = self._get_agent(all_agents, agent_name)
            if hasattr(agent, "render_greeting"):
                try:
                    greeting = agent.render_greeting()
                    assert isinstance(greeting, str)
                    assert len(greeting) > 0
                except Exception as e:
                    pytest.fail(f"Agent {agent_name} failed to render greeting: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL EXECUTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestUtilitiesToolExecution:
    """Tests verifying utilities tools execute correctly."""
    
    @pytest.mark.asyncio
    async def test_get_current_bill_executes(self, tool_registry):
        """Verify get_current_bill tool executes and returns expected structure."""
        from apps.artagent.backend.registries.toolstore.registry import execute_tool
        
        result = await execute_tool("get_current_bill", {
            "account_number": "12345"
        })
        
        assert result.get("success") is True
        assert "current_balance" in result
        assert "due_date" in result
    
    @pytest.mark.asyncio
    async def test_check_outage_status_executes(self, tool_registry):
        """Verify check_outage_status tool executes and returns expected structure."""
        from apps.artagent.backend.registries.toolstore.registry import execute_tool
        
        result = await execute_tool("check_outage_status", {
            "service_address": "123 Main St"
        })
        
        assert result.get("success") is True
        assert "outage_active" in result
    
    @pytest.mark.asyncio
    async def test_report_outage_executes(self, tool_registry):
        """Verify report_outage tool executes and returns ticket."""
        from apps.artagent.backend.registries.toolstore.registry import execute_tool
        
        result = await execute_tool("report_outage", {
            "outage_type": "electric"
        })
        
        assert result.get("success") is True
        assert "ticket_id" in result
    
    @pytest.mark.asyncio
    async def test_process_payment_executes(self, tool_registry):
        """Verify process_payment tool executes and returns confirmation."""
        from apps.artagent.backend.registries.toolstore.registry import execute_tool
        
        result = await execute_tool("process_payment", {
            "amount": 150.00,
            "payment_method": "credit_card"
        })
        
        assert result.get("success") is True
        assert "confirmation_number" in result
    
    @pytest.mark.asyncio
    async def test_get_usage_history_executes(self, tool_registry):
        """Verify get_usage_history tool returns usage data."""
        from apps.artagent.backend.registries.toolstore.registry import execute_tool
        
        result = await execute_tool("get_usage_history", {
            "months": 6
        })
        
        assert result.get("success") is True
        assert "history" in result
        assert isinstance(result["history"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# MISSING TOOL INVENTORY (FOR DEVELOPMENT GUIDANCE)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMissingToolInventory:
    """Identify tools referenced by agents but not yet implemented.
    
    This test class helps track which tools need to be implemented
    for the utilities scenario to be fully functional.
    """
    
    def test_list_missing_tools(self, agent_configs, tool_registry):
        """Generate a report of missing tools for development guidance."""
        missing_by_agent = {}
        
        for agent_name, config in agent_configs.items():
            agent_tools = config.get("tools", [])
            missing = [t for t in agent_tools if t not in tool_registry]
            if missing:
                missing_by_agent[agent_name] = missing
        
        if missing_by_agent:
            report_lines = ["Missing tools by agent:"]
            for agent, tools in missing_by_agent.items():
                report_lines.append(f"  {agent}:")
                for tool in tools:
                    report_lines.append(f"    - {tool}")
            
            # This test passes but logs missing tools for awareness
            print("\n" + "\n".join(report_lines))
        
        # Note: This test always passes - it's for reporting purposes
        assert True
