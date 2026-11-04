"""Thin, shared wrapper around the Claude Agent SDK.

Every phase agent is the same shape: a system prompt that scopes what this
run is allowed to do, a short list of allowed tools, a working directory,
and a single prompt describing today's job. This module is the one place
that actually talks to `claude_agent_sdk`, so the three phase scripts stay
readable as *policy* (what should this agent do and with what tools) rather
than SDK plumbing.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    McpSdkServerConfig,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from .config import DEFAULT_MAX_TURNS, DEFAULT_MODEL

logger = logging.getLogger("job_search_agent")


async def _run_async(
    prompt: str,
    *,
    system_prompt: str,
    allowed_tools: list[str],
    cwd: Path,
    mcp_servers: dict[str, McpSdkServerConfig] | None = None,
    permission_mode: str = "acceptEdits",
    max_turns: int = DEFAULT_MAX_TURNS,
) -> str:
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        allowed_tools=allowed_tools,
        mcp_servers=mcp_servers or {},
        cwd=str(cwd),
        permission_mode=permission_mode,
        model=DEFAULT_MODEL,
        max_turns=max_turns,
    )

    transcript: list[str] = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)
                    transcript.append(block.text)
                elif isinstance(block, ToolUseBlock):
                    logger.info("tool call: %s(%s)", block.name, _short(block.input))
        elif isinstance(message, ResultMessage):
            cost = getattr(message, "total_cost_usd", None)
            turns = getattr(message, "num_turns", None)
            logger.info("run complete: turns=%s cost_usd=%s", turns, cost)

    return "\n".join(transcript)


def _short(value, limit: int = 200) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def run_agent(
    prompt: str,
    *,
    system_prompt: str,
    allowed_tools: list[str],
    cwd: Path,
    mcp_servers: dict[str, McpSdkServerConfig] | None = None,
    permission_mode: str = "acceptEdits",
    max_turns: int = DEFAULT_MAX_TURNS,
) -> str:
    """Synchronous entrypoint the phase scripts and the CLI call."""
    return asyncio.run(
        _run_async(
            prompt,
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            cwd=cwd,
            mcp_servers=mcp_servers,
            permission_mode=permission_mode,
            max_turns=max_turns,
        )
    )
