#!/usr/bin/env python3
"""
Data Migration Script (Supabase REST API版)
旧Supabaseプロジェクトから新Supabaseプロジェクトへ全データを移行する。

使い方:
  cd backend
  uv run python ../scripts/migrate-data.py

環境変数 (.env or export):
  OLD_SUPABASE_URL        旧プロジェクトURL
  OLD_SUPABASE_SERVICE_KEY 旧プロジェクトのservice_role_key
  NEW_SUPABASE_URL        新プロジェクトURL
  NEW_SUPABASE_SERVICE_KEY 新プロジェクトのservice_role_key
"""

import os
import sys
import json
from datetime import datetime

# Add backend to path for supabase dependency
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from supabase import create_client, Client

# --- Configuration ---

OLD_URL = os.environ.get("OLD_SUPABASE_URL", "")
OLD_KEY = os.environ.get("OLD_SUPABASE_SERVICE_KEY", "")
NEW_URL = os.environ.get("NEW_SUPABASE_URL", "")
NEW_KEY = os.environ.get("NEW_SUPABASE_SERVICE_KEY", "")

# Tables in FK dependency order (parents first)
TABLES = [
    "plan_tiers",
    "article_generation_flows",
    "flow_steps",
    "organizations",
    "organization_members",
    "invitations",
    "organization_subscriptions",
    "user_subscriptions",
    "company_info",
    "style_guide_templates",
    "wordpress_sites",
    "subscription_events",
    "agent_log_sessions",
    "generated_articles_state",
    "articles",
    "blog_generation_state",
    "images",
    "image_placeholders",
    "article_edit_versions",
    "article_generation_step_snapshots",
    "article_agent_sessions",
    "article_agent_messages",
    "blog_process_events",
    "process_events",
    "background_tasks",
    "usage_tracking",
    "usage_logs",
    "agent_execution_logs",
    "llm_call_logs",
    "tool_call_logs",
    "workflow_step_logs",
]

# Tables with non-standard primary keys
PK_MAP = {
    "user_subscriptions": "user_id",
    "organization_members": "organization_id,user_id",
    "organization_subscriptions": "id",  # text PK = stripe subscription ID
}

# Columns to DROP before insert (GENERATED ALWAYS columns)
DROP_COLUMNS = {
    "article_agent_messages": ["sequence"],
}

# Tables that need FK constraints temporarily ignored
# generated_articles_state.current_snapshot_id -> article_generation_step_snapshots
# But snapshots reference generated_articles_state.id (circular!)
# Solution: insert generated_articles_state first WITHOUT current_snapshot_id,
# then insert snapshots, then UPDATE current_snapshot_id
NULLABLE_FK_COLUMNS = {
    "generated_articles_state": ["current_snapshot_id"],
}

# Batch size for inserts (PostgREST limit)
BATCH_SIZE = 500
# Page size for reads
PAGE_SIZE = 1000


def fetch_all_rows(client: Client, table: str) -> list[dict]:
    """Fetch all rows from a table, handling pagination."""
    all_rows = []
    offset = 0

    while True:
        response = (
            client.table(table)
            .select("*")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        rows = response.data
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return all_rows


def get_on_conflict(table: str) -> str:
    """Get the on_conflict column(s) for a table."""
    return PK_MAP.get(table, "id")


def prepare_rows(table: str, rows: list[dict], strip_nullable_fks: bool = False) -> list[dict]:
    """Prepare rows for insert: drop generated columns, optionally strip nullable FK columns."""
    drop_cols = DROP_COLUMNS.get(table, [])
    nullable_fk_cols = NULLABLE_FK_COLUMNS.get(table, []) if strip_nullable_fks else []
    all_drop = set(drop_cols + nullable_fk_cols)

    if not all_drop:
        return rows

    return [{k: v for k, v in row.items() if k not in all_drop} for row in rows]


def insert_rows(client: Client, table: str, rows: list[dict]) -> int:
    """Insert rows in batches. Returns number of rows inserted."""
    if not rows:
        return 0

    on_conflict = get_on_conflict(table)
    inserted = 0

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        try:
            client.table(table).upsert(batch, on_conflict=on_conflict).execute()
            inserted += len(batch)
        except Exception as e:
            print(f"    Batch error on {table}, trying one-by-one: {e}")
            for row in batch:
                try:
                    client.table(table).upsert(row, on_conflict=on_conflict).execute()
                    inserted += 1
                except Exception as e2:
                    print(f"    SKIP row in {table}: {e2}")

    return inserted


def main():
    if not all([OLD_URL, OLD_KEY, NEW_URL, NEW_KEY]):
        print("Error: All 4 environment variables are required:")
        print("  OLD_SUPABASE_URL, OLD_SUPABASE_SERVICE_KEY")
        print("  NEW_SUPABASE_URL, NEW_SUPABASE_SERVICE_KEY")
        print()
        print("Example:")
        print("  export OLD_SUPABASE_URL='https://xxx.supabase.co'")
        print("  export OLD_SUPABASE_SERVICE_KEY='eyJ...'")
        print("  export NEW_SUPABASE_URL='https://yyy.supabase.co'")
        print("  export NEW_SUPABASE_SERVICE_KEY='eyJ...'")
        sys.exit(1)

    print("=" * 60)
    print(f"Data Migration: {OLD_URL} → {NEW_URL}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    old_client = create_client(OLD_URL, OLD_KEY)
    new_client = create_client(NEW_URL, NEW_KEY)

    results = []
    errors = 0
    deferred_updates = {}  # For circular FK resolution

    for table in TABLES:
        print(f"\n--- {table} ---")

        # 1. Fetch from old DB
        try:
            rows = fetch_all_rows(old_client, table)
            print(f"  Read: {len(rows)} rows")
        except Exception as e:
            print(f"  READ ERROR: {e}")
            errors += 1
            results.append((table, "READ_ERROR", 0, 0))
            continue

        if not rows:
            results.append((table, "OK", 0, 0))
            continue

        # 2. Prepare rows (drop generated columns, handle circular FKs)
        strip_fks = table in NULLABLE_FK_COLUMNS
        prepared = prepare_rows(table, rows, strip_nullable_fks=strip_fks)

        # 3. Insert into new DB
        inserted = insert_rows(new_client, table, prepared)
        print(f"  Inserted: {inserted}/{len(rows)}")

        # 4. For tables with stripped nullable FKs, update those columns after dependents are inserted
        if strip_fks:
            deferred_updates[table] = rows  # Save original rows for later update

        # 5. Verify count
        try:
            verify = new_client.table(table).select("*", count="exact", head=True).execute()
            new_count = verify.count
            print(f"  Verify: {new_count} rows in new DB")
            status = "OK" if new_count >= len(rows) else "MISMATCH"
        except Exception as e:
            print(f"  Verify error: {e}")
            new_count = inserted
            status = "UNVERIFIED"

        if inserted < len(rows):
            errors += 1
            status = "PARTIAL"

        results.append((table, status, len(rows), new_count))

    # Deferred FK updates (circular references)
    if deferred_updates:
        print("\n--- Deferred FK Updates ---")
        for table, original_rows in deferred_updates.items():
            fk_cols = NULLABLE_FK_COLUMNS[table]
            on_conflict = get_on_conflict(table)
            updated = 0
            for row in original_rows:
                # Only update rows that have non-null deferred FK values
                update_data = {k: row[k] for k in fk_cols if row.get(k) is not None}
                if not update_data:
                    continue
                pk_col = on_conflict.split(",")[0]
                pk_val = row[pk_col]
                try:
                    new_client.table(table).update(update_data).eq(pk_col, pk_val).execute()
                    updated += 1
                except Exception as e:
                    print(f"    Deferred update skip {table}.{pk_val}: {e}")
            print(f"  {table}: updated {updated} rows with deferred FK columns {fk_cols}")

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"{'Table':<40} {'Status':<12} {'Old':>6} {'New':>6}")
    print("-" * 66)
    for table, status, old_count, new_count in results:
        marker = "  " if status == "OK" else "**"
        print(f"{marker}{table:<38} {status:<12} {old_count:>6} {new_count:>6}")

    print("-" * 66)
    print(f"Total tables: {len(TABLES)}")
    print(f"Errors: {errors}")
    print(f"Finished: {datetime.now().isoformat()}")

    if errors > 0:
        print("\nWARNING: Some tables had issues. Review output above.")
        sys.exit(1)
    else:
        print("\nMigration completed successfully!")


if __name__ == "__main__":
    main()
