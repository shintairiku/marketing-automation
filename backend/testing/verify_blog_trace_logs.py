# -*- coding: utf-8 -*-
"""
Blog AI trace/log consistency verifier.

Usage:
  cd backend && uv run python testing/verify_blog_trace_logs.py [process_id]
"""

from __future__ import annotations

import sys
from collections import Counter
from typing import Any

from app.common.database import supabase


def fetch_all_rows(query_builder: Any, page_size: int = 1000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        result = query_builder.range(offset, offset + page_size - 1).execute()
        chunk = result.data or []
        rows.extend(chunk)
        if len(chunk) < page_size:
            break
        offset += page_size
    return rows


def main() -> int:
    process_id: str | None = sys.argv[1] if len(sys.argv) > 1 else None

    if not process_id:
        state_resp = (
            supabase.table("blog_generation_state")
            .select("id")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        states = state_resp.data or []
        if not states:
            print("ERROR: blog_generation_state has no rows")
            return 1
        process_id = states[0]["id"]

    state_resp = (
        supabase.table("blog_generation_state")
        .select("id,user_id,status,created_at,updated_at,blog_context,response_id")
        .eq("id", process_id)
        .maybe_single()
        .execute()
    )
    state = state_resp.data
    if not state:
        print(f"ERROR: process not found: {process_id}")
        return 1

    sessions_resp = (
        supabase.table("agent_log_sessions")
        .select("id,status,created_at,completed_at,session_metadata")
        .eq("article_uuid", process_id)
        .order("created_at", desc=True)
        .execute()
    )
    sessions = sessions_resp.data or []
    if not sessions:
        print(f"ERROR: no agent_log_sessions for process: {process_id}")
        return 1
    session = sessions[0]
    session_id = session["id"]

    executions = (
        supabase.table("agent_execution_logs")
        .select(
            "id,status,input_tokens,output_tokens,cache_tokens,reasoning_tokens,duration_ms"
        )
        .eq("session_id", session_id)
        .order("step_number")
        .order("sub_step_number")
        .execute()
        .data
        or []
    )
    execution_ids = [row["id"] for row in executions]

    llm_calls = []
    tool_calls = []
    if execution_ids:
        llm_calls = (
            supabase.table("llm_call_logs")
            .select(
                "id,execution_id,call_sequence,model_name,prompt_tokens,completion_tokens,total_tokens,cached_tokens,reasoning_tokens,api_response_id,called_at"
            )
            .in_("execution_id", execution_ids)
            .order("called_at")
            .order("call_sequence")
            .execute()
            .data
            or []
        )
        tool_calls = (
            supabase.table("tool_call_logs")
            .select("id,execution_id,call_sequence,tool_name,status,tool_metadata")
            .in_("execution_id", execution_ids)
            .order("called_at")
            .order("call_sequence")
            .execute()
            .data
            or []
        )

    trace_events: list[dict[str, Any]] = []
    trace_error: str | None = None
    try:
        trace_events = fetch_all_rows(
            supabase.table("blog_agent_trace_events")
            .select(
                "event_sequence,event_type,source,tool_call_id,response_id,tool_name,model_name,total_tokens"
            )
            .eq("session_id", session_id)
            .order("event_sequence")
        )
    except Exception as exc:  # table not migrated etc
        trace_error = str(exc)

    print("=== BLOG TRACE VERIFICATION ===")
    print("process_id:", process_id)
    print("session_id:", session_id)
    print("state.status:", state.get("status"))
    print("session.status:", session.get("status"))
    print("workflow_type:", (session.get("session_metadata") or {}).get("workflow_type"))
    print("state.response_id:", state.get("response_id"))
    print(
        "has_conversation_history:",
        isinstance((state.get("blog_context") or {}).get("conversation_history"), list),
    )

    exec_input = sum(int(e.get("input_tokens") or 0) for e in executions)
    exec_output = sum(int(e.get("output_tokens") or 0) for e in executions)
    exec_cache = sum(int(e.get("cache_tokens") or 0) for e in executions)
    exec_reason = sum(int(e.get("reasoning_tokens") or 0) for e in executions)

    llm_input = sum(int(e.get("prompt_tokens") or 0) for e in llm_calls)
    llm_output = sum(int(e.get("completion_tokens") or 0) for e in llm_calls)
    llm_total = sum(int(e.get("total_tokens") or 0) for e in llm_calls)
    llm_cache = sum(int(e.get("cached_tokens") or 0) for e in llm_calls)
    llm_reason = sum(int(e.get("reasoning_tokens") or 0) for e in llm_calls)

    print("execution_count:", len(executions))
    print("llm_call_count:", len(llm_calls))
    print("tool_call_count:", len(tool_calls))
    print("execution_token_sums:", {
        "input": exec_input,
        "output": exec_output,
        "cache": exec_cache,
        "reasoning": exec_reason,
    })
    print("llm_token_sums:", {
        "input": llm_input,
        "output": llm_output,
        "total": llm_total,
        "cache": llm_cache,
        "reasoning": llm_reason,
    })

    if trace_error:
        print("trace_table_ok: False")
        print("trace_table_error:", trace_error)
    else:
        print("trace_table_ok: True")
        print("trace_event_count:", len(trace_events))
        print("trace_event_type_counts:", dict(Counter(e.get("event_type") for e in trace_events)))
        tool_output_events = [
            e for e in trace_events if e.get("event_type") == "tool_output"
        ]
        print(
            "trace_tool_output_missing_call_id:",
            sum(1 for e in tool_output_events if not e.get("tool_call_id")),
        )
        print(
            "trace_tool_output_missing_tool_name:",
            sum(1 for e in tool_output_events if not e.get("tool_name")),
        )

    # consistency checks
    checks: list[tuple[str, bool, str]] = []
    checks.append(
        (
            "workflow_type_is_blog_generation",
            (session.get("session_metadata") or {}).get("workflow_type") == "blog_generation",
            "session_metadata.workflow_type must be blog_generation",
        )
    )
    checks.append(("has_execution_logs", len(executions) > 0, "execution logs should exist"))
    checks.append(("has_llm_call_logs", len(llm_calls) > 0, "llm_call_logs should exist"))
    checks.append(("has_tool_call_logs", len(tool_calls) > 0, "tool_call_logs should exist"))
    if state.get("status") == "completed":
        checks.append(
            (
                "session_status_completed_if_state_completed",
                session.get("status") == "completed",
                "blog_generation_state.status=completed のとき session.status も completed",
            )
        )
    checks.append(
        (
            "execution_vs_llm_input_output_equal",
            exec_input == llm_input and exec_output == llm_output,
            "execution token sums should match llm_call_logs sums",
        )
    )

    if not trace_error:
        llm_response_ids = [r.get("api_response_id") for r in llm_calls if r.get("api_response_id")]
        trace_response_ids = [
            r.get("response_id")
            for r in trace_events
            if r.get("event_type") == "response.completed" and r.get("response_id")
        ]
        checks.append(
            (
                "llm_response_ids_present_in_trace_completed",
                all(rid in trace_response_ids for rid in llm_response_ids),
                "every llm_call_logs.api_response_id should appear in trace response.completed",
            )
        )

        tool_started = sum(1 for r in trace_events if r.get("event_type") == "tool_called")
        checks.append(
            (
                "tool_called_count_matches_tool_call_logs",
                tool_started == len(tool_calls),
                "tool_called events should match tool_call_logs count",
            )
        )
        tool_output_events = [r for r in trace_events if r.get("event_type") == "tool_output"]
        checks.append(
            (
                "tool_output_events_have_call_id",
                all(r.get("tool_call_id") for r in tool_output_events),
                "tool_output events should have tool_call_id",
            )
        )

    print("\n=== CHECKS ===")
    failed = 0
    for name, ok, detail in checks:
        print(f"[{ 'OK' if ok else 'NG' }] {name}: {detail}")
        if not ok:
            failed += 1

    print("\nVERDICT:", "OK" if failed == 0 else f"WARN ({failed} checks failed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
