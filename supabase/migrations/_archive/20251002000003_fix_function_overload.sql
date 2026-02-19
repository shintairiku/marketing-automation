/**
 * FIX FUNCTION OVERLOAD CONFLICT
 *
 * Remove the old save_step_snapshot function (6 parameters)
 * Keep only the new version (7 parameters with p_branch_id)
 */

-- Drop the old 6-parameter version
DROP FUNCTION IF EXISTS save_step_snapshot(
    UUID, -- p_process_id
    TEXT, -- p_step_name
    JSONB, -- p_article_context
    TEXT, -- p_step_description
    TEXT, -- p_step_category
    JSONB -- p_snapshot_metadata
);

-- Ensure the new 7-parameter version exists with proper defaults
-- This was already created in 20251002000002, but we recreate it to be sure
CREATE OR REPLACE FUNCTION save_step_snapshot(
    p_process_id UUID,
    p_step_name TEXT,
    p_article_context JSONB,
    p_step_description TEXT DEFAULT NULL,
    p_step_category TEXT DEFAULT 'autonomous',
    p_snapshot_metadata JSONB DEFAULT '{}'::jsonb,
    p_branch_id UUID DEFAULT NULL  -- New parameter for branch support, optional
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

COMMENT ON FUNCTION save_step_snapshot IS 'Save a step snapshot with optional branch support (backward compatible)';
