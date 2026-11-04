"""In-process tools exposed to the agent via the Claude Agent SDK's SDK-MCP
server -- i.e. deterministic Python functions the model can call like any
other tool, without round-tripping through a subprocess or a real MCP
server.

Keeping the scorer as a *tool call* rather than letting the model eyeball
each JD and decide Builder/Integrator itself is the point: triage is
deterministic and reproducible, and the model's only job is judgment calls
a keyword match genuinely can't make (is this even a real, open posting).
"""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from .scorer import score_jd


@tool(
    "score_job_description",
    "Score a job description's text on a Builder-PM <-> Integrator-PM spectrum "
    "using a deterministic, weighted keyword match (no model call). Returns "
    "builder_score, integrator_score, lean (Builder PM / Hybrid / Integrator PM / "
    "Unclear), and confidence (High/Medium/Low). Use this instead of eyeballing "
    "a JD yourself -- it's reproducible and the same input always scores the same.",
    {"text": str},
)
async def score_job_description(args: dict[str, Any]) -> dict[str, Any]:
    result = score_jd(args["text"]).to_dict()
    summary = (
        f"Lean: {result['lean']} (confidence: {result['confidence']}). "
        f"Builder score {result['builder_score']}, integrator score {result['integrator_score']}."
    )
    return {"content": [{"type": "text", "text": summary}], "structuredContent": result}


def scoring_server():
    return create_sdk_mcp_server(name="job-search-scoring", tools=[score_job_description])
