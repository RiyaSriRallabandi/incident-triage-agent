"""Named agent configurations for ablation studies.

Each variant differs from ``dev-baseline`` in one dimension so a comparison
isolates that dimension's effect.
"""

from __future__ import annotations

from pydantic import BaseModel

ALL_TOOLS = ("search_logs", "query_metrics", "get_recent_deploys", "retrieve_runbook")


class Variant(BaseModel):
    tag: str
    budget: int = 6
    provider: str = "gemini"
    model: str | None = None
    plan_prompt: str = "plan_v1"
    conclude_prompt: str = "conclude_v1"
    tools: tuple[str, ...] = ALL_TOOLS


BASELINE = Variant(tag="dev-baseline")

VARIANTS: dict[str, Variant] = {
    v.tag: v
    for v in [
        BASELINE,
        Variant(tag="conclude-v2", conclude_prompt="conclude_v2"),
        Variant(tag="conclude-v3", conclude_prompt="conclude_v3"),
        Variant(tag="plan-v2", plan_prompt="plan_v2"),
        Variant(tag="budget-10", budget=10),
        Variant(
            tag="no-runbook",
            tools=("search_logs", "query_metrics", "get_recent_deploys"),
        ),
        Variant(
            tag="no-deploys",
            tools=("search_logs", "query_metrics", "retrieve_runbook"),
        ),
    ]
}
