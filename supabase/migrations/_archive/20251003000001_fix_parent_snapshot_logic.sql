/**
 * FIX PARENT SNAPSHOT LOGIC
 *
 * parent_snapshot_idの意味を明確化：
 * - 同じブランチ内：parent_snapshot_id = そのブランチの直前のスナップショット
 * - 新しいブランチ：parent_snapshot_id = 分岐元のスナップショット（別ブランチ）
 */

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
    v_latest_in_branch UUID;
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
        SELECT id INTO v_latest_in_branch
        FROM article_generation_step_snapshots
        WHERE process_id = p_process_id
          AND branch_id = v_current_branch_id
        ORDER BY created_at DESC
        LIMIT 1;

        -- If current snapshot is NOT the latest, we're creating a branch
        IF v_latest_in_branch != v_current_snapshot_id THEN
            v_should_create_new_branch := TRUE;
            -- Parent is the snapshot we're branching FROM (the current position)
            v_parent_snapshot_id := v_current_snapshot_id;
        ELSE
            -- Continue on same branch, parent is current snapshot
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
        IF v_current_snapshot_id IS NOT NULL THEN
            -- Use current branch
            v_branch_id := v_current_branch_id;
            v_branch_name := (
                SELECT branch_name FROM article_generation_step_snapshots
                WHERE branch_id = v_branch_id
                LIMIT 1
            );
            -- Parent is already set above
        ELSE
            -- First snapshot ever (main branch)
            v_branch_id := gen_random_uuid();
            v_branch_name := 'メインブランチ';
            v_parent_snapshot_id := NULL;
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

COMMENT ON FUNCTION save_step_snapshot IS 'Save snapshot with proper parent tracking: same branch = previous snapshot, new branch = branching point';
