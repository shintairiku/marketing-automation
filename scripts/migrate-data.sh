#!/bin/bash
# =============================================================
# Data Migration Script
# Migrates all active table data from old Supabase to new Supabase.
#
# Usage:
#   ./scripts/migrate-data.sh <old_db_url> <new_db_url>
#
# Example:
#   ./scripts/migrate-data.sh \
#     "postgresql://postgres:[PASSWORD]@db.[OLD_REF].supabase.co:5432/postgres" \
#     "postgresql://postgres:[PASSWORD]@db.[NEW_REF].supabase.co:5432/postgres"
#
# Prerequisites:
#   - psql and pg_dump installed
#   - New DB has baseline migration applied (schema exists)
#   - New DB has seed data applied (plan_tiers, flow template)
# =============================================================

set -euo pipefail

if [ $# -ne 2 ]; then
    echo "Usage: $0 <old_db_url> <new_db_url>"
    exit 1
fi

OLD_DB="$1"
NEW_DB="$2"
DUMP_DIR="/tmp/supabase_migration_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$DUMP_DIR"
echo "=== Data Migration Started ==="
echo "Dump directory: $DUMP_DIR"
echo ""

# Tables in FK dependency order (parent tables first)
TABLES=(
    "plan_tiers"
    "article_generation_flows"
    "flow_steps"
    "organizations"
    "organization_members"
    "invitations"
    "organization_subscriptions"
    "user_subscriptions"
    "company_info"
    "style_guide_templates"
    "wordpress_sites"
    "subscription_events"
    "agent_log_sessions"
    "generated_articles_state"
    "articles"
    "blog_generation_state"
    "images"
    "image_placeholders"
    "article_edit_versions"
    "article_generation_step_snapshots"
    "article_agent_sessions"
    "article_agent_messages"
    "blog_process_events"
    "process_events"
    "background_tasks"
    "usage_tracking"
    "usage_logs"
    "agent_execution_logs"
    "llm_call_logs"
    "tool_call_logs"
    "workflow_step_logs"
)

# Step 1: Export data from each table
echo "=== Step 1: Exporting data from old DB ==="
for table in "${TABLES[@]}"; do
    echo -n "  Exporting $table... "
    pg_dump \
        --data-only \
        --table="public.$table" \
        --no-owner \
        --no-privileges \
        --disable-triggers \
        --column-inserts \
        "$OLD_DB" > "$DUMP_DIR/${table}.sql" 2>/dev/null || true

    rows=$(grep -c "^INSERT" "$DUMP_DIR/${table}.sql" 2>/dev/null || echo "0")
    echo "$rows rows"
done
echo ""

# Step 2: Clear seed data that will be replaced by migration data
echo "=== Step 2: Clearing seed data from new DB ==="
psql "$NEW_DB" -c "
    DELETE FROM flow_steps WHERE flow_id IN (
        SELECT id FROM article_generation_flows WHERE is_template = true AND name = 'Default SEO Article Generation'
    );
    DELETE FROM article_generation_flows WHERE is_template = true AND name = 'Default SEO Article Generation';
    DELETE FROM plan_tiers WHERE id = 'default';
" 2>/dev/null || echo "  (seed data may not exist yet, continuing)"
echo ""

# Step 3: Disable FK checks and import data
echo "=== Step 3: Importing data to new DB ==="
psql "$NEW_DB" -c "SET session_replication_role = 'replica';" 2>/dev/null

ERRORS=0
for table in "${TABLES[@]}"; do
    file="$DUMP_DIR/${table}.sql"
    if [ -s "$file" ]; then
        echo -n "  Importing $table... "
        if psql "$NEW_DB" < "$file" > /dev/null 2>&1; then
            echo "OK"
        else
            echo "ERROR"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "  Skipping $table (no data)"
    fi
done

psql "$NEW_DB" -c "SET session_replication_role = 'origin';" 2>/dev/null
echo ""

# Step 4: Verify row counts
echo "=== Step 4: Verifying row counts ==="
MISMATCHES=0
for table in "${TABLES[@]}"; do
    OLD_COUNT=$(psql -t -A "$OLD_DB" -c "SELECT COUNT(*) FROM public.$table;" 2>/dev/null || echo "ERR")
    NEW_COUNT=$(psql -t -A "$NEW_DB" -c "SELECT COUNT(*) FROM public.$table;" 2>/dev/null || echo "ERR")

    if [ "$OLD_COUNT" = "$NEW_COUNT" ]; then
        echo "  $table: $OLD_COUNT = $NEW_COUNT OK"
    else
        echo "  $table: OLD=$OLD_COUNT NEW=$NEW_COUNT *** MISMATCH ***"
        MISMATCHES=$((MISMATCHES + 1))
    fi
done
echo ""

# Step 5: Reset sequences
echo "=== Step 5: Resetting sequences ==="
psql "$NEW_DB" -c "
    -- Reset all sequences to max value + 1
    DO \$\$
    DECLARE
        r RECORD;
    BEGIN
        FOR r IN (
            SELECT
                pg_get_serial_sequence(quote_ident(schemaname) || '.' || quote_ident(tablename), attname) AS seq,
                quote_ident(schemaname) || '.' || quote_ident(tablename) AS tbl,
                attname
            FROM pg_catalog.pg_attribute a
            JOIN pg_catalog.pg_class c ON a.attrelid = c.oid
            JOIN pg_catalog.pg_tables t ON c.relname = t.tablename
            WHERE schemaname = 'public'
              AND pg_get_serial_sequence(quote_ident(schemaname) || '.' || quote_ident(tablename), attname) IS NOT NULL
        ) LOOP
            EXECUTE format('SELECT setval(%L, COALESCE(MAX(%I), 0) + 1, false) FROM %s', r.seq, r.attname, r.tbl);
            RAISE NOTICE 'Reset sequence % for %.%', r.seq, r.tbl, r.attname;
        END LOOP;
    END \$\$;
" 2>/dev/null
echo "  Done"
echo ""

# Summary
echo "=== Migration Summary ==="
echo "  Tables processed: ${#TABLES[@]}"
echo "  Import errors: $ERRORS"
echo "  Row mismatches: $MISMATCHES"
echo "  Dump files: $DUMP_DIR"

if [ $ERRORS -eq 0 ] && [ $MISMATCHES -eq 0 ]; then
    echo ""
    echo "  Migration completed successfully!"
else
    echo ""
    echo "  WARNING: There were issues. Review the output above."
    exit 1
fi
