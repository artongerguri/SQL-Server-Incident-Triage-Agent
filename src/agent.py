from __future__ import annotations

import hashlib

from src.adk_workflow import is_adk_configured, run_adk_analysis
from src.memory import IncidentMemoryStore
from src.rules import build_local_analysis
from src.security import scan_and_redact


class IncidentTriageAgent:
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
        privacy = scan_and_redact(incident_text)
        local = build_local_analysis(incident_text)

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

        if self.remember_incident:
            store = self.memory_store or IncidentMemoryStore()
            result["similar_incidents"] = store.find_similar(
                privacy.redacted_text,
                category=local["category"],
            )
            result["memory_id"] = store.remember(privacy.redacted_text, local)

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
                result["adk_analysis"] = (
                    "ADK analysis failed; the local triage result remains available."
                )

        # Preserve the existing report field while the UI migrates to ADK terminology.
        result["gemini_analysis"] = result["adk_analysis"]

        return result
