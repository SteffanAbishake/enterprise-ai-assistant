import asyncio
import json
import sys
from collections import Counter

from langsmith import traceable

from app.security import authorize


@traceable(name="python_analysis", run_type="tool")
async def analyze(user, rows):
    authorize(user, "analytics")

    # Only a fixed operation over validated records. No eval/exec or generated Python execution.
    def count():
        documents = {r["doc_id"]: r for r in rows if r["document_type"] == "incident"}
        return dict(Counter(r["root_cause"] for r in documents.values()))

    return await asyncio.to_thread(count)


@traceable(name="enterprise_mcp", run_type="tool")
async def enterprise_lookup(user, timeout):
    authorize(user, "mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async with asyncio.timeout(timeout):
        async with (
            stdio_client(
                StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "app.mcp_server"],
                )
            ) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            result = await session.call_tool("service_catalog", {"service": "payments"})
            if result.isError:
                raise RuntimeError("MCP tool failed")
            return json.loads(result.content[0].text)
