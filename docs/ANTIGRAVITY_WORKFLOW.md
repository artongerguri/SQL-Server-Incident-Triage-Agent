# Antigravity Workflow

You can use this project with both VS Code and Google Antigravity IDE.

For the Kaggle video, mention Antigravity as a development/review tool only if
you actually open the repository there and use it for a real review or focused
refinement. The project already demonstrates the required capstone concepts
through ADK, MCP, security, Agent Skills, and deployable GitHub documentation.

## Suggested workflow

1. Open the project in VS Code.
2. Run and test the app.
3. Commit or copy the working version.
4. Open the same folder in Google Antigravity.
5. Ask Antigravity to add or improve a small feature.
6. Test again.
7. Mention this workflow in your Kaggle writeup and video.

## Suggested Antigravity prompts

### Prompt 1: Add a new incident type

```text
Review the SQL Server deadlock triage support.
Suggest one improvement to the verification steps or sample incident.
Keep the change small and testable.
```

### Prompt 2: Improve security

```text
Review this project for safety issues.
Add a note that production logs must be anonymized before being sent to Gemini.
Make sure no SQL commands are executed automatically.
```

### Prompt 3: Improve reporting

```text
Review the Kaggle writeup draft and demo script.
Suggest wording improvements that make the ADK, MCP, and security concepts
clearer for judges.
```

## What to say in the demo

> I built and tested the project in VS Code, then used Google Antigravity IDE to
> review and refine one focused part of the project before the final Kaggle
> submission.
