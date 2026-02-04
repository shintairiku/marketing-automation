# Agent-11: Supabase RLS / DB Security Findings

**Investigation Status: Complete**
**Date: 2026-02-04**
**Severity Summary: Critical:1, High:3, Medium:4, Low:2**

## Investigation Scope

### Files Analyzed
- `shared/supabase/migrations/` (34 migration files)
- `shared/supabase/config.toml`
- `backend/app/common/database.py`
- `frontend/src/libs/supabase/*.ts`

## Critical Findings

### [CRITICAL] RLS-001: 15 Tables Have RLS Enabled But All Policies Deleted

**File:** `shared/supabase/migrations/20260130000003_fix_org_clerk_compat.sql`

**Problem:** The Clerk compatibility migration deleted 31 RLS policies and did not recreate them with Clerk-compatible conditions.

**Affected Tables:**
1. `organizations` - Organization data
2. `organization_members` - Membership records
3. `invitations` - Invitation tokens
4. `organization_subscriptions` - Org-level subscriptions
5. `generated_articles_state` - Article generation state (Realtime enabled)
6. `articles` - Article content
7. `article_generation_flows` - Generation workflow definitions
8. `flow_steps` - Workflow steps
9. `style_guide_templates` - Style templates
10. `images` - Generated/uploaded images
11. `agent_log_sessions` - Agent logging sessions
12. `agent_execution_logs` - Execution logs
13. `llm_call_logs` - LLM API call logs
14. `tool_call_logs` - Tool invocation logs
15. `workflow_step_logs` - Workflow step logs

**Impact:**
- With RLS enabled but no policies, `anon_key` access is completely blocked (all queries return empty)
- Only `service_role_key` can access these tables
- Frontend Realtime subscriptions using `anon_key` cannot receive updates
- Complete dependency on backend for all data access

**Migration Excerpt (policies dropped but not recreated):**
```sql
DROP POLICY IF EXISTS "Organization owners can manage their organizations" ON organizations;
DROP POLICY IF EXISTS "Organization members can view their organizations" ON organizations;
DROP POLICY IF EXISTS "Users can manage their own generation processes" ON generated_articles_state;
-- ... 28 more DROP statements
-- NO CREATE POLICY statements follow
```

## High Severity Findings

### [HIGH] RLS-002: Backend Uses Only service_role_key, Bypassing RLS Entirely

**File:** `backend/app/common/database.py:14-18`

**Code:**
```python
def create_supabase_client() -> Client:
    supabase_client = create_client(
        settings.supabase_url,
        settings.supabase_service_role_key  # Always uses service_role
    )
    return supabase_client
```

**Impact:**
- No Defense in Depth - a single backend bug can expose all user data
- SQL injection vulnerabilities have full database access
- No database-level audit trail of which user accessed what data

### [HIGH] RLS-003: Frontend Uses service_role_key in API Routes

**Files:**
- `frontend/src/libs/supabase/supabase-admin.ts`
- `frontend/src/app/api/articles/generation/create/route.ts:8`
- `frontend/src/app/api/articles/generation/[processId]/route.ts:8`

**Code:**
```typescript
export const supabaseAdminClient = createClient<Database>(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY  // service_role in Next.js API routes
);
```

**Impact:**
- API routes bypass RLS completely
- If authentication check is missing in any route, full database access is possible
- Risk of `SUPABASE_SERVICE_ROLE_KEY` exposure if not properly protected

### [HIGH] RLS-004: Child Table Policies Reference Deleted Parent Table Policies

**Files:**
- `shared/supabase/migrations/20251002000000_add_step_snapshots.sql`
- `shared/supabase/migrations/20251010000000_add_article_edit_versions.sql`

**Example Policy:**
```sql
CREATE POLICY "Users can access their own process snapshots" ON article_generation_step_snapshots
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM generated_articles_state  -- Parent table has no policies!
            WHERE id = article_generation_step_snapshots.process_id
                AND user_id = current_setting('request.jwt.claims', true)::json->>'sub'
        )
    );
```

**Impact:** These policies rely on parent tables that have had their own policies deleted, creating an inconsistent access control model.

## Medium Severity Findings

### [MEDIUM] RLS-005: customers Table Has No Policies (Intentional but Undocumented)

**File:** `shared/supabase/migrations/20240115041359_init.sql:44-45`

**Comment:** "No policies as this is a private table that the user must not have access to."

**Status:** Intentional design but not clearly documented in architecture docs.

### [MEDIUM] RLS-006: usage_tracking/usage_logs Use USING(true) - Allows All Access

**File:** `shared/supabase/migrations/20260202000001_add_usage_limits.sql:109-113`

**Code:**
```sql
CREATE POLICY "Service role full access to usage_tracking" ON usage_tracking FOR ALL USING (true);
CREATE POLICY "Service role full access to usage_logs" ON usage_logs FOR ALL USING (true);
```

**Impact:** Despite the policy name suggesting "service role only", `USING (true)` allows ANY role (including `anon_key`) to access ALL data in these tables. This makes RLS meaningless.

### [MEDIUM] RLS-007: plan_tiers Table Publicly Readable

**File:** `shared/supabase/migrations/20260202000001_add_usage_limits.sql:105-106`

**Code:**
```sql
CREATE POLICY "Anyone can read plan tiers" ON plan_tiers FOR SELECT USING (true);
```

**Impact:** Internal plan names, pricing strategy, and tier configurations are exposed to any user.

### [MEDIUM] RLS-008: Realtime Subscriptions Lack User Isolation

**Problem:** Tables `blog_generation_state` and `generated_articles_state` are added to `supabase_realtime` publication, but their RLS policies were deleted.

**Impact:** Realtime subscribers may receive updates for other users' data if they know the process ID.

## Low Severity Findings

### [LOW] RLS-009: WordPress Credentials Properly Encrypted (Good Implementation)

**File:** `backend/app/domains/blog/services/crypto_service.py`

**Status:** AES-256-GCM encryption with proper nonce handling. Key managed via `CREDENTIAL_ENCRYPTION_KEY` environment variable.

### [LOW] RLS-010: products/prices Tables Publicly Readable (Intentional)

**File:** `shared/supabase/migrations/20240115041359_init.sql`

**Status:** Stripe product/price data is public. No security issue.

## Table-by-Table RLS Status Summary

| Table | RLS Enabled | Policy Status | Service Role Dependent |
|-------|-------------|---------------|------------------------|
| users | Yes | Own data only | Partial |
| customers | Yes | None (intentional) | Full |
| products | Yes | Public read | No |
| prices | Yes | Public read | No |
| subscriptions | Yes | Own data only | Partial |
| organizations | Yes | **DELETED** | Full |
| organization_members | Yes | **DELETED** | Full |
| invitations | Yes | **DELETED** | Full |
| organization_subscriptions | Yes | **DELETED** | Full |
| article_generation_flows | Yes | **DELETED** | Full |
| flow_steps | Yes | **DELETED** | Full |
| generated_articles_state | Yes | **DELETED** | Full |
| articles | Yes | **DELETED** | Full |
| images | Yes | **DELETED** | Full |
| style_guide_templates | Yes | **DELETED** | Full |
| agent_log_sessions | Yes | **DELETED** | Full |
| agent_execution_logs | Yes | **DELETED** | Full |
| llm_call_logs | Yes | **DELETED** | Full |
| tool_call_logs | Yes | **DELETED** | Full |
| workflow_step_logs | Yes | **DELETED** | Full |
| user_subscriptions | Yes | Own data only | Partial |
| subscription_events | Yes | Deny all (service only) | Full |
| wordpress_sites | Yes | Own + service | Partial |
| blog_generation_state | Yes | Own + service | Partial |
| blog_process_events | Yes | Own + service | Partial |
| plan_tiers | Yes | Public read | No |
| usage_tracking | Yes | **USING(true)** | No (broken) |
| usage_logs | Yes | **USING(true)** | No (broken) |
| company_info | Yes | JWT sub check | Partial |
| article_generation_step_snapshots | Yes | Parent reference | Partial |
| article_edit_versions | Yes | Parent reference | Partial |
| article_agent_sessions | Yes | JWT sub check | Partial |
| article_agent_messages | Yes | Parent reference | Partial |

## Recommended Remediation

### Priority 1: Critical
1. **Recreate RLS policies for 15 affected tables** using Clerk-compatible JWT claims
   ```sql
   -- Example: Clerk-compatible policy
   CREATE POLICY "Users can manage own articles" ON articles
     FOR ALL USING (
       user_id = current_setting('request.jwt.claims', true)::json->>'sub'
     );
   ```
   OR explicitly disable RLS if service_role-only access is intended:
   ```sql
   ALTER TABLE organizations DISABLE ROW LEVEL SECURITY;
   ```

### Priority 2: High
2. **Fix usage_tracking/usage_logs policies**
   ```sql
   DROP POLICY "Service role full access to usage_tracking" ON usage_tracking;
   -- Either add proper user filtering or disable RLS
   ```

3. **Review Realtime publication security**
   - Consider removing tables without proper RLS from publication
   - Or implement filtered subscriptions with user-specific channels

### Priority 3: Medium
4. **Minimize service_role_key usage in frontend**
   - Use `anon_key` with proper RLS for user-scoped operations
   - Reserve `service_role_key` for admin operations only

5. **Review plan_tiers exposure**
   - Determine if pricing strategy exposure is acceptable
   - Consider restricting to authenticated users

## Architecture Concerns

The current architecture relies on "backend uses service_role_key for everything, authentication is handled by JWT verification at the application layer."

This approach works but carries risks:

1. **No Defense in Depth:** A single backend bug can expose all data
2. **Reduced SQL Injection Resistance:** service_role_key has full table access
3. **Audit Difficulty:** Cannot track data access at DB level

**Recommendation:** For critical tables (articles, organizations, user_subscriptions), restore RLS policies and use user-context Supabase clients in the backend where possible.
