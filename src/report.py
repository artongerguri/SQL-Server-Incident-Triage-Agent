from __future__ import annotations


def render_list(items: list[str]) -> str:
    return "\n".join([f"- {item}" for item in items])


def render_code_block(items: list[str]) -> str:
    if not items:
        return "No SQL checks suggested."
    return "\n\n".join([f"```sql\n{item}\n```" for item in items])


def render_markdown_report(result: dict) -> str:
    matched_rules = result.get("matched_rules", [])

    matched_text = "No specific rules matched."
    if matched_rules:
        matched_text = "\n".join(
            [
                f"- {rule.get('name')} | keywords: {', '.join(rule.get('matched_keywords', []))}"
                for rule in matched_rules
            ]
        )

    adk_text = result.get("adk_analysis")
    if not adk_text:
        adk_text = "ADK analysis was not requested or not configured."

    return f"""
### Likely cause

{result.get("likely_cause", "Unknown")}

### Verification steps

{render_list(result.get("verification_steps", []))}

### Recommended actions

{render_list(result.get("recommended_actions", []))}

### Safe SQL checks

{render_code_block(result.get("sql_checks", []))}

### Matched rules

{matched_text}

### ADK multi-agent analysis

{adk_text}

### Safety reminder

This tool does not execute SQL commands. Review every query before running it in any real environment.
""".strip()
