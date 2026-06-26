"""Tests for the top-level incident agent orchestration."""

from src.agent import IncidentTriageAgent
from src.memory import IncidentMemoryStore


def test_external_ai_requires_explicit_approval(monkeypatch):
    """ADK must not run just because an API key is configured."""
    monkeypatch.setattr("src.agent.is_adk_configured", lambda: True)

    def fail_if_called(*_args, **_kwargs):
        # If this fake is called, the approval gate has failed.
        raise AssertionError("ADK must not run without approval")

    monkeypatch.setattr("src.agent.run_adk_analysis", fail_if_called)
    result = IncidentTriageAgent(
        use_adk=True,
        external_ai_approved=False,
    ).analyze("Backup failed: disk full")

    assert "not approved" in result["adk_analysis"]


def test_adk_receives_only_redacted_text(monkeypatch):
    """External AI receives redacted text, never the raw incident content."""
    captured = {}
    monkeypatch.setattr("src.agent.is_adk_configured", lambda: True)

    def fake_adk(redacted_text, local_analysis):
        # Capture the payload that would be sent to the ADK workflow.
        captured["text"] = redacted_text
        captured["category"] = local_analysis["category"]
        return "safe analysis"

    monkeypatch.setattr("src.agent.run_adk_analysis", fake_adk)
    raw = (
        "Database: SecretDb\nServer=prod01;User ID=admin;Password=hunter2\n"
        "Client 10.1.2.3 reports backup failed disk full"
    )
    result = IncidentTriageAgent(
        use_adk=True,
        external_ai_approved=True,
    ).analyze(raw)

    assert result["adk_analysis"] == "safe analysis"
    assert captured["category"] == "Backup / Storage"
    for secret in ["SecretDb", "prod01", "admin", "hunter2", "10.1.2.3"]:
        assert secret not in captured["text"]


def test_agent_memory_is_opt_in():
    """When memory is enabled, stored previews must still be redacted."""
    store = IncidentMemoryStore(":memory:")
    agent = IncidentTriageAgent(
        use_adk=False,
        remember_incident=True,
        memory_store=store,
    )

    result = agent.analyze("Database: PrivateDb\nBackup failed disk full")

    assert result["memory_id"] is not None
    assert "PrivateDb" not in store.recent()[0]["redacted_preview"]
