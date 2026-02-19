"""
Base Agent for Claude Agent SDK sub-agents.

Provides shared functionality for all clinical sub-agents including
skill loading, structured output, and timeout management.
"""

from typing import Any

import anthropic

from src.python.skills.skill_loader import load_skills
from src.python.utils.config import settings
from src.python.utils.logging import get_logger

logger = get_logger(__name__)


class BaseAgent:
    """
    Base class for all clinical sub-agents.

    Provides:
    - Anthropic client initialization
    - Skill loading into system prompts
    - Structured message handling
    - Timeout and error handling
    """

    agent_name: str = "base_agent"
    agent_description: str = "Base clinical agent"
    required_skills: tuple[str, ...] = ()

    def __init__(self, client: anthropic.Anthropic | None = None):
        """
        Initialize the agent.

        Args:
            client: Optional pre-configured Anthropic client.
                    If None, creates one from settings.
        """
        self.client = client or anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
        )
        self.model = settings.claude_model

        # Load skills into system prompt
        self._system_prompt = self._build_system_prompt()

        logger.info(
            "agent_initialized",
            agent_name=self.agent_name,
            model=self.model,
            skills=self.required_skills,
        )

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt from agent description and loaded skills.

        Returns:
            Complete system prompt string
        """
        sections = [self._get_agent_instructions()]

        if self.required_skills:
            skills_content = load_skills(*self.required_skills)
            sections.append(skills_content)

        return "\n\n---\n\n".join(sections)

    def _get_agent_instructions(self) -> str:
        """
        Get agent-specific instructions. Override in subclasses.

        Returns:
            Agent instruction string
        """
        return f"You are {self.agent_description}."

    def run(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Run the agent with a prompt and optional context.

        Args:
            prompt: The user/orchestrator prompt
            context: Optional context dict (patient data, prior results, etc.)

        Returns:
            Dictionary with 'content' (str) and 'usage' (dict) keys
        """
        messages = self._build_messages(prompt, context)

        logger.info(
            "agent_run_started",
            agent_name=self.agent_name,
            prompt_length=len(prompt),
            has_context=context is not None,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self._system_prompt,
                messages=messages,
            )

            content = response.content[0].text if response.content else ""

            result = {
                "content": content,
                "agent": self.agent_name,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                "stop_reason": response.stop_reason,
            }

            logger.info(
                "agent_run_success",
                agent_name=self.agent_name,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                stop_reason=response.stop_reason,
            )

            return result

        except anthropic.APITimeoutError:
            logger.error(
                "agent_run_timeout",
                agent_name=self.agent_name,
            )
            return {
                "content": "",
                "agent": self.agent_name,
                "error": "Request timed out",
            }

        except anthropic.APIError as e:
            logger.error(
                "agent_run_error",
                agent_name=self.agent_name,
                error=str(e),
            )
            return {
                "content": "",
                "agent": self.agent_name,
                "error": f"API error: {str(e)}",
            }

    def _build_messages(
        self, prompt: str, context: dict[str, Any] | None = None
    ) -> list[dict[str, str]]:
        """
        Build the messages list for the API call.

        Args:
            prompt: The user prompt
            context: Optional context to prepend

        Returns:
            List of message dicts
        """
        user_content = prompt

        if context:
            context_str = "\n".join(f"**{key}**: {value}" for key, value in context.items())
            user_content = f"## Context\n{context_str}\n\n## Task\n{prompt}"

        return [{"role": "user", "content": user_content}]
