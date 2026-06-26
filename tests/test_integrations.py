import asyncio
from pathlib import Path
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.adk_workflow import build_adk_workflow
from src.mcp_server import mcp
from src.security import is_read_only_sql
from src.sqlserver_tools import DIAGNOSTICS, SqlServerReadOnlyClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_adk_workflow_has_three_specialized_agents():
    workflow = build_adk_workflow(model="gemini-2.5-flash")
    assert [node.name for node in workflow.graph.nodes] == [
        "__START__",
        "sql_triage_specialist",
        "safety_reviewer",
        "incident_coordinator",
    ]


def test_mcp_tools_are_marked_read_only():
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    assert names == {
        "analyze_incident",
        "list_sql_diagnostics",
        "run_sql_diagnostic",
        "search_incident_memory",
    }
    assert all(tool.annotations.readOnlyHint for tool in tools)
    assert all(not tool.annotations.destructiveHint for tool in tools)


def test_mcp_stdio_round_trip():
    async def run_client():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "src.mcp_server"],
            cwd=str(PROJECT_ROOT),
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                result = await session.call_tool(
                    "analyze_incident",
                    {"incident_text": "Backup failed because the disk is full"},
                )
        return tools, result

    try:
        tools, result = asyncio.run(run_client())
    except PermissionError:
        pytest.skip("The execution environment blocks Windows named pipes.")
    assert "analyze_incident" in {tool.name for tool in tools.tools}
    assert result.isError is False


def test_all_sql_diagnostics_pass_the_allowlist():
    assert all(is_read_only_sql(item.query) for item in DIAGNOSTICS.values())


def test_live_sql_diagnostics_are_disabled_by_default():
    client = SqlServerReadOnlyClient(enabled=False)
    with pytest.raises(RuntimeError, match="disabled"):
        client.run("database_health")
