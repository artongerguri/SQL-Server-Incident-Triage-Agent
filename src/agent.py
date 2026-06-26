"""Application-level incident orchestration.

`IncidentTriageAgent` is the central coordinator used by the Streamlit UI and
tests. It always runs deterministic local triage, then optionally adds local
memory and ADK analysis only when the user has enabled those paths.
"""

from __future__ import annotations

import hashlib

from src.adk_workflow import is_adk_configured, run_adk_analysis
from src.memory import IncidentMemoryStore
from src.rules import build_local_analysis
from src.security import scan_and_redact


class IncidentTriageAgent:
    """Coordinate local triage, privacy controls, memory, and optional ADK."""

    def __init__(
        self,
        use_adk: bool = True,
        external_ai_approved: bool = False,
        remember_incident: bool = False,
        memory_store: IncidentMemoryStore | None = None,
    ):
        self.use_adk = use_adk
        self.external_ai_approved = external_ai_approved
        self.remember_incident = remember_incident
        self.memory_store = memory_store

    def analyze(self, incident_text: str) -> dict:
        """Return a complete incident report for UI rendering and tests."""
        # Redaction happens first because every downstream optional feature
        # should work from the safer representation whenever possible.
        privacy = scan_and_redact(incident_text)
        # The local engine can inspect raw text because it runs in-process and
        # never leaves the user's machine.
        local = build_local_analysis(incident_text)

        # The fingerprint is based on redacted text so logs/memory can correlate
        # repeated incidents without storing the original sensitive content.
        result = {
            "input_preview": privacy.redacted_text[:500],
            "incident_fingerprint": hashlib.sha256(
                privacy.redacted_text.encode("utf-8")
            ).hexdigest()[:12],
            **local,
            "privacy": privacy.to_dict(),
            "external_ai_approved": self.external_ai_approved,
            "adk_enabled": self.use_adk and is_adk_configured(),
            "adk_analysis": None,
            "gemini_analysis": None,
            "memory_id": None,
            "similar_incidents": [],
        }

        # Memory is opt-in and stores only redacted previews plus classification
        # metadata. Similarity search is intentionally local and simple.
        if self.remember_incident:
            store = self.memory_store or IncidentMemoryStore()
            result["similar_incidents"] = store.find_similar(
                privacy.redacted_text,
                category=local["category"],
            )
            result["memory_id"] = store.remember(privacy.redacted_text, local)

        # ADK is gated twice: a configured API key is not enough; the user must
        # explicitly approve sharing the redacted incident.
        if self.use_adk and not self.external_ai_approved:
            result["adk_analysis"] = (
                "ADK analysis skipped: external AI sharing was not approved."
            )
        elif self.use_adk and not is_adk_configured():
            result["adk_analysis"] = (
                "ADK analysis skipped because GOOGLE_API_KEY is not configured."
            )
        elif self.use_adk:
            try:
                result["adk_analysis"] = run_adk_analysis(
                    privacy.redacted_text,
                    local,
                )
            except Exception:
                # The local report remains useful even when external AI fails.
                # The UI should not crash during an incident demo or outage.
                result["adk_analysis"] = (
                    "ADK analysis failed; the local triage result remains available."
                )

        # Preserve the existing report field while the UI migrates to ADK terminology.
        result["gemini_analysis"] = result["adk_analysis"]

        return result
