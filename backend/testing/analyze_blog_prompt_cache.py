# -*- coding: utf-8 -*-
"""
Blog AI prompt cache analyzer.

Usage:
  cd backend && PYTHONPATH=. uv run python testing/analyze_blog_prompt_cache.py
  cd backend && PYTHONPATH=. uv run python testing/analyze_blog_prompt_cache.py <process_id>
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from app.common.database import supabase


@dataclass
class LlmCallRow:
    process_id: str
    session_id: str
    execution_id: str
    call_sequence: int
    called_at: str
    response_id: str | None
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    reasoning_tokens: int
    cost_usd: float
    response_data: dict[str, Any]

    @property
    def cache_hit_rate(self) -> float:
        if self.input_tokens <= 0:
            return 0.0
        return (self.cached_tokens / self.input_tokens) * 100


def fetch_latest_process_ids(limit: int = 5) -> list[str]:
    rows = (
        supabase.table("blog_generation_state")
        .select("id")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )
    return [r["id"] for r in rows if r.get("id")]


def fetch_llm_calls(process_id: str) -> list[LlmCallRow]:
    sessions = (
        supabase.table("agent_log_sessions")
        .select("id,article_uuid")
        .eq("article_uuid", process_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not sessions:
        return []

    session_id = sessions[0]["id"]
    executions = (
        supabase.table("agent_execution_logs")
        .select("id")
        .eq("session_id", session_id)
        .order("step_number")
        .order("sub_step_number")
        .execute()
        .data
        or []
    )
    execution_ids = [e["id"] for e in executions if e.get("id")]
    if not execution_ids:
        return []

    rows = (
        supabase.table("llm_call_logs")
        .select(
            "execution_id,call_sequence,called_at,api_response_id,prompt_tokens,completion_tokens,"
            "cached_tokens,reasoning_tokens,estimated_cost_usd,response_data"
        )
        .in_("execution_id", execution_ids)
        .order("called_at")
        .order("call_sequence")
        .execute()
        .data
        or []
    )

    result: list[LlmCallRow] = []
    for r in rows:
        result.append(
            LlmCallRow(
                process_id=process_id,
                session_id=session_id,
                execution_id=r.get("execution_id") or "",
                call_sequence=int(r.get("call_sequence", 0) or 0),
                called_at=r.get("called_at") or "",
                response_id=r.get("api_response_id"),
                input_tokens=int(r.get("prompt_tokens", 0) or 0),
                output_tokens=int(r.get("completion_tokens", 0) or 0),
                cached_tokens=int(r.get("cached_tokens", 0) or 0),
                reasoning_tokens=int(r.get("reasoning_tokens", 0) or 0),
                cost_usd=float(r.get("estimated_cost_usd", 0) or 0),
                response_data=r.get("response_data") or {},
            )
        )
    return result


def summarize_process(process_id: str, calls: list[LlmCallRow]) -> None:
    total_input = sum(c.input_tokens for c in calls)
    total_cached = sum(c.cached_tokens for c in calls)
    total_output = sum(c.output_tokens for c in calls)
    total_cost = sum(c.cost_usd for c in calls)
    overall_rate = (total_cached / total_input * 100) if total_input > 0 else 0.0
    zero_cache_calls = [c for c in calls if c.cached_tokens == 0]

    print("\n=== PROCESS ===")
    print("process_id:", process_id)
    print("llm_calls:", len(calls))
    print("tokens:", {"input": total_input, "cached": total_cached, "output": total_output})
    print("cache_hit_rate(%):", round(overall_rate, 2))
    print("cost_usd:", round(total_cost, 6))
    print("zero_cache_calls:", len(zero_cache_calls))

    by_exec: dict[str, list[LlmCallRow]] = defaultdict(list)
    for call in calls:
        by_exec[call.execution_id].append(call)

    for execution_id, ex_calls in by_exec.items():
        ex_input = sum(c.input_tokens for c in ex_calls)
        ex_cached = sum(c.cached_tokens for c in ex_calls)
        ex_rate = (ex_cached / ex_input * 100) if ex_input > 0 else 0.0
        print(
            f"  - execution={execution_id[:8]} calls={len(ex_calls)} "
            f"cache_hit_rate={ex_rate:.2f}%"
        )

    print("\nLLM calls:")
    for idx, call in enumerate(calls, 1):
        cfg = call.response_data.get("cache_config") or {}
        print(
            f"{idx:>2}. {call.called_at} "
            f"in={call.input_tokens:>6} cache={call.cached_tokens:>6} "
            f"out={call.output_tokens:>5} reason={call.reasoning_tokens:>4} "
            f"hit={call.cache_hit_rate:>6.2f}% seq={call.call_sequence} "
            f"resp={str(call.response_id or '-')[:32]}"
        )
        if cfg:
            print(
                f"    cache_key={cfg.get('prompt_cache_key')} "
                f"retention={cfg.get('prompt_cache_retention')} "
                f"parallel_tool_calls={cfg.get('parallel_tool_calls')}"
            )


def main() -> int:
    process_ids = [sys.argv[1]] if len(sys.argv) > 1 else fetch_latest_process_ids(5)
    if not process_ids:
        print("no process_ids found")
        return 1

    for process_id in process_ids:
        calls = fetch_llm_calls(process_id)
        if not calls:
            print("\n=== PROCESS ===")
            print("process_id:", process_id)
            print("no llm_call_logs found")
            continue
        summarize_process(process_id, calls)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
