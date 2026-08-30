"""Synthetic evidence generator.

Turns a small hand-written scenario *spec* into a full :class:`Scenario`: the spec
supplies the incident report, ground truth, the real signal log lines, deploys,
and the shape of each metric; the generator fills in the surrounding noise —
distractor log lines from unrelated services and realistic metric time series —
so the evaluation exercises signal-vs-noise, not a toy.

Generation is deterministic: the RNG is seeded from the scenario id, so
regenerating a scenario produces byte-identical output.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from triage.schema import (
    Deploy,
    Difficulty,
    FailureCategory,
    GroundTruth,
    LogLevel,
    LogLine,
    MetricSeries,
    Scenario,
)

# Distractor log templates keyed loosely by service role. Placeholders are filled
# with plausible random values. These are deliberately mundane — they are noise.
_DISTRACTOR_TEMPLATES: dict[str, list[tuple[LogLevel, str]]] = {
    "api": [
        (LogLevel.INFO, "GET {path} 200 in {ms}ms"),
        (LogLevel.INFO, "POST {path} 201 in {ms}ms"),
        (LogLevel.INFO, "request completed method=GET path={path} status=200"),
        (LogLevel.WARN, "slow request path={path} duration_ms={ms}"),
        (LogLevel.INFO, "health check ok"),
    ],
    "worker": [
        (LogLevel.INFO, "job {job} completed in {ms}ms"),
        (LogLevel.INFO, "processed batch size={n}"),
        (LogLevel.WARN, "job {job} retried attempt=1"),
        (LogLevel.INFO, "queue depth={n}"),
    ],
    "db": [
        (LogLevel.INFO, "checkpoint complete: wrote {n} buffers"),
        (LogLevel.INFO, "connection received: host=10.0.{n}.{m}"),
        (LogLevel.WARN, "long-running query {ms}ms: SELECT ..."),
        (LogLevel.INFO, 'autovacuum: table "events" done'),
    ],
    "cache": [
        (LogLevel.INFO, "SET key=session:{n} ttl=3600"),
        (LogLevel.INFO, "GET key=user:{n} hit"),
        (LogLevel.INFO, "evicted {n} keys (lru)"),
        (LogLevel.WARN, "GET key=user:{n} miss"),
    ],
    "gateway": [
        (LogLevel.INFO, "upstream {svc} 200 {ms}ms"),
        (LogLevel.INFO, "route matched {path} -> {svc}"),
        (LogLevel.WARN, "upstream {svc} slow {ms}ms"),
    ],
}

_PATHS = ["/checkout", "/cart", "/api/v1/orders", "/api/v1/users/me", "/search", "/products"]
_JOBS = ["email.send", "invoice.render", "cache.warm", "report.build", "webhook.deliver"]

_DISTRACTORS_PER_DIFFICULTY: dict[Difficulty, int] = {
    Difficulty.EASY: 12,
    Difficulty.MEDIUM: 28,
    Difficulty.HARD: 50,
}


class SignalLine(BaseModel):
    """A real, load-bearing log line — part of the ground-truth evidence path."""

    model_config = ConfigDict(extra="forbid")

    offset_s: int = Field(description="Seconds from incident_start (may be negative).")
    service: str
    level: LogLevel
    msg: str


class MetricSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    unit: str
    service: str
    baseline: float
    spike: float
    spike_at_offset_s: int = 0
    ramp_s: int = 120


class DeploySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str
    offset_s: int
    commit: str
    summary: str


class DistractorService(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    role: str = "api"


class ScenarioSpec(BaseModel):
    """Hand-written input to the generator. This is what a human reviews."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^scn_\d{3}$")
    category: FailureCategory
    difficulty: Difficulty = Difficulty.MEDIUM
    title: str
    source_url: str
    source_note: str
    incident_report: str

    incident_start: datetime
    detected_offset_s: int = Field(description="Seconds from incident_start until noticed.")
    window_before_s: int = 1800
    window_after_s: int = 900

    primary_service: str
    distractor_services: list[DistractorService] = Field(default_factory=list)

    signal_lines: list[SignalLine] = Field(default_factory=list)
    metrics: list[MetricSpec] = Field(default_factory=list)
    deploys: list[DeploySpec] = Field(default_factory=list)

    ground_truth: GroundTruth


def _fill(template: str, rng: random.Random, primary: str) -> str:
    return template.format(
        path=rng.choice(_PATHS),
        ms=rng.randint(3, 240),
        n=rng.randint(1, 900),
        m=rng.randint(1, 250),
        job=rng.choice(_JOBS),
        svc=primary,
    )


def _distractor_logs(spec: ScenarioSpec, rng: random.Random) -> list[LogLine]:
    start, end = _window(spec)
    span = (end - start).total_seconds()
    count = _DISTRACTORS_PER_DIFFICULTY[spec.difficulty]

    roles = [(spec.primary_service, "api")] + [(d.name, d.role) for d in spec.distractor_services]
    lines: list[LogLine] = []
    for _ in range(count):
        service, role = rng.choice(roles)
        level, template = rng.choice(_DISTRACTOR_TEMPLATES.get(role, _DISTRACTOR_TEMPLATES["api"]))
        ts = start + timedelta(seconds=rng.uniform(0, span))
        msg = _fill(template, rng, spec.primary_service)
        lines.append(LogLine(ts=ts, service=service, level=level, msg=msg))
    return lines


def _signal_logs(spec: ScenarioSpec) -> list[LogLine]:
    return [
        LogLine(
            ts=spec.incident_start + timedelta(seconds=s.offset_s),
            service=s.service,
            level=s.level,
            msg=s.msg,
        )
        for s in spec.signal_lines
    ]


def _window(spec: ScenarioSpec) -> tuple[datetime, datetime]:
    start = spec.incident_start - timedelta(seconds=spec.window_before_s)
    end = (
        spec.incident_start
        + timedelta(seconds=spec.detected_offset_s)
        + timedelta(seconds=spec.window_after_s)
    )
    return start, end


def _metric_series(spec: ScenarioSpec, m: MetricSpec, rng: random.Random) -> MetricSeries:
    start, end = _window(spec)
    step = timedelta(seconds=60)
    spike_at = spec.incident_start + timedelta(seconds=m.spike_at_offset_s)

    points: list[tuple[datetime, float]] = []
    t = start
    while t <= end:
        if t < spike_at:
            value = m.baseline
        elif t < spike_at + timedelta(seconds=m.ramp_s):
            frac = (t - spike_at).total_seconds() / max(m.ramp_s, 1)
            value = m.baseline + frac * (m.spike - m.baseline)
        else:
            value = m.spike
        jitter = rng.uniform(-0.04, 0.04) * (abs(value) or 1.0)
        points.append((t, round(value + jitter, 4)))
        t += step
    return MetricSeries(name=m.name, unit=m.unit, service=m.service, points=points)


def generate_scenario(spec: ScenarioSpec) -> Scenario:
    """Expand a spec into a fully-populated, validated :class:`Scenario`."""
    rng = random.Random(spec.id)

    logs = _signal_logs(spec) + _distractor_logs(spec, rng)
    logs.sort(key=lambda line: line.ts)

    metrics = [_metric_series(spec, m, rng) for m in spec.metrics]

    deploys = [
        Deploy(
            service=d.service,
            ts=spec.incident_start + timedelta(seconds=d.offset_s),
            commit=d.commit,
            summary=d.summary,
        )
        for d in spec.deploys
    ]

    return Scenario(
        id=spec.id,
        category=spec.category,
        difficulty=spec.difficulty,
        title=spec.title,
        source_url=spec.source_url,
        source_note=spec.source_note,
        incident_report=spec.incident_report,
        synthetic_logs=logs,
        synthetic_metrics=metrics,
        synthetic_deploys=deploys,
        ground_truth=spec.ground_truth,
    )
