"""Data contract for incident scenarios and their ground truth.

A scenario is one synthetic incident: an incident report, a bundle of synthetic
evidence (logs, metrics, deploys), and a hand-verified ground-truth answer. The
evidence is fabricated for evaluation; only the failure pattern and root-cause
shape are drawn from the cited real postmortem.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FailureCategory(StrEnum):
    BAD_DEPLOY = "bad_deploy"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_DNS = "network_dns"
    CERT_CONFIG_EXPIRY = "cert_config_expiry"
    DEPENDENCY_FAILURE = "dependency_failure"
    DATABASE_ISSUE = "database_issue"
    AMBIGUOUS = "ambiguous"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class LogLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ts: datetime
    service: str = Field(min_length=1)
    level: LogLevel
    msg: str = Field(min_length=1)


class MetricSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    service: str = Field(min_length=1)
    points: list[tuple[datetime, float]] = Field(min_length=1)

    @field_validator("points")
    @classmethod
    def _points_sorted(cls, points: list[tuple[datetime, float]]) -> list[tuple[datetime, float]]:
        times = [t for t, _ in points]
        if times != sorted(times):
            raise ValueError("metric points must be in chronological order")
        return points


class Deploy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str = Field(min_length=1)
    ts: datetime
    commit: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class GroundTruth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_cause: str = Field(min_length=1)
    evidence_path: list[str] = Field(
        default_factory=list,
        description="Ordered list of the key evidence a correct investigation surfaces.",
    )
    fix: str = Field(min_length=1)
    should_escalate: bool = False

    @model_validator(mode="after")
    def _check_evidence_path(self) -> GroundTruth:
        if not self.should_escalate and not self.evidence_path:
            raise ValueError("evidence_path is required unless should_escalate is true")
        return self


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^scn_\d{3}$")
    category: FailureCategory
    difficulty: Difficulty = Difficulty.MEDIUM
    title: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_note: str = Field(
        min_length=1,
        description="What is drawn from the cited source vs. fabricated for evaluation.",
    )
    incident_report: str = Field(min_length=1)
    synthetic_logs: list[LogLine]
    synthetic_metrics: list[MetricSeries]
    synthetic_deploys: list[Deploy]
    ground_truth: GroundTruth

    @field_validator("synthetic_logs")
    @classmethod
    def _logs_sorted(cls, logs: list[LogLine]) -> list[LogLine]:
        times = [log.ts for log in logs]
        if times != sorted(times):
            raise ValueError("synthetic_logs must be in chronological order")
        return logs

    def services(self) -> set[str]:
        """All service names referenced anywhere in the scenario."""
        names = {log.service for log in self.synthetic_logs}
        names |= {m.service for m in self.synthetic_metrics}
        names |= {d.service for d in self.synthetic_deploys}
        return names

    def time_range(self) -> tuple[datetime, datetime]:
        """Earliest and latest timestamp across all evidence."""
        times: list[datetime] = [log.ts for log in self.synthetic_logs]
        times += [t for m in self.synthetic_metrics for t, _ in m.points]
        times += [d.ts for d in self.synthetic_deploys]
        return min(times), max(times)
