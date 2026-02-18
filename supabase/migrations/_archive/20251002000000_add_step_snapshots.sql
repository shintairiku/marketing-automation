/**
 * STEP SNAPSHOT SYSTEM FOR ARTICLE GENERATION
 *
 * This migration implements step-by-step navigation for article generation processes.
 * Users can return to any previous step and continue from there.
 *
 * Key Features:
 * 1. Snapshot creation at each significant step
 * 2. Full article_context preservation
 * 3. Restoration to any saved step
 * 4. Historical data retention
 * 5. Realtime integration
 */

-- ============================================================================
-- 1. CREATE STEP SNAPSHOTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS article_generation_step_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    process_id UUID NOT NULL REFERENCES generated_articles_state(id) ON DELETE CASCADE,

    -- Step identification
    step_name TEXT NOT NULL,
    step_index INTEGER NOT NULL DEFAULT 1, -- For handling regenerations (same step multiple times)
    step_category TEXT, -- 'autonomous', 'user_input', 'transition', etc.
    step_description TEXT, -- User-friendly description

    -- Snapshot data
    article_context JSONB NOT NULL DEFAULT '{}', -- Full ArticleContext snapshot
    process_metadata JSONB DEFAULT '{}', -- Additional process state

    -- Snapshot metadata
    snapshot_metadata JSONB DEFAULT '{}'::jsonb,
    can_restore BOOLEAN DEFAULT TRUE, -- Whether this snapshot can be restored to

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint: one snapshot per process/step/index combination
    CONSTRAINT unique_process_step_index UNIQUE(process_id, step_name, step_index)
);

-- Add comments for documentation
COMMENT ON TABLE article_generation_step_snapshots IS 'Snapshots of article generation process at each step for navigation';
COMMENT ON COLUMN article_generation_step_snapshots.step_index IS 'Index for handling multiple passes through same step (e.g., regeneration)';
COMMENT ON COLUMN article_generation_step_snapshots.article_context IS 'Complete ArticleContext JSON snapshot';
COMMENT ON COLUMN article_generation_step_snapshots.can_restore IS 'Whether restoration to this step is permitted';
COMMENT ON COLUMN article_generation_step_snapshots.step_category IS 'Step category: autonomous, user_input, transition, terminal';

-- ============================================================================
-- 2. CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_step_snapshots_process_id ON article_generation_step_snapshots(process_id);
CREATE INDEX IF NOT EXISTS idx_step_snapshots_created_at ON article_generation_step_snapshots(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_step_snapshots_step_name ON article_generation_step_snapshots(step_name);
CREATE INDEX IF NOT EXISTS idx_step_snapshots_process_created ON article_generation_step_snapshots(process_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_step_snapshots_can_restore ON article_generation_step_snapshots(can_restore) WHERE can_restore = TRUE;
CREATE INDEX IF NOT EXISTS idx_step_snapshots_category ON article_generation_step_snapshots(step_category);

-- ============================================================================
-- 3. ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE article_generation_step_snapshots ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access snapshots for their own processes
DROP POLICY IF EXISTS "Users can access their own process snapshots" ON article_generation_step_snapshots;
CREATE POLICY "Users can access their own process snapshots" ON article_generation_step_snapshots
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM generated_articles_state
            WHERE id = article_generation_step_snapshots.process_id
                AND user_id = current_setting('request.jwt.claims', true)::json->>'sub'
        )
    );

-- ============================================================================
-- 4. REALTIME PUBLICATION
-- ============================================================================

-- Drop and recreate publication to include new table
DROP PUBLICATION IF EXISTS supabase_realtime;
CREATE PUBLICATION supabase_realtime FOR TABLE
    products,
    prices,
    organizations,
    organization_members,
    invitations,
    article_generation_flows,
    flow_steps,
    generated_articles_state,
    articles,
    process_events,
    background_tasks,
    task_dependencies,
    image_placeholders,
    company_info,
    style_guide_templates,
    agent_log_sessions,
    agent_execution_logs,
    llm_call_logs,
    tool_call_logs,
    workflow_step_logs,
    article_generation_step_snapshots; -- Added

-- Set replica identity for realtime
ALTER TABLE article_generation_step_snapshots REPLICA IDENTITY FULL;

-- ============================================================================
-- 5. HELPER FUNCTIONS
-- ============================================================================

-- Function: Save step snapshot
CREATE OR REPLACE FUNCTION save_step_snapshot(
    p_process_id UUID,
    p_step_name TEXT,
    p_article_context JSONB,
    p_step_description TEXT DEFAULT NULL,
    p_step_category TEXT DEFAULT NULL,
    p_snapshot_metadata JSONB DEFAULT '{}'::jsonb
)
RETURNS UUID AS $$
DECLARE
    v_step_index INTEGER;
    v_snapshot_id UUID;
BEGIN
    -- Get the next index for this step (handles regenerations)
    SELECT COALESCE(MAX(step_index), 0) + 1 INTO v_step_index
    FROM article_generation_step_snapshots
    WHERE process_id = p_process_id AND step_name = p_step_name;

    -- Insert snapshot
    INSERT INTO article_generation_step_snapshots (
        process_id,
        step_name,
        step_index,
        step_category,
        step_description,
        article_context,
        snapshot_metadata,
        can_restore
    ) VALUES (
        p_process_id,
        p_step_name,
        v_step_index,
        p_step_category,
        p_step_description,
        p_article_context,
        p_snapshot_metadata,
        -- Don't allow restoration to start, error, or completed states
        p_step_name NOT IN ('start', 'error', 'completed')
    )
    RETURNING id INTO v_snapshot_id;

    -- Create process event for snapshot creation
    PERFORM create_process_event(
        p_process_id,
        'snapshot_created',
        jsonb_build_object(
            'snapshot_id', v_snapshot_id,
            'step_name', p_step_name,
            'step_index', v_step_index,
            'step_description', p_step_description
        ),
        'step_navigation',
        'system'
    );

    RETURN v_snapshot_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION save_step_snapshot IS 'Create a snapshot of the current step state for later restoration';

-- Function: Get available snapshots for a process
CREATE OR REPLACE FUNCTION get_available_snapshots(
    p_process_id UUID
)
RETURNS TABLE (
    snapshot_id UUID,
    step_name TEXT,
    step_index INTEGER,
    step_category TEXT,
    step_description TEXT,
    created_at TIMESTAMPTZ,
    can_restore BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        article_generation_step_snapshots.id,
        article_generation_step_snapshots.step_name,
        article_generation_step_snapshots.step_index,
        article_generation_step_snapshots.step_category,
        article_generation_step_snapshots.step_description,
        article_generation_step_snapshots.created_at,
        article_generation_step_snapshots.can_restore
    FROM article_generation_step_snapshots
    WHERE article_generation_step_snapshots.process_id = p_process_id
        AND article_generation_step_snapshots.can_restore = TRUE
    ORDER BY article_generation_step_snapshots.created_at ASC; -- Chronological order
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_available_snapshots IS 'Retrieve all restorable snapshots for a process in chronological order';

-- Function: Restore process from snapshot
CREATE OR REPLACE FUNCTION restore_from_snapshot(
    p_snapshot_id UUID
)
RETURNS JSONB AS $$
DECLARE
    v_process_id UUID;
    v_step_name TEXT;
    v_article_context JSONB;
    v_process_metadata JSONB;
    v_current_context JSONB;
BEGIN
    -- Retrieve snapshot data
    SELECT
        process_id,
        step_name,
        article_context,
        process_metadata
    INTO v_process_id, v_step_name, v_article_context, v_process_metadata
    FROM article_generation_step_snapshots
    WHERE id = p_snapshot_id AND can_restore = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Snapshot not found or cannot be restored: %', p_snapshot_id;
    END IF;

    -- Get current context to preserve later data if possible
    SELECT article_context INTO v_current_context
    FROM generated_articles_state
    WHERE id = v_process_id;

    -- Merge contexts: use snapshot as base but preserve certain forward data
    -- This allows users to see what they had selected before, but they can change it
    v_article_context := jsonb_set(
        v_article_context,
        '{_restoration_metadata}',
        jsonb_build_object(
            'restored_from_snapshot', p_snapshot_id,
            'restored_at', NOW(),
            'previous_context_preserved', true
        )
    );

    -- Update process state
    UPDATE generated_articles_state
    SET
        current_step_name = v_step_name,
        article_context = v_article_context,
        status = CASE
            -- If restoring to a user input step, set to waiting for input
            WHEN v_step_name IN ('persona_generated', 'theme_proposed', 'research_plan_generated', 'outline_generated')
            THEN 'user_input_required'::generation_status
            -- Otherwise, set to in_progress
            ELSE 'in_progress'::generation_status
        END,
        is_waiting_for_input = CASE
            WHEN v_step_name IN ('persona_generated', 'theme_proposed', 'research_plan_generated', 'outline_generated')
            THEN TRUE
            ELSE FALSE
        END,
        input_type = CASE
            WHEN v_step_name = 'persona_generated' THEN 'select_persona'
            WHEN v_step_name = 'theme_proposed' THEN 'select_theme'
            WHEN v_step_name = 'research_plan_generated' THEN 'approve_plan'
            WHEN v_step_name = 'outline_generated' THEN 'approve_outline'
            ELSE NULL
        END,
        updated_at = NOW(),
        last_activity_at = NOW()
    WHERE id = v_process_id;

    -- Create process event for restoration
    PERFORM create_process_event(
        v_process_id,
        'step_restored',
        jsonb_build_object(
            'snapshot_id', p_snapshot_id,
            'restored_step', v_step_name,
            'restored_at', NOW()
        ),
        'step_navigation',
        'user_action'
    );

    -- Return restoration result
    RETURN jsonb_build_object(
        'success', true,
        'process_id', v_process_id,
        'step_name', v_step_name,
        'restored_at', NOW()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION restore_from_snapshot IS 'Restore a process to a previous step state from snapshot';

-- Function: Get snapshot details
CREATE OR REPLACE FUNCTION get_snapshot_details(
    p_snapshot_id UUID
)
RETURNS JSONB AS $$
DECLARE
    v_snapshot RECORD;
BEGIN
    SELECT
        id,
        process_id,
        step_name,
        step_index,
        step_category,
        step_description,
        article_context,
        snapshot_metadata,
        can_restore,
        created_at
    INTO v_snapshot
    FROM article_generation_step_snapshots
    WHERE id = p_snapshot_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Snapshot not found: %', p_snapshot_id;
    END IF;

    RETURN to_jsonb(v_snapshot);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_snapshot_details IS 'Get detailed information about a specific snapshot';

-- ============================================================================
-- 6. UTILITY VIEWS
-- ============================================================================

-- View: Latest snapshots per step
CREATE OR REPLACE VIEW latest_step_snapshots AS
SELECT DISTINCT ON (process_id, step_name)
    id,
    process_id,
    step_name,
    step_index,
    step_category,
    step_description,
    created_at,
    can_restore
FROM article_generation_step_snapshots
WHERE can_restore = TRUE
ORDER BY process_id, step_name, step_index DESC, created_at DESC;

COMMENT ON VIEW latest_step_snapshots IS 'Latest restorable snapshot for each step in each process';

-- ============================================================================
-- 7. CLEANUP FUNCTION
-- ============================================================================

-- Function: Clean up old snapshots
CREATE OR REPLACE FUNCTION cleanup_old_snapshots(
    p_days_old INTEGER DEFAULT 30,
    p_keep_count INTEGER DEFAULT 10
)
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER := 0;
BEGIN
    -- Delete old snapshots, keeping the most recent p_keep_count per process
    WITH snapshots_to_keep AS (
        SELECT id
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY process_id ORDER BY created_at DESC) as rn
            FROM article_generation_step_snapshots
        ) ranked
        WHERE rn <= p_keep_count
    ),
    old_snapshots AS (
        SELECT id
        FROM article_generation_step_snapshots
        WHERE created_at < (NOW() - INTERVAL '1 day' * p_days_old)
          AND id NOT IN (SELECT id FROM snapshots_to_keep)
    )
    DELETE FROM article_generation_step_snapshots
    WHERE id IN (SELECT id FROM old_snapshots);

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_snapshots IS 'Clean up old snapshots while preserving recent ones';

-- ============================================================================
-- 8. GRANTS (if needed for service role)
-- ============================================================================

-- Grant necessary permissions to authenticated users
GRANT SELECT ON article_generation_step_snapshots TO authenticated;
GRANT SELECT ON latest_step_snapshots TO authenticated;
