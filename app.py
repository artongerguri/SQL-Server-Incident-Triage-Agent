from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.adk_workflow import is_adk_configured
from src.agent import IncidentTriageAgent
from src.memory import IncidentMemoryStore
from src.report import render_markdown_report


load_dotenv()

APP_DIR = Path(__file__).parent
SAMPLE_DIR = APP_DIR / "sample_incidents"
PLACEHOLDER = (
    "Paste SQL Server error log, SQL Agent job history, replication error, "
    "backup failure, Query Store finding, or DMV output here."
)

st.set_page_config(
    page_title="SQL Server Incident Triage Agent",
    layout="wide",
)


def load_selected_sample() -> None:
    selected = st.session_state.get("selected_sample")
    if selected and selected != "-- Select sample --":
        st.session_state["incident_input"] = (SAMPLE_DIR / selected).read_text(
            encoding="utf-8"
        )


if "incident_input" not in st.session_state:
    st.session_state["incident_input"] = PLACEHOLDER

st.title("SQL Server Incident Triage Agent")
st.caption("ADK multi-agent triage with read-only MCP tools and local fallback")

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

    st.divider()
    st.subheader("Sample incidents")
    sample_files = sorted(SAMPLE_DIR.glob("*.txt"))
    sample_names = ["-- Select sample --"] + [path.name for path in sample_files]
    st.selectbox(
        "Load sample incident",
        sample_names,
        key="selected_sample",
        on_change=load_selected_sample,
    )

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
    st.subheader("Triage Summary")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Severity", result.get("severity", "Unknown"))
    metric_cols[1].metric(
        "Category", result.get("category", "General SQL Server Incident")
    )
    metric_cols[2].metric("Matched rules", len(result.get("matched_rules", [])))

    privacy = result.get("privacy", {})
    findings = privacy.get("findings", [])
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

    st.subheader("Human approval")
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

    with st.expander("Raw JSON result"):
        st.json(result)
