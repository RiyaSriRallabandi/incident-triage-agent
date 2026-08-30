from triage.config import Settings
from triage.dataset import load_scenarios
from triage.tracing import configure_tracing, trace_config, tracing_enabled

SCENARIOS = {s.id: s for s in load_scenarios()}

TRACING_ENV = [
    "LANGCHAIN_TRACING_V2",
    "LANGSMITH_TRACING",
    "LANGCHAIN_API_KEY",
    "LANGSMITH_API_KEY",
    "LANGCHAIN_PROJECT",
    "LANGSMITH_PROJECT",
]


def _clear_env(monkeypatch):
    for name in TRACING_ENV:
        monkeypatch.delenv(name, raising=False)


def test_tracing_disabled_without_key(monkeypatch):
    _clear_env(monkeypatch)
    settings = Settings(_env_file=None, langchain_tracing_v2=True, langchain_api_key="")
    assert tracing_enabled(settings) is False
    assert configure_tracing(settings) is False


def test_tracing_disabled_when_flag_off(monkeypatch):
    _clear_env(monkeypatch)
    settings = Settings(_env_file=None, langchain_tracing_v2=False, langchain_api_key="lsv2_x")
    assert configure_tracing(settings) is False


def test_configure_tracing_sets_all_env_aliases(monkeypatch):
    _clear_env(monkeypatch)
    settings = Settings(
        _env_file=None,
        langchain_tracing_v2=True,
        langchain_api_key="lsv2_secret",
        langchain_project="incident-triage-agent",
    )
    assert configure_tracing(settings) is True

    import os

    assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGCHAIN_API_KEY"] == "lsv2_secret"
    assert os.environ["LANGSMITH_API_KEY"] == "lsv2_secret"
    assert os.environ["LANGCHAIN_PROJECT"] == "incident-triage-agent"


def test_trace_config_carries_filterable_metadata():
    cfg = trace_config(SCENARIOS["scn_004"], budget=6)

    assert cfg["run_name"] == "triage-scn_004"
    assert "ambiguous" in cfg["tags"]
    assert cfg["metadata"]["scenario_id"] == "scn_004"
    assert cfg["metadata"]["tool_call_budget"] == 6
    assert cfg["metadata"]["ground_truth_should_escalate"] is True
