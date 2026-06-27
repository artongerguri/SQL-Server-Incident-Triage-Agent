"""Streamlit UI for the SQL Server Incident Triage Agent.

The UI is intentionally thin: it collects incident text, exposes explicit
security controls, calls the orchestration class, and renders the structured
result. Business rules, ADK execution, persistence, and redaction remain in
separate modules so the safety-critical behavior is testable outside Streamlit.
"""

from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.adk_workflow import is_adk_configured
from src.agent import IncidentTriageAgent
from src.memory import IncidentMemoryStore
from src.report import render_markdown_report
from src.rule_proposals import create_rule_proposal, is_actionable_adk_analysis
from src.sample_library import (
    list_sample_names,
    load_sample_text,
)


# Load local `.env` values for demos. `override=True` makes the visible project
# configuration win over any stale shell variables during local testing.
load_dotenv(override=True)

APP_DIR = Path(__file__).parent
SAMPLE_DIR = APP_DIR / "sample_incidents"
PLACEHOLDER = (
    "Paste SQL Server error log, SQL Agent job history, replication error, "
    "backup failure, Query Store finding, or DMV output here."
)

st.set_page_config(
    page_title="SQL Server Incident Triage Agent",
    layout="wide",
    menu_items={},
)

st.markdown(
    """
    <style>
    header,
    header[data-testid="stHeader"],
    [data-testid="stHeader"],
    [data-testid="stAppToolbar"],
    [data-testid="stDeployButton"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }
    .stApp {
        margin-top: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_selected_sample() -> None:
    """Copy the selected sample incident into Streamlit session state."""
    selected = st.session_state.get("selected_sample")
    if selected and selected != "-- Select sample --":
        st.session_state["incident_input"] = load_sample_text(SAMPLE_DIR, selected)


# Seed the text area only once. Streamlit reruns the script on every interaction,
# so state must preserve user edits between reruns.
if "incident_input" not in st.session_state:
    st.session_state["incident_input"] = PLACEHOLDER

st.title("SQL Server Incident Triage Agent")
st.caption("ADK multi-agent triage with read-only MCP tools and local fallback")

# Sidebar controls make every privacy-sensitive feature explicit. The app works
# locally without ADK, without memory, and without live SQL diagnostics.
with st.sidebar:
    st.header("Controls")
    use_adk = st.toggle(
        "Use Google ADK workflow",
        value=True,
        help="Runs triage, safety review, and coordination agents.",
    )

    if is_adk_configured():
        st.success("Google ADK is configured.")
    else:
        st.info("No GOOGLE_API_KEY: local triage remains available.")

    # External AI sharing is disabled unless both conditions are true: the user
    # wants the ADK workflow and an API key is configured.
    external_ai_approved = st.checkbox(
        "Approve sharing redacted text with Gemini",
        value=False,
        disabled=not use_adk or not is_adk_configured(),
        help=(
            "Only the redacted and length-limited incident is shared. "
            "Original text remains local."
        ),
    )
    remember_incident = st.toggle(
        "Store redacted incident in local memory",
        value=False,
        help="Stores a redacted preview, category, severity, and rule names in SQLite.",
    )

    # Samples are demo-safe inputs that exercise the local rule library. Custom
    # samples are listed too, but they are ignored by git.
    st.divider()
    st.subheader("Sample incidents")
    sample_names = ["-- Select sample --"] + list_sample_names(SAMPLE_DIR)
    st.selectbox(
        "Load sample incident",
        sample_names,
        key="selected_sample",
        on_change=load_selected_sample,
    )
    saved_message = st.session_state.pop("rule_proposal_saved_message", None)
    if saved_message:
        st.success(saved_message)

    # Local memory is displayed only as redacted summaries. The original incident
    # text is never retrieved or shown because it is not stored.
    store = IncidentMemoryStore()
    if store.path.exists():
        with st.expander("Recent local memory"):
            for incident in store.recent(limit=5):
                st.caption(
                    f"{incident['severity']} | {incident['category']} | "
                    f"{incident['created_at'][:19]}"
                )

incident_text = st.text_area(
    "Incident input",
    key="incident_input",
    height=280,
    max_chars=25_000,
)

action_col, info_col = st.columns([1, 3])
with action_col:
    analyze = st.button("Analyze Incident", type="primary")
with info_col:
    st.info(
        "The local engine always runs first. External AI and memory require "
        "separate opt-in controls."
    )

# Analysis is triggered by a button instead of running on every keystroke. This
# keeps ADK/API calls user-controlled and avoids repeated work during editing.
if analyze:
    if not incident_text.strip() or incident_text.strip() == PLACEHOLDER:
        st.warning("Paste an incident message or load a sample incident.")
    else:
        with st.spinner("Analyzing incident..."):
            agent = IncidentTriageAgent(
                use_adk=use_adk,
                external_ai_approved=external_ai_approved,
                remember_incident=remember_incident,
            )
            st.session_state["last_result"] = agent.analyze(incident_text)

result = st.session_state.get("last_result")
if result:
    # The summary gives the operator a fast incident classification before the
    # full report details below.
    st.subheader("Triage Summary")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Severity", result.get("severity", "Unknown"))
    metric_cols[1].metric(
        "Category", result.get("category", "General SQL Server Incident")
    )
    metric_cols[2].metric("Matched rules", len(result.get("matched_rules", [])))

    privacy = result.get("privacy", {})
    findings = privacy.get("findings", [])
    # Keep the privacy review visible in the UI so users can audit exactly what
    # would be shared with optional external AI.
    with st.expander("Privacy review", expanded=bool(findings)):
        if findings:
            st.warning(
                "Sensitive-looking values were replaced before external AI access."
            )
            st.json(findings)
        else:
            st.success("No configured sensitive patterns were detected.")
        if privacy.get("truncated"):
            st.warning("Input was truncated to the local safety limit.")
        st.text_area(
            "Redacted preview",
            value=privacy.get("redacted_text", "")[:2000],
            height=160,
            disabled=True,
        )

    st.markdown(render_markdown_report(result))

    if not result.get("matched_rules"):
        st.subheader("Propose a new rule")
        # Unknown incidents can become proposed deterministic rules only after
        # external AI guidance exists and the user approves local draft storage.
        st.caption(
            "No local rule matched this incident. If ADK/Gemini produced useful "
            "guidance and a DBA reviewed it, you can save a local proposed rule "
            "for later developer review. This does not activate the rule."
        )
        adk_analysis = result.get("adk_analysis")
        can_save_rule_proposal = is_actionable_adk_analysis(adk_analysis)
        if not is_adk_configured():
            st.info(
                "Configure GOOGLE_API_KEY and approve external AI sharing if you "
                "want ADK help for unknown incidents. Without an API key, the app "
                "continues with local rules and existing samples."
            )
        elif not can_save_rule_proposal:
            st.info(
                "Run this incident with ADK enabled and external AI sharing "
                "approved. After you verify the ADK guidance, this panel can save "
                "a proposed deterministic rule for manual review."
            )
        else:
            severity_options = ["Critical", "High", "Medium", "Low", "Unknown"]
            current_severity = result.get("severity", "Unknown")
            # Preserve the current local severity when possible, but allow the
            # operator to correct it before saving a rule proposal.
            severity_index = (
                severity_options.index(current_severity)
                if current_severity in severity_options
                else len(severity_options) - 1
            )
            with st.form(f"save_rule_proposal_{result.get('incident_fingerprint')}"):
                proposed_name = st.text_input(
                    "Proposed rule name",
                    value=f"Proposed rule {result.get('incident_fingerprint', 'incident')}",
                    help="Saved as a local JSON proposal under data/rule_proposals/.",
                )
                confirmed_category = st.text_input(
                    "Confirmed category",
                    value="Custom / Unclassified",
                    help="Use the category confirmed by the DBA after reviewing the ADK output.",
                )
                confirmed_severity = st.selectbox(
                    "Confirmed severity",
                    severity_options,
                    index=severity_index,
                )
                candidate_keywords = st.text_area(
                    "Candidate keywords",
                    value="",
                    height=90,
                    help="Comma- or newline-separated keywords that should trigger this rule.",
                )
                operator_notes = st.text_area(
                    "Verified notes / ADK analysis",
                    value=adk_analysis,
                    height=180,
                )
                approve_save = st.checkbox(
                    "I approve saving a local proposed rule for manual review."
                )
                submitted = st.form_submit_button("Save proposed rule")
                if submitted:
                    if not approve_save:
                        st.warning(
                            "Approve local storage before saving the proposed rule."
                        )
                    else:
                        # Rule proposals store reviewed draft metadata. They do
                        # not edit or activate src/rules.py automatically.
                        saved_name = create_rule_proposal(
                            redacted_incident=result.get("privacy", {}).get(
                                "redacted_text", ""
                            ),
                            proposed_name=proposed_name,
                            confirmed_category=confirmed_category,
                            confirmed_severity=confirmed_severity,
                            candidate_keywords=candidate_keywords,
                            operator_notes=operator_notes,
                            source_fingerprint=result.get(
                                "incident_fingerprint", ""
                            ),
                        )
                        st.session_state["rule_proposal_saved_message"] = (
                            f"Saved proposed rule for review: {saved_name}"
                        )
                        st.rerun()

    st.subheader("Human approval")
    # Approval is an audit aid for the demo and workflow. It records what a DBA
    # reviewed, but it never executes a SQL check.
    st.caption(
        "Approval only records which read-only checks a DBA reviewed. "
        "This application does not execute them."
    )
    fingerprint = result.get("incident_fingerprint", "current")
    approval_key = f"approved_sql_{fingerprint}"
    approved_checks = st.multiselect(
        "Reviewed and approved SQL checks",
        options=result.get("sql_checks", []),
        key=approval_key,
    )
    if st.button("Record DBA approval", key=f"record_{fingerprint}"):
        approvals = st.session_state.setdefault("dba_approvals", {})
        approvals[fingerprint] = approved_checks
        st.success(f"Recorded approval for {len(approved_checks)} check(s).")

    if result.get("similar_incidents"):
        with st.expander("Similar incidents from local memory"):
            st.json(result["similar_incidents"])

    # Raw JSON is useful for judges and reviewers because it exposes the exact
    # structured output behind the UI.
    with st.expander("Raw JSON result"):
        st.json(result)
