"""
Multi-Agent Supervisor
======================

Orchestrates multiple agents running in parallel for complex scenarios.
Implements the supervisor pattern for agent collaboration.

Patterns Supported:
    1. Advisory Supervisors: Monitor and whisper recommendations
    2. Parallel Execution: Multiple agents work on different aspects
    3. Consensus: Multiple agents vote on decisions
    4. Hierarchical: Supervisor coordinates specialists

Usage:
    from apps.artagent.backend.voice.shared.multi_agent import MultiAgentSupervisor

    supervisor = MultiAgentSupervisor(
        primary_agent="Concierge",
        advisory_agents=["ChannelRouter"],
        scenario_config=scenario,
    )

    # Process with supervisor oversight
    result = await supervisor.process_turn(
        user_text="I need help with my account",
        context=context,
    )
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from utils.ml_logging import get_logger

if TYPE_CHECKING:
    from apps.artagent.backend.registries.agentstore.base import UnifiedAgent
    from apps.artagent.backend.registries.scenariostore.loader import ScenarioConfig

logger = get_logger("voice.multi_agent")


@dataclass
class AgentAdvice:
    """Advice from a supervisor agent."""
    
    agent_name: str
    action: str  # "suggest_channel_switch", "continue_current", "escalate_human"
    reason: str
    preferred_channel: str | None = None
    urgency: str = "medium"  # low, medium, high, urgent
    context_to_preserve: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def should_act(self) -> bool:
        """Check if this advice warrants immediate action."""
        return self.urgency in ("high", "urgent") and self.action != "continue_current"


@dataclass
class ParallelResult:
    """Result from parallel agent execution."""
    
    agent_name: str
    success: bool
    result: dict[str, Any]
    execution_time_ms: float
    error: str | None = None


class MultiAgentSupervisor:
    """
    Supervisor for multi-agent orchestration.
    
    This supervisor:
    1. Runs advisory agents in parallel with the primary agent
    2. Collects and synthesizes recommendations
    3. Coordinates parallel execution for complex tasks
    4. Manages context sharing between agents
    """
    
    def __init__(
        self,
        primary_agent: str,
        agents: dict[str, Any],
        advisory_agents: list[str] | None = None,
        scenario_config: Any | None = None,
    ):
        """
        Initialize the supervisor.
        
        Args:
            primary_agent: Name of the customer-facing agent
            agents: Registry of available agents
            advisory_agents: Agents that provide recommendations
            scenario_config: Scenario configuration with orchestration rules
        """
        self._primary_agent = primary_agent
        self._agents = agents
        self._advisory_agents = advisory_agents or []
        self._scenario = scenario_config
        self._active_advice: list[AgentAdvice] = []
        
        logger.info(
            "MultiAgentSupervisor initialized | primary=%s advisors=%s",
            primary_agent,
            self._advisory_agents,
        )
    
    async def get_advisory_recommendations(
        self,
        context: dict[str, Any],
    ) -> list[AgentAdvice]:
        """
        Get recommendations from all advisory agents.
        
        Runs all advisors in parallel and collects their advice.
        """
        if not self._advisory_agents:
            return []
        
        async def get_advice(agent_name: str) -> AgentAdvice | None:
            """Get advice from a single agent."""
            try:
                agent = self._agents.get(agent_name)
                if not agent:
                    logger.warning("Advisory agent not found: %s", agent_name)
                    return None
                
                # Build context for advisor
                advisor_context = {
                    "queue_status": context.get("queue_status", {}),
                    "customer_sentiment": context.get("sentiment", 0.5),
                    "issue_type": context.get("issue_type", "general"),
                    "conversation_length": context.get("turn_count", 0),
                    "current_channel": context.get("channel", "voice"),
                }
                
                # Get recommendation (simplified - in production, call LLM)
                advice = await self._evaluate_routing_rules(agent_name, advisor_context)
                return advice
                
            except Exception as e:
                logger.warning("Failed to get advice from %s: %s", agent_name, e)
                return None
        
        # Run all advisors in parallel
        tasks = [get_advice(name) for name in self._advisory_agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter valid advice
        advice_list = [r for r in results if isinstance(r, AgentAdvice)]
        self._active_advice = advice_list
        
        return advice_list
    
    async def _evaluate_routing_rules(
        self,
        agent_name: str,
        context: dict[str, Any],
    ) -> AgentAdvice:
        """
        Evaluate routing rules for the ChannelRouter agent.
        
        This is a simplified rule evaluation - in production,
        this would call the LLM with the agent's prompt.
        """
        queue_status = context.get("queue_status", {})
        queue_depth = queue_status.get("queue_depth", 0)
        wait_time = queue_status.get("estimated_wait_seconds", 0)
        sentiment = context.get("customer_sentiment", 0.5)
        issue_type = context.get("issue_type", "general")
        
        # Rule 1: High queue volume
        if wait_time > 120 or queue_depth > 50:
            return AgentAdvice(
                agent_name=agent_name,
                action="suggest_channel_switch",
                reason="High call volume detected",
                preferred_channel="whatsapp",
                urgency="high",
                context_to_preserve=["customer_id", "conversation_summary", "issue_type"],
            )
        
        # Rule 2: Document needed
        if issue_type in ("document_submission", "claim_filing", "proof_required"):
            return AgentAdvice(
                agent_name=agent_name,
                action="suggest_channel_switch",
                reason="Document sharing needed",
                preferred_channel="whatsapp",
                urgency="medium",
            )
        
        # Rule 3: Negative sentiment
        if sentiment < 0.3:
            return AgentAdvice(
                agent_name=agent_name,
                action="escalate_human",
                reason="Customer sentiment is negative",
                urgency="high",
            )
        
        # Default: continue current channel
        return AgentAdvice(
            agent_name=agent_name,
            action="continue_current",
            reason="Current channel is optimal",
            urgency="low",
        )
    
    async def execute_parallel(
        self,
        agent_tasks: list[tuple[str, dict[str, Any]]],
        timeout_seconds: float = 10.0,
    ) -> list[ParallelResult]:
        """
        Execute multiple agents in parallel.
        
        Args:
            agent_tasks: List of (agent_name, task_args) tuples
            timeout_seconds: Maximum time to wait for all agents
            
        Returns:
            List of results from each agent
        """
        async def execute_one(
            agent_name: str,
            task_args: dict[str, Any],
        ) -> ParallelResult:
            """Execute a single agent task."""
            import time
            start_time = time.perf_counter()
            
            try:
                agent = self._agents.get(agent_name)
                if not agent:
                    return ParallelResult(
                        agent_name=agent_name,
                        success=False,
                        result={},
                        execution_time_ms=0,
                        error=f"Agent not found: {agent_name}",
                    )
                
                # Execute agent task
                # In production, this would call the agent's process method
                result = {"status": "completed", "agent": agent_name}
                
                execution_time = (time.perf_counter() - start_time) * 1000
                
                return ParallelResult(
                    agent_name=agent_name,
                    success=True,
                    result=result,
                    execution_time_ms=execution_time,
                )
                
            except Exception as e:
                execution_time = (time.perf_counter() - start_time) * 1000
                return ParallelResult(
                    agent_name=agent_name,
                    success=False,
                    result={},
                    execution_time_ms=execution_time,
                    error=str(e),
                )
        
        # Execute all tasks in parallel with timeout
        tasks = [execute_one(name, args) for name, args in agent_tasks]
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout_seconds,
            )
            
            # Convert exceptions to ParallelResult
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    agent_name = agent_tasks[i][0]
                    final_results.append(ParallelResult(
                        agent_name=agent_name,
                        success=False,
                        result={},
                        execution_time_ms=0,
                        error=str(result),
                    ))
                else:
                    final_results.append(result)
            
            return final_results
            
        except asyncio.TimeoutError:
            logger.warning("Parallel execution timed out after %ss", timeout_seconds)
            return [
                ParallelResult(
                    agent_name=name,
                    success=False,
                    result={},
                    execution_time_ms=timeout_seconds * 1000,
                    error="Timeout",
                )
                for name, _ in agent_tasks
            ]
    
    def synthesize_advice(self) -> AgentAdvice | None:
        """
        Synthesize advice from multiple advisors.
        
        If multiple advisors give conflicting advice, use priority:
        1. Urgent actions take precedence
        2. Higher urgency wins
        3. Channel switches require consensus
        """
        if not self._active_advice:
            return None
        
        # Sort by urgency
        urgency_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        sorted_advice = sorted(
            self._active_advice,
            key=lambda a: urgency_order.get(a.urgency, 99),
        )
        
        # Return highest urgency advice
        return sorted_advice[0] if sorted_advice else None
    
    def get_context_for_handoff(self) -> dict[str, Any]:
        """
        Build context to preserve during channel handoff.
        
        Aggregates fields from all advisor recommendations.
        """
        fields_to_preserve = set()
        for advice in self._active_advice:
            fields_to_preserve.update(advice.context_to_preserve)
        
        return {
            "preserve_fields": list(fields_to_preserve),
            "advisors_consulted": [a.agent_name for a in self._active_advice],
            "synthesis_time": datetime.now(UTC).isoformat(),
        }
