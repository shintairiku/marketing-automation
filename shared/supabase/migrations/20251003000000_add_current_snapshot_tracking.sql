/**
 * ADD CURRENT SNAPSHOT TRACKING (like git HEAD)
 *
 * This migration adds current_snapshot_id to generated_articles_state
 * to track the current position in the snapshot history (like git HEAD).
 *
 * Key Changes:
 * 1. Add current_snapshot_id column to track current position
 * 2. Modify restore_from_snapshot to NOT create new snapshots on restore
 * 3. Only create new snapshots when actually progressing forward
 * 4. Branch creation happens when moving forward from a restore point
 */

-- ============================================================================
-- 1. ADD CURRENT_SNAPSHOT_ID TO TRACK HEAD
-- ============================================================================

ALTER TABLE generated_articles_state
ADD COLUMN IF NOT EXISTS current_snapshot_id UUID REFERENCES article_generation_step_snapshots(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_generated_articles_current_snapshot
ON generated_articles_state(current_snapshot_id);

COMMENT ON COLUMN generated_articles_state.current_snapshot_id IS 'Current snapshot position (like git HEAD) - shows which snapshot the process is currently at';

-- ============================================================================
-- 2. REWRITE restore_from_snapshot TO NOT CREATE NEW SNAPSHOTS
-- ============================================================================

CREATE OR REPLACE FUNCTION restore_from_snapshot(
    p_snapshot_id UUID,
    p_create_new_branch BOOLEAN DEFAULT FALSE  -- Changed default to FALSE
)
RETURNS JSONB AS $$
DECLARE
    v_process_id UUID;
    v_step_name TEXT;
    v_article_context JSONB;
    v_branch_id UUID;
    v_snapshot_branch_id UUID;
BEGIN
    -- Retrieve snapshot data
    SELECT
        process_id,
        step_name,
        article_context,
        branch_id
    INTO v_process_id, v_step_name, v_article_context, v_snapshot_branch_id
    FROM article_generation_step_snapshots
    WHERE id = p_snapshot_id AND can_restore = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Snapshot not found or cannot be restored: %', p_snapshot_id;
    END IF;

    -- Get current active branch
    SELECT branch_id INTO v_branch_id
    FROM article_generation_step_snapshots
    WHERE process_id = v_process_id
      AND is_active_branch = TRUE
    ORDER BY created_at DESC
    LIMIT 1;

    -- If restore point is on a different branch, switch branches
    IF v_snapshot_branch_id != v_branch_id THEN
        -- Deactivate all branches for this process
        UPDATE article_generation_step_snapshots
        SET is_active_branch = FALSE
        WHERE process_id = v_process_id;

        -- Activate the snapshot's branch
        UPDATE article_generation_step_snapshots
        SET is_active_branch = TRUE
        WHERE process_id = v_process_id
          AND branch_id = v_snapshot_branch_id;

        v_branch_id := v_snapshot_branch_id;
    END IF;

    -- Add restoration metadata to context
    v_article_context := jsonb_set(
        v_article_context,
        '{_restoration_metadata}',
        jsonb_build_object(
            'restored_from_snapshot', p_snapshot_id,
            'restored_at', NOW(),
            'branch_id', v_branch_id
        )
    );

    -- Update process state - NO NEW SNAPSHOT CREATED, just move HEAD
    UPDATE generated_articles_state
    SET
        current_step_name = v_step_name,
        article_context = v_article_context,
        current_snapshot_id = p_snapshot_id,  -- Move HEAD to this snapshot
        status = CASE
            WHEN v_step_name IN ('persona_generated', 'theme_proposed', 'outline_generated')
            THEN 'user_input_required'::generation_status
            ELSE 'in_progress'::generation_status
        END,
        is_waiting_for_input = CASE
            WHEN v_step_name IN ('persona_generated', 'theme_proposed', 'outline_generated')
            THEN TRUE
            ELSE FALSE
        END,
        input_type = CASE
            WHEN v_step_name = 'persona_generated' THEN 'select_persona'
            WHEN v_step_name = 'theme_proposed' THEN 'select_theme'
            WHEN v_step_name = 'outline_generated' THEN 'approve_outline'
            ELSE NULL
        END,
        updated_at = NOW(),
        last_activity_at = NOW()
    WHERE id = v_process_id;

    -- Create process event for restoration
    PERFORM create_process_event(
        v_process_id,
        'snapshot_restored',
        jsonb_build_object(
            'snapshot_id', p_snapshot_id,
            'restored_step', v_step_name,
            'branch_id', v_branch_id,
            'restored_at', NOW()
        )
    );

    RETURN jsonb_build_object(
        'process_id', v_process_id,
        'step_name', v_step_name,
        'branch_id', v_branch_id,
        'created_new_branch', FALSE  -- Never create new branch on restore
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION restore_from_snapshot IS 'Restore process to a snapshot position (like git checkout) - does NOT create new snapshots';

-- ============================================================================
-- 3. UPDATE save_step_snapshot TO HANDLE BRANCH CREATION INTELLIGENTLY
-- ============================================================================

CREATE OR REPLACE FUNCTION save_step_snapshot(
    p_process_id UUID,
    p_step_name TEXT,
    p_article_context JSONB,
    p_step_description TEXT DEFAULT NULL,
    p_step_category TEXT DEFAULT 'autonomous',
    p_snapshot_metadata JSONB DEFAULT '{}'::jsonb,
    p_branch_id UUID DEFAULT NULL  -- Can be passed explicitly
)
RETURNS UUID AS $$
DECLARE
    v_snapshot_id UUID;
    v_step_index INTEGER;
    v_branch_id UUID;
    v_parent_snapshot_id UUID;
    v_branch_name TEXT;
    v_current_snapshot_id UUID;
    v_current_branch_id UUID;
    v_should_create_new_branch BOOLEAN := FALSE;
BEGIN
    -- Get current snapshot and branch info
    SELECT current_snapshot_id INTO v_current_snapshot_id
    FROM generated_articles_state
    WHERE id = p_process_id;

    -- If we have a current snapshot, check if we need to branch
    IF v_current_snapshot_id IS NOT NULL THEN
        -- Get current snapshot's branch
        SELECT branch_id INTO v_current_branch_id
        FROM article_generation_step_snapshots
        WHERE id = v_current_snapshot_id;

        -- Check if current snapshot is the latest in its branch
        SELECT id INTO v_parent_snapshot_id
        FROM article_generation_step_snapshots
        WHERE process_id = p_process_id
          AND branch_id = v_current_branch_id
        ORDER BY created_at DESC
        LIMIT 1;

        -- If current snapshot is NOT the latest, we're creating a branch
        IF v_parent_snapshot_id != v_current_snapshot_id THEN
            v_should_create_new_branch := TRUE;
            v_parent_snapshot_id := v_current_snapshot_id;
        END IF;
    END IF;

    -- Determine branch_id
    IF p_branch_id IS NOT NULL THEN
        -- Explicitly provided branch ID
        v_branch_id := p_branch_id;
        v_branch_name := NULL; -- Will be set by caller
    ELSIF v_should_create_new_branch THEN
        -- Create new branch (diverging from current snapshot)
        v_branch_id := gen_random_uuid();
        v_branch_name := '分岐 ' || TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI');

        -- Deactivate all branches for this process
        UPDATE article_generation_step_snapshots
        SET is_active_branch = FALSE
        WHERE process_id = p_process_id;
    ELSE
        -- Continue on current active branch
        SELECT branch_id, id INTO v_branch_id, v_parent_snapshot_id
        FROM article_generation_step_snapshots
        WHERE process_id = p_process_id
          AND is_active_branch = TRUE
        ORDER BY created_at DESC
        LIMIT 1;

        -- If no active branch found, this is the first snapshot (main branch)
        IF v_branch_id IS NULL THEN
            v_branch_id := gen_random_uuid();
            v_branch_name := 'メインブランチ';
            v_parent_snapshot_id := NULL;
        ELSE
            v_branch_name := (
                SELECT branch_name FROM article_generation_step_snapshots
                WHERE branch_id = v_branch_id
                LIMIT 1
            );
        END IF;
    END IF;

    -- Calculate step_index for this step/branch combination
    SELECT COALESCE(MAX(step_index), 0) + 1 INTO v_step_index
    FROM article_generation_step_snapshots
    WHERE process_id = p_process_id
      AND step_name = p_step_name
      AND branch_id = v_branch_id;

    -- Insert new snapshot
    INSERT INTO article_generation_step_snapshots (
        process_id,
        step_name,
        step_index,
        step_category,
        step_description,
        article_context,
        snapshot_metadata,
        branch_id,
        parent_snapshot_id,
        is_active_branch,
        branch_name,
        can_restore,
        created_at
    ) VALUES (
        p_process_id,
        p_step_name,
        v_step_index,
        p_step_category,
        p_step_description,
        p_article_context,
        p_snapshot_metadata,
        v_branch_id,
        v_parent_snapshot_id,
        TRUE,  -- New snapshot is always on active branch
        COALESCE(v_branch_name, 'メインブランチ'),
        TRUE,
        NOW()
    ) RETURNING id INTO v_snapshot_id;

    -- Update process's current_snapshot_id (move HEAD)
    UPDATE generated_articles_state
    SET current_snapshot_id = v_snapshot_id
    WHERE id = p_process_id;

    RETURN v_snapshot_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 4. UPDATE get_available_snapshots TO INCLUDE CURRENT INDICATOR
-- ============================================================================

DROP FUNCTION IF EXISTS get_available_snapshots(UUID);

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
    can_restore BOOLEAN,
    branch_id UUID,
    branch_name TEXT,
    is_active_branch BOOLEAN,
    parent_snapshot_id UUID,
    is_current BOOLEAN  -- NEW: indicates if this is the current snapshot (HEAD)
) AS $$
DECLARE
    v_current_snapshot_id UUID;
BEGIN
    -- Get current snapshot ID
    SELECT generated_articles_state.current_snapshot_id INTO v_current_snapshot_id
    FROM generated_articles_state
    WHERE generated_articles_state.id = p_process_id;

    RETURN QUERY
    SELECT
        article_generation_step_snapshots.id,
        article_generation_step_snapshots.step_name,
        article_generation_step_snapshots.step_index,
        article_generation_step_snapshots.step_category,
        article_generation_step_snapshots.step_description,
        article_generation_step_snapshots.created_at,
        article_generation_step_snapshots.can_restore,
        article_generation_step_snapshots.branch_id,
        article_generation_step_snapshots.branch_name,
        article_generation_step_snapshots.is_active_branch,
        article_generation_step_snapshots.parent_snapshot_id,
        article_generation_step_snapshots.id = v_current_snapshot_id AS is_current
    FROM article_generation_step_snapshots
    WHERE article_generation_step_snapshots.process_id = p_process_id
        AND article_generation_step_snapshots.can_restore = TRUE
    ORDER BY article_generation_step_snapshots.created_at ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_available_snapshots IS 'Get all snapshots with current position indicator (like git log with HEAD marker)';

-- ============================================================================
-- 5. DROP OBSOLETE create_branch_from_snapshot FUNCTION
-- ============================================================================

-- This function is no longer needed - branching happens automatically in save_step_snapshot
DROP FUNCTION IF EXISTS create_branch_from_snapshot(UUID, TEXT);

COMMENT ON FUNCTION save_step_snapshot IS 'Save snapshot and automatically create branches when diverging from history';
