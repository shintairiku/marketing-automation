# -*- coding: utf-8 -*-
"""
Cleanup script for noisy Blog AI trace rows.

By default this runs in dry-run mode and only prints counts.

Usage:
  cd backend && PYTHONPATH=. uv run python testing/cleanup_blog_trace_delta_events.py
  cd backend && PYTHONPATH=. uv run python testing/cleanup_blog_trace_delta_events.py --process-id <uuid>
  cd backend && PYTHONPATH=. uv run python testing/cleanup_blog_trace_delta_events.py --apply
"""

from __future__ import annotations

import argparse
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


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[i : i + size] for i in range(0, len(values), size)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--process-id", type=str, default=None)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    query = supabase.table("blog_agent_trace_events").select(
        "id,process_id,session_id,event_type,created_at"
    )
    if args.process_id:
        query = query.eq("process_id", args.process_id)

    rows = fetch_all_rows(query.order("created_at"))
    noisy = [
        row
        for row in rows
        if row.get("event_type") == "keepalive"
        or str(row.get("event_type", "")).endswith(".delta")
    ]

    print("=== BLOG TRACE DELTA CLEANUP ===")
    print("scope.process_id:", args.process_id or "ALL")
    print("total_rows:", len(rows))
    print("noisy_rows:", len(noisy))
    print(
        "noisy_type_counts:",
        dict(Counter(str(row.get("event_type")) for row in noisy)),
    )

    if not args.apply:
        print("mode: dry-run (no deletion)")
        print("hint: pass --apply to delete noisy rows")
        return 0

    noisy_ids = [str(row["id"]) for row in noisy if row.get("id")]
    deleted = 0
    for batch in chunked(noisy_ids, 200):
        supabase.table("blog_agent_trace_events").delete().in_("id", batch).execute()
        deleted += len(batch)

    print("mode: apply")
    print("deleted_rows:", deleted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
