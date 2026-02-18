/**
 * BRANCH MANAGEMENT FOR STEP SNAPSHOTS
 *
 * This migration adds branch management capabilities to the snapshot system.
 * Users can:
 * 1. Create branches by restoring to previous snapshots
 * 2. Switch between different branches
 * 3. Return to the main branch
 * 4. All branches preserve their complete state
 *
 * Key Features:
 * - branch_id: Unique identifier for each branch
 * - parent_snapshot_id: Tracks the snapshot this branch originated from
 * - is_active_branch: Marks the currently active branch
 * - Branch lineage tracking for full history
 */

-- ============================================================================
-- 1. ADD BRANCH MANAGEMENT COLUMNS TO SNAPSHOTS TABLE
-- ============================================================================

-- Add branch management columns
ALTER TABLE article_generation_step_snapshots
ADD COLUMN IF NOT EXISTS branch_id UUID DEFAULT gen_random_uuid(),
ADD COLUMN IF NOT EXISTS parent_snapshot_id UUID REFERENCES article_generation_step_snapshots(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS is_active_branch BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS branch_name TEXT;

-- Add comments
COMMENT ON COLUMN article_generation_step_snapshots.branch_id IS 'Unique identifier for this branch - all snapshots in same branch share this ID';
COMMENT ON COLUMN article_generation_step_snapshots.parent_snapshot_id IS 'The snapshot this branch was created from (null for main branch)';
COMMENT ON COLUMN article_generation_step_snapshots.is_active_branch IS 'Whether this branch is currently active for the process';
COMMENT ON COLUMN article_generation_step_snapshots.branch_name IS 'User-friendly branch name (e.g., "Main", "Persona variant 1")';

-- ============================================================================
-- 2. CREATE INDEXES FOR BRANCH QUERIES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_snapshots_branch_id ON article_generation_step_snapshots(branch_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_parent_snapshot ON article_generation_step_snapshots(parent_snapshot_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_active_branch ON article_generation_step_snapshots(process_id, is_active_branch) WHERE is_active_branch = TRUE;
CREATE INDEX IF NOT EXISTS idx_snapshots_process_branch ON article_generation_step_snapshots(process_id, branch_id);

-- ============================================================================
-- 3. UPDATE save_step_snapshot FUNCTION FOR BRANCH SUPPORT
-- ============================================================================

CREATE OR REPLACE FUNCTION save_step_snapshot(
    p_process_id UUID,
    p_step_name TEXT,
    p_article_context JSONB,
    p_step_description TEXT DEFAULT NULL,
    p_step_category TEXT DEFAULT 'autonomous',
    p_snapshot_metadata JSONB DEFAULT '{}'::jsonb,
    p_branch_id UUID DEFAULT NULL  -- New parameter for branch support
)
RETURNS UUID AS $$
DECLARE
    v_snapshot_id UUID;
    v_step_index INTEGER;
    v_branch_id UUID;
    v_parent_snapshot_id UUID;
    v_branch_name TEXT;
BEGIN
    -- Determine branch_id and parent
    IF p_branch_id IS NULL THEN
        -- Get current active branch for this process
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
            -- Continue same branch
            v_branch_name := (
                SELECT branch_name FROM article_generation_step_snapshots
                WHERE branch_id = v_branch_id
                LIMIT 1
            );
        END IF;
    ELSE
        v_branch_id := p_branch_id;
        -- Branch name will be set by caller
        v_branch_name := NULL;
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

    RETURN v_snapshot_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 4. CREATE FUNCTION TO CREATE NEW BRANCH FROM SNAPSHOT
-- ============================================================================

CREATE OR REPLACE FUNCTION create_branch_from_snapshot(
    p_snapshot_id UUID,
    p_branch_name TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_new_branch_id UUID;
    v_process_id UUID;
    v_snapshot_data RECORD;
BEGIN
    -- Get snapshot data
    SELECT
        process_id,
        step_name,
        article_context,
        snapshot_metadata
    INTO v_snapshot_data
    FROM article_generation_step_snapshots
    WHERE id = p_snapshot_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Snapshot not found: %', p_snapshot_id;
    END IF;

    v_process_id := v_snapshot_data.process_id;

    -- Deactivate current active branch for this process
    UPDATE article_generation_step_snapshots
    SET is_active_branch = FALSE
    WHERE process_id = v_process_id
      AND is_active_branch = TRUE;

    -- Generate new branch ID
    v_new_branch_id := gen_random_uuid();

    -- Create new branch snapshot (copy of the restore point)
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
    )
    SELECT
        process_id,
        step_name,
        1, -- Reset index for new branch
        step_category,
        step_description,
        article_context,
        snapshot_metadata,
        v_new_branch_id,
        p_snapshot_id, -- This snapshot is the parent
        TRUE, -- New branch is now active
        COALESCE(p_branch_name, '分岐 ' || TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI')),
        TRUE,
        NOW()
    FROM article_generation_step_snapshots
    WHERE id = p_snapshot_id;

    RETURN v_new_branch_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION create_branch_from_snapshot IS 'Create a new branch from an existing snapshot, preserving all existing branches';

-- ============================================================================
-- 5. CREATE FUNCTION TO SWITCH ACTIVE BRANCH
-- ============================================================================

CREATE OR REPLACE FUNCTION switch_to_branch(
    p_process_id UUID,
    p_branch_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_latest_snapshot_id UUID;
    v_article_context JSONB;
    v_step_name TEXT;
BEGIN
    -- Verify branch exists for this process
    SELECT id, article_context, step_name
    INTO v_latest_snapshot_id, v_article_context, v_step_name
    FROM article_generation_step_snapshots
    WHERE process_id = p_process_id
      AND branch_id = p_branch_id
    ORDER BY created_at DESC
    LIMIT 1;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Branch % not found for process %', p_branch_id, p_process_id;
    END IF;

    -- Deactivate all branches for this process
    UPDATE article_generation_step_snapshots
    SET is_active_branch = FALSE
    WHERE process_id = p_process_id;

    -- Activate the target branch
    UPDATE article_generation_step_snapshots
    SET is_active_branch = TRUE
    WHERE process_id = p_process_id
      AND branch_id = p_branch_id;

    -- Update process state to reflect the branch
    UPDATE generated_articles_state
    SET
        current_step_name = v_step_name,
        article_context = v_article_context,
        updated_at = NOW(),
        last_activity_at = NOW()
    WHERE id = p_process_id;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION switch_to_branch IS 'Switch active branch for a process without creating a new branch';

-- ============================================================================
-- 6. UPDATE get_available_snapshots TO SHOW BRANCH INFO
-- ============================================================================

-- Drop existing function first (return type changed)
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
    parent_snapshot_id UUID
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
        article_generation_step_snapshots.can_restore,
        article_generation_step_snapshots.branch_id,
        article_generation_step_snapshots.branch_name,
        article_generation_step_snapshots.is_active_branch,
        article_generation_step_snapshots.parent_snapshot_id
    FROM article_generation_step_snapshots
    WHERE article_generation_step_snapshots.process_id = p_process_id
        AND article_generation_step_snapshots.can_restore = TRUE
    ORDER BY article_generation_step_snapshots.created_at ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- 7. UPDATE restore_from_snapshot TO USE BRANCH SYSTEM
-- ============================================================================

-- Drop existing function first (signature changed)
DROP FUNCTION IF EXISTS restore_from_snapshot(UUID);

CREATE OR REPLACE FUNCTION restore_from_snapshot(
    p_snapshot_id UUID,
    p_create_new_branch BOOLEAN DEFAULT TRUE
)
RETURNS JSONB AS $$
DECLARE
    v_process_id UUID;
    v_step_name TEXT;
    v_article_context JSONB;
    v_new_branch_id UUID;
    v_branch_id UUID;
BEGIN
    -- Retrieve snapshot data
    SELECT
        process_id,
        step_name,
        article_context,
        branch_id
    INTO v_process_id, v_step_name, v_article_context, v_branch_id
    FROM article_generation_step_snapshots
    WHERE id = p_snapshot_id AND can_restore = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Snapshot not found or cannot be restored: %', p_snapshot_id;
    END IF;

    IF p_create_new_branch THEN
        -- Create new branch from this snapshot
        v_new_branch_id := create_branch_from_snapshot(p_snapshot_id);
    ELSE
        -- Switch to existing branch
        PERFORM switch_to_branch(v_process_id, v_branch_id);
        v_new_branch_id := v_branch_id;
    END IF;

    -- Add restoration metadata to context
    v_article_context := jsonb_set(
        v_article_context,
        '{_restoration_metadata}',
        jsonb_build_object(
            'restored_from_snapshot', p_snapshot_id,
            'restored_at', NOW(),
            'branch_id', v_new_branch_id,
            'created_new_branch', p_create_new_branch
        )
    );

    -- Update process state
    UPDATE generated_articles_state
    SET
        current_step_name = v_step_name,
        article_context = v_article_context,
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
        'step_restored',
        jsonb_build_object(
            'snapshot_id', p_snapshot_id,
            'restored_step', v_step_name,
            'branch_id', v_new_branch_id,
            'created_new_branch', p_create_new_branch,
            'restored_at', NOW()
        )
    );

    RETURN jsonb_build_object(
        'process_id', v_process_id,
        'step_name', v_step_name,
        'branch_id', v_new_branch_id,
        'created_new_branch', p_create_new_branch
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION restore_from_snapshot IS 'Restore process from snapshot, optionally creating a new branch';
