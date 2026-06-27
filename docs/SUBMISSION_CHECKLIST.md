# Kaggle Submission Checklist

Use this checklist before submitting the Kaggle Writeup.

## Required assets

- Kaggle Writeup created and submitted before the deadline.
- Track selected: Agents for Business.
- Cover image uploaded from `assets/cover.svg` or an exported PNG version.
- Video uploaded to YouTube, 5 minutes or less.
- Video attached to the Kaggle Media Gallery.
- Public project link added.

## Public project link

A live deployment is optional. If there is no live demo, use a public GitHub
repository and make sure it includes:

- `README.md` with setup instructions
- `.env.example` without real secrets
- `requirements.txt`
- sample incident files
- rule proposal workflow documented if shown in the video
- Agent Skill folder under `skills/`
- visual diagrams under `assets/`
- tests
- architecture explanation
- pertinent code comments for implementation, design, and behavior decisions
- no real `.env` or API key committed

## Final code checks

Run:

```bash
python -m pytest -q
python -m compileall -q app.py src tests
```

Before publishing, confirm that these are not committed:

- `.env`
- `.venv/`
- `data/*.db`
- `__pycache__/`
- pytest or Streamlit cache files

## Writeup points to cover

- Problem and business value.
- Why agents are useful for this workflow.
- Build/development tools: VS Code, Google Antigravity IDE, Python, Streamlit,
  Google ADK, FastMCP, SQLite, GitHub, and pytest.
- ADK multi-agent architecture.
- MCP tools and read-only design.
- Agent Skill runbook and how it captures reusable triage procedure.
- Security guardrails and human DBA approval.
- Focused implementation comments in ADK, MCP, security, and SQL diagnostic
  code paths.
- Safety-first flow, security boundary, and incident knowledge loop diagrams.
- Expanded SQL Server incident scenarios and limitations.
