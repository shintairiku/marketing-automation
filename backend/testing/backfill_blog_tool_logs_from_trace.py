# -*- coding: utf-8 -*-
"""
Backfill tool_call_logs and tool_output trace rows from blog_agent_trace_events.

This fixes legacy runs where ToolCallOutputItem.raw_item was dict and call_id/tool_name
were not captured correctly.

Usage:
  cd backend && PYTHONPATH=. uv run python testing/backfill_blog_tool_logs_from_trace.py
  cd backend && PYTHONPATH=. uv run python testing/backfill_blog_tool_logs_from_trace.py --process-id <uuid>
  cd backend && PYTHONPATH=. uv run python testing/backfill_blog_tool_logs_from_trace.py --apply
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from datetime import datetime
from typing import Any

from app.common.database import supabase


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--process-id", type=str, default=None)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.process_id:
        process_ids = [args.process_id]
    else:
        process_ids = [
            row["id"]
            for row in (
                supabase.table("blog_generation_state")
                .select("id")
                .order("created_at", desc=True)
                .limit(20)
                .execute()
                .data
                or []
            )
        ]

    total_trace_updates = 0
    total_tool_updates = 0

    for process_id in process_ids:
        session_row = (
            supabase.table("agent_log_sessions")
            .select("id")
            .eq("article_uuid", process_id)
            .eq("session_metadata->>workflow_type", "blog_generation")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not session_row:
            continue
        session_id = session_row[0]["id"]

        execution_ids = [
            row["id"]
            for row in (
                supabase.table("agent_execution_logs")
                .select("id")
                .eq("session_id", session_id)
                .order("step_number")
                .order("sub_step_number")
                .execute()
                .data
                or []
            )
        ]
        if not execution_ids:
            continue

        trace_rows = fetch_all_rows(
            supabase.table("blog_agent_trace_events")
            .select(
                "id,execution_id,event_sequence,event_type,tool_name,tool_call_id,output_payload,input_payload,event_metadata,created_at"
            )
            .eq("session_id", session_id)
            .order("event_sequence")
        )

        tool_rows = (
            supabase.table("tool_call_logs")
            .select(
                "id,execution_id,call_sequence,tool_name,status,input_parameters,output_data,execution_time_ms,called_at,completed_at,tool_metadata"
            )
            .in_("execution_id", execution_ids)
            .order("called_at")
            .order("call_sequence")
            .execute()
            .data
            or []
        )

        pending_output_by_exec: dict[str, deque[str]] = defaultdict(deque)
        tool_name_by_call_id: dict[str, str] = {}
        output_by_call_id: dict[str, dict[str, Any]] = {}
        fallback_outputs_by_exec: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
        trace_updates: list[tuple[str, dict[str, Any]]] = []

        for ev in trace_rows:
            ex_id = ev.get("execution_id") or "__no_execution__"
            ev_type = ev.get("event_type")

            if ev_type == "tool_called":
                call_id = ev.get("tool_call_id")
                if call_id:
                    if ev.get("tool_name"):
                        tool_name_by_call_id[call_id] = ev.get("tool_name")
                continue

            if ev_type == "response.function_call_arguments.done":
                call_id = ev.get("tool_call_id")
                if call_id:
                    if ev.get("tool_name"):
                        tool_name_by_call_id.setdefault(call_id, ev.get("tool_name"))
                continue

            if (
                ev_type == "response.output_item.done"
                and (ev.get("event_metadata") or {}).get("item_type") == "function_call"
            ):
                call_id = ev.get("tool_call_id")
                if call_id:
                    if call_id not in pending_output_by_exec[ex_id]:
                        pending_output_by_exec[ex_id].append(call_id)
                    if ev.get("tool_name"):
                        tool_name_by_call_id.setdefault(call_id, ev.get("tool_name"))
                continue

            if ev_type == "response.web_search_call.completed":
                call_id = ev.get("tool_call_id") or (ev.get("event_metadata") or {}).get("item_id")
                if call_id:
                    update_payload: dict[str, Any] = {}
                    if ev.get("tool_call_id") != call_id:
                        update_payload["tool_call_id"] = call_id
                    if not ev.get("tool_name"):
                        update_payload["tool_name"] = "web_search"
                    if update_payload:
                        trace_updates.append((ev["id"], update_payload))
                    output_by_call_id[call_id] = ev
                    tool_name_by_call_id.setdefault(call_id, "web_search")
                continue

            if ev_type == "tool_output":
                call_id = ev.get("tool_call_id")
                expected_call_id = (
                    pending_output_by_exec[ex_id].popleft()
                    if pending_output_by_exec[ex_id]
                    else None
                )
                if expected_call_id:
                    call_id = expected_call_id

                if call_id:
                    output_by_call_id[call_id] = ev
                    update_payload: dict[str, Any] = {}
                    if ev.get("tool_call_id") != call_id:
                        update_payload["tool_call_id"] = call_id
                    if not ev.get("tool_name") and tool_name_by_call_id.get(call_id):
                        update_payload["tool_name"] = tool_name_by_call_id[call_id]
                    if update_payload:
                        trace_updates.append((ev["id"], update_payload))
                else:
                    fallback_outputs_by_exec[ex_id].append(ev)

        tool_updates: list[tuple[str, dict[str, Any]]] = []
        for tool in tool_rows:
            ex_id = tool.get("execution_id") or "__no_execution__"
            metadata = tool.get("tool_metadata") or {}
            call_id = metadata.get("call_id")
            output_event = output_by_call_id.get(call_id) if call_id else None
            if not output_event and fallback_outputs_by_exec[ex_id]:
                output_event = fallback_outputs_by_exec[ex_id].popleft()

            if not output_event:
                continue

            output_payload = output_event.get("output_payload") or {}
            output_value = output_payload.get("output", output_payload)
            if not output_value:
                output_value = {
                    "status": "completed",
                    "event_type": output_event.get("event_type"),
                }
            update_payload: dict[str, Any] = {
                "status": "completed",
                "output_data": {"output": output_value},
            }
            if not tool.get("completed_at") and output_event.get("created_at"):
                update_payload["completed_at"] = output_event.get("created_at")
            if tool.get("tool_name") in (None, "", "unknown", "unknown_tool") and call_id:
                if tool_name_by_call_id.get(call_id):
                    update_payload["tool_name"] = tool_name_by_call_id[call_id]

            started_at = parse_dt(tool.get("called_at"))
            finished_at = parse_dt(output_event.get("created_at"))
            if started_at and finished_at and finished_at >= started_at:
                update_payload["execution_time_ms"] = int(
                    (finished_at - started_at).total_seconds() * 1000
                )
            tool_updates.append((tool["id"], update_payload))

        print("=== PROCESS ===")
        print("process_id:", process_id)
        print("session_id:", session_id)
        print("trace_rows:", len(trace_rows))
        print("tool_rows:", len(tool_rows))
        print("trace_updates:", len(trace_updates))
        print("tool_updates:", len(tool_updates))
        print("tool_status_counts_before:", dict(Counter(t.get("status") for t in tool_rows)))

        if args.apply:
            for trace_id, payload in trace_updates:
                supabase.table("blog_agent_trace_events").update(payload).eq("id", trace_id).execute()
            for tool_id, payload in tool_updates:
                supabase.table("tool_call_logs").update(payload).eq("id", tool_id).execute()
            total_trace_updates += len(trace_updates)
            total_tool_updates += len(tool_updates)

    print("=== SUMMARY ===")
    print("mode:", "apply" if args.apply else "dry-run")
    print("total_trace_updates:", total_trace_updates if args.apply else "N/A")
    print("total_tool_updates:", total_tool_updates if args.apply else "N/A")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
