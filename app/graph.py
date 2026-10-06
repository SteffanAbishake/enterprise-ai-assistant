import asyncio
import re
from typing import TypedDict
from fastapi import HTTPException
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer
from langsmith import traceable
from app.models import Answer
from app.security import authorize, SUSPICIOUS
from app.tools import analyze, enterprise_lookup


class State(TypedDict, total=False):
    user: object
    request: object
    history: list
    query: str
    route: str
    rows: list
    warnings: list
    analysis: dict
    answer: dict


def event(node, status, **data):
    get_stream_writer()({"type": "activity", "node": node, "status": status, **data})


def validate_answer(answer, rows):
    parsed = Answer.model_validate(answer)
    ids = {row["id"] for row in rows}
    inline = set(re.findall(r"\[([^\[\]]+)\]", parsed.text))
    if not set(parsed.citations).issubset(ids) or not inline.issubset(set(parsed.citations)):
        raise ValueError("Unverified citations")
    if rows and (not parsed.citations or not inline):
        raise ValueError("Evidence-based response needs citations")
    if SUSPICIOUS.search(parsed.text):
        raise ValueError("Unsafe response")
    return parsed.model_dump()


def extractive(rows):
    if not rows:
        return {"text": "I could not find sufficient authorized evidence for that question.", "citations": []}
    return {"text": "Evidence excerpts (not a generated synthesis):\n\n" + "\n\n".join(
        f"{r['text']} [{r['id']}]" for r in rows[:5]), "citations": [r["id"] for r in rows[:5]]}


def build_graph(settings, retrieval, providers):
    async def supervisor(state):
        message = state["request"].message
        lowered = message.lower()
        route = "research" if any(w in lowered for w in ["summar", "recurring", "compare", "analy", "all outage"]) else "retrieval"
        if any(w in lowered for w in ["service owner", "who owns", "service catalog"]):
            route = "tools"
        if route == "research":
            authorize(state["user"], "analytics")
        if route == "tools":
            authorize(state["user"], "mcp")
        # A bounded previous question helps resolve simple follow-ups without loading documents.
        previous = next((t["content"] for t in reversed(state["history"]) if t["role"] == "user"), "")
        query = message + (" " + previous if re.search(r"\b(it|those|that|these|they)\b", lowered) else "")
        event("supervisor", "routed", route=route, reason="Bounded keyword routing; permissions checked")
        return {"query": query, "route": route, "warnings": []}

    async def retrieve(state):
        event("retrieval", "searching", tool="knowledge_search")
        rows, warnings = await retrieval.search(state["user"], state["request"], state["query"])
        event("retrieval", "complete", sections=len(rows), warnings=warnings)
        return {"rows": rows, "warnings": warnings}

    @traceable(name="recursive_research_batch", run_type="chain")
    async def recursive(user, rows, depth=0):
        event("research", "batch", depth=depth, sections=len(rows))
        if len(rows) <= 3 or depth >= 3:
            counts = await analyze(user, rows)
            return {"counts": counts, "ids": [r["id"] for r in rows]}
        midpoint = len(rows) // 2
        left = await recursive(user, rows[:midpoint], depth + 1)
        right = await recursive(user, rows[midpoint:], depth + 1)
        # Aggregate unique documents again to avoid counting overlapping chunks twice.
        return {"counts": await analyze(user, rows), "ids": left["ids"] + right["ids"]}

    async def research(state):
        event("research", "plan", python_plan="filter_authorized -> search -> split_batches(3) -> count_root_causes -> aggregate",
              scope="At most 12 retrieved sections; not an exhaustive corpus census")
        result = await recursive(state["user"], state["rows"])
        event("research", "complete", analysis=result)
        return {"analysis": result}

    async def tools_node(state):
        event("tools", "calling", tool="enterprise_mcp")
        if not settings.mcp_enabled:
            return {"rows": [], "warnings": ["MCP is disabled; enable MCP_ENABLED for the mock service catalog."]}
        try:
            row = await enterprise_lookup(state["user"], settings.tool_timeout_seconds)
            return {"rows": [row], "warnings": []}
        except Exception:
            return {"rows": [], "warnings": ["Service catalog unavailable; please try again later."]}

    async def response(state):
        event("response", "generating")
        rows = state.get("rows", [])
        warnings = list(state.get("warnings", []))
        answer = extractive(rows)
        if settings.app_mode == "live" and rows:
            try:
                async with asyncio.timeout(settings.tool_timeout_seconds):
                    evidence = {"sections": rows, "analysis": state.get("analysis", {})}
                    answer = await providers.complete(state["request"].message, evidence, state["history"])
            except Exception:
                warnings.append("Language model unavailable; showing evidence excerpts.")
        elif state.get("analysis") and rows:
            answer["text"] += "\n\nRoot-cause counts within the retrieved evidence: " + str(state["analysis"]["counts"])
        return {"answer": answer, "warnings": warnings}

    async def validation(state):
        try:
            answer = validate_answer(state["answer"], state.get("rows", []))
            status = "passed"
        except (ValueError, TypeError):
            answer = extractive(state.get("rows", []))
            status = "replaced_with_evidence"
        event("validation", status, check="Schema, citation IDs and content screening; not semantic proof")
        # Stream only validated output, not unchecked model tokens.
        for word in answer["text"].split(" "):
            get_stream_writer()({"type": "token", "text": word + " "})
            await asyncio.sleep(0)
        get_stream_writer()({"type": "answer", **answer, "warnings": state.get("warnings", []),
                             "sources": state.get("rows", [])})
        return {"answer": answer}

    graph = StateGraph(State)
    for name, function in [("supervisor", supervisor), ("retrieval", retrieve),
                           ("research", research), ("tools", tools_node),
                           ("response", response), ("validation", validation)]:
        graph.add_node(name, function)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", lambda s: "tools" if s["route"] == "tools" else "retrieval")
    graph.add_conditional_edges("retrieval", lambda s: "research" if s["route"] == "research" else "response")
    graph.add_edge("research", "response")
    graph.add_edge("tools", "response")
    graph.add_edge("response", "validation")
    graph.add_edge("validation", END)
    return graph.compile()
