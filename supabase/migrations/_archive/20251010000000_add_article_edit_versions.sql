/**
 * ARTICLE EDIT VERSION HISTORY SYSTEM
 *
 * This migration implements version control for article editing,
 * similar to Google Docs version history.
 *
 * Key Features:
 * 1. Complete version history of article edits
 * 2. Navigation between versions (forward/backward)
 * 3. Version restoration capabilities
 * 4. Automatic version limit management
 * 5. Change descriptions and metadata
 */

-- ============================================================================
-- 1. CREATE ARTICLE EDIT VERSIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS article_edit_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Article reference
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,

    -- User who created this version
    user_id TEXT NOT NULL,

    -- Version tracking
    version_number INTEGER NOT NULL, -- Sequential version number per article

    -- Content snapshot
    title TEXT, -- Article title at this version
    content TEXT NOT NULL, -- Article content at this version

    -- Version metadata
    change_description TEXT, -- User-provided description of changes
    is_current BOOLEAN DEFAULT FALSE, -- Whether this is the current version

    -- Additional metadata
    metadata JSONB DEFAULT '{}'::jsonb, -- Additional information (word count, etc.)

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint: one version number per article
    CONSTRAINT unique_article_version UNIQUE(article_id, version_number)
);

-- Add comments for documentation
COMMENT ON TABLE article_edit_versions IS 'Version history for article edits - tracks all saved versions';
COMMENT ON COLUMN article_edit_versions.version_number IS 'Sequential version number starting from 1';
COMMENT ON COLUMN article_edit_versions.is_current IS 'Indicates the current active version (HEAD)';
COMMENT ON COLUMN article_edit_versions.change_description IS 'User-provided or auto-generated description of changes';
COMMENT ON COLUMN article_edit_versions.metadata IS 'Additional version metadata (word count, character count, etc.)';

-- ============================================================================
-- 2. CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_article_versions_article_id ON article_edit_versions(article_id);
CREATE INDEX IF NOT EXISTS idx_article_versions_created_at ON article_edit_versions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_article_versions_article_created ON article_edit_versions(article_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_article_versions_article_version ON article_edit_versions(article_id, version_number DESC);
CREATE INDEX IF NOT EXISTS idx_article_versions_is_current ON article_edit_versions(article_id, is_current) WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_article_versions_user ON article_edit_versions(user_id);

-- ============================================================================
-- 3. ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE article_edit_versions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can access versions of articles they own
DROP POLICY IF EXISTS "Users can access their own article versions" ON article_edit_versions;
CREATE POLICY "Users can access their own article versions" ON article_edit_versions
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM articles
            WHERE id = article_edit_versions.article_id
                AND user_id = current_setting('request.jwt.claims', true)::json->>'sub'::text
        )
    );

-- ============================================================================
-- 4. HELPER FUNCTIONS
-- ============================================================================

-- Function: Save a new article version
CREATE OR REPLACE FUNCTION save_article_version(
    p_article_id UUID,
    p_user_id TEXT,
    p_title TEXT,
    p_content TEXT,
    p_change_description TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::jsonb,
    p_max_versions INTEGER DEFAULT 50 -- Default maximum versions to keep
)
RETURNS UUID AS $$
DECLARE
    v_version_id UUID;
    v_next_version_number INTEGER;
    v_version_count INTEGER;
    v_versions_to_delete INTEGER;
BEGIN
    -- Get the next version number for this article
    SELECT COALESCE(MAX(version_number), 0) + 1 INTO v_next_version_number
    FROM article_edit_versions
    WHERE article_id = p_article_id;

    -- Mark all existing versions as not current
    UPDATE article_edit_versions
    SET is_current = FALSE
    WHERE article_id = p_article_id;

    -- Insert new version
    INSERT INTO article_edit_versions (
        article_id,
        user_id,
        version_number,
        title,
        content,
        change_description,
        is_current,
        metadata,
        created_at
    ) VALUES (
        p_article_id,
        p_user_id,
        v_next_version_number,
        p_title,
        p_content,
        COALESCE(
            p_change_description,
            CASE
                WHEN v_next_version_number = 1 THEN '初期バージョン'
                ELSE 'バージョン ' || v_next_version_number
            END
        ),
        TRUE, -- New version is current
        p_metadata,
        NOW()
    )
    RETURNING id INTO v_version_id;

    -- Check if we need to clean up old versions
    SELECT COUNT(*) INTO v_version_count
    FROM article_edit_versions
    WHERE article_id = p_article_id;

    IF v_version_count > p_max_versions THEN
        v_versions_to_delete := v_version_count - p_max_versions;

        -- Delete oldest versions (keeping the most recent p_max_versions)
        DELETE FROM article_edit_versions
        WHERE id IN (
            SELECT id
            FROM article_edit_versions
            WHERE article_id = p_article_id
            ORDER BY version_number ASC
            LIMIT v_versions_to_delete
        );

        RAISE NOTICE 'Deleted % old version(s) for article %', v_versions_to_delete, p_article_id;
    END IF;

    RETURN v_version_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION save_article_version IS 'Save a new version of an article and automatically manage version limits';

-- Function: Get version history for an article
CREATE OR REPLACE FUNCTION get_article_version_history(
    p_article_id UUID,
    p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    version_id UUID,
    version_number INTEGER,
    title TEXT,
    change_description TEXT,
    is_current BOOLEAN,
    created_at TIMESTAMPTZ,
    user_id TEXT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        article_edit_versions.id,
        article_edit_versions.version_number,
        article_edit_versions.title,
        article_edit_versions.change_description,
        article_edit_versions.is_current,
        article_edit_versions.created_at,
        article_edit_versions.user_id,
        article_edit_versions.metadata
    FROM article_edit_versions
    WHERE article_edit_versions.article_id = p_article_id
    ORDER BY article_edit_versions.version_number DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_article_version_history IS 'Retrieve version history for an article in reverse chronological order';

-- Function: Get a specific version
CREATE OR REPLACE FUNCTION get_article_version(
    p_version_id UUID
)
RETURNS TABLE (
    version_id UUID,
    article_id UUID,
    version_number INTEGER,
    title TEXT,
    content TEXT,
    change_description TEXT,
    is_current BOOLEAN,
    created_at TIMESTAMPTZ,
    user_id TEXT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        article_edit_versions.id,
        article_edit_versions.article_id,
        article_edit_versions.version_number,
        article_edit_versions.title,
        article_edit_versions.content,
        article_edit_versions.change_description,
        article_edit_versions.is_current,
        article_edit_versions.created_at,
        article_edit_versions.user_id,
        article_edit_versions.metadata
    FROM article_edit_versions
    WHERE article_edit_versions.id = p_version_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_article_version IS 'Get details of a specific version';

-- Function: Restore an article to a specific version
CREATE OR REPLACE FUNCTION restore_article_version(
    p_version_id UUID,
    p_create_new_version BOOLEAN DEFAULT TRUE
)
RETURNS JSONB AS $$
DECLARE
    v_version RECORD;
    v_new_version_id UUID;
BEGIN
    -- Get the version data
    SELECT
        article_id,
        version_number,
        title,
        content,
        user_id
    INTO v_version
    FROM article_edit_versions
    WHERE id = p_version_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Version not found: %', p_version_id;
    END IF;

    -- Update the article with the version content
    UPDATE articles
    SET
        title = v_version.title,
        content = v_version.content,
        updated_at = NOW()
    WHERE id = v_version.article_id;

    IF p_create_new_version THEN
        -- Create a new version for this restoration
        v_new_version_id := save_article_version(
            v_version.article_id,
            v_version.user_id,
            v_version.title,
            v_version.content,
            'バージョン ' || v_version.version_number || ' から復元',
            jsonb_build_object(
                'restored_from_version', v_version.version_number,
                'restored_from_version_id', p_version_id,
                'restored_at', NOW()
            )
        );
    ELSE
        -- Just mark this version as current
        UPDATE article_edit_versions
        SET is_current = FALSE
        WHERE article_id = v_version.article_id;

        UPDATE article_edit_versions
        SET is_current = TRUE
        WHERE id = p_version_id;

        v_new_version_id := p_version_id;
    END IF;

    RETURN jsonb_build_object(
        'success', true,
        'article_id', v_version.article_id,
        'restored_version_number', v_version.version_number,
        'new_version_id', v_new_version_id,
        'created_new_version', p_create_new_version
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION restore_article_version IS 'Restore an article to a specific version, optionally creating a new version';

-- Function: Get current version
CREATE OR REPLACE FUNCTION get_current_article_version(
    p_article_id UUID
)
RETURNS UUID AS $$
DECLARE
    v_current_version_id UUID;
BEGIN
    SELECT id INTO v_current_version_id
    FROM article_edit_versions
    WHERE article_id = p_article_id
        AND is_current = TRUE
    LIMIT 1;

    RETURN v_current_version_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_current_article_version IS 'Get the current version ID for an article';

-- Function: Navigate to next version
CREATE OR REPLACE FUNCTION navigate_to_version(
    p_article_id UUID,
    p_direction TEXT -- 'next' or 'previous'
)
RETURNS UUID AS $$
DECLARE
    v_current_version_number INTEGER;
    v_target_version_id UUID;
    v_target_version_number INTEGER;
BEGIN
    -- Get current version number
    SELECT version_number INTO v_current_version_number
    FROM article_edit_versions
    WHERE article_id = p_article_id
        AND is_current = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No current version found for article %', p_article_id;
    END IF;

    -- Find target version based on direction
    IF p_direction = 'next' THEN
        SELECT id, version_number INTO v_target_version_id, v_target_version_number
        FROM article_edit_versions
        WHERE article_id = p_article_id
            AND version_number > v_current_version_number
        ORDER BY version_number ASC
        LIMIT 1;
    ELSIF p_direction = 'previous' THEN
        SELECT id, version_number INTO v_target_version_id, v_target_version_number
        FROM article_edit_versions
        WHERE article_id = p_article_id
            AND version_number < v_current_version_number
        ORDER BY version_number DESC
        LIMIT 1;
    ELSE
        RAISE EXCEPTION 'Invalid direction: %. Must be "next" or "previous"', p_direction;
    END IF;

    IF v_target_version_id IS NULL THEN
        RAISE EXCEPTION 'No % version available', p_direction;
    END IF;

    -- Update current markers (don't create new version, just navigate)
    UPDATE article_edit_versions
    SET is_current = FALSE
    WHERE article_id = p_article_id;

    UPDATE article_edit_versions
    SET is_current = TRUE
    WHERE id = v_target_version_id;

    -- Update article content to match target version
    UPDATE articles
    SET
        title = (SELECT title FROM article_edit_versions WHERE id = v_target_version_id),
        content = (SELECT content FROM article_edit_versions WHERE id = v_target_version_id),
        updated_at = NOW()
    WHERE id = p_article_id;

    RETURN v_target_version_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION navigate_to_version IS 'Navigate to next or previous version without creating a new version';

-- Function: Delete a specific version
CREATE OR REPLACE FUNCTION delete_article_version(
    p_version_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_is_current BOOLEAN;
    v_article_id UUID;
BEGIN
    -- Check if this is the current version
    SELECT is_current, article_id INTO v_is_current, v_article_id
    FROM article_edit_versions
    WHERE id = p_version_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Version not found: %', p_version_id;
    END IF;

    IF v_is_current THEN
        RAISE EXCEPTION 'Cannot delete current version. Please navigate to a different version first.';
    END IF;

    -- Delete the version
    DELETE FROM article_edit_versions
    WHERE id = p_version_id;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION delete_article_version IS 'Delete a specific version (cannot delete current version)';

-- ============================================================================
-- 5. REALTIME PUBLICATION
-- ============================================================================

-- Update publication to include new table
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
    article_generation_step_snapshots,
    article_edit_versions; -- Added

-- Set replica identity for realtime
ALTER TABLE article_edit_versions REPLICA IDENTITY FULL;

-- ============================================================================
-- 6. GRANTS
-- ============================================================================

-- Grant necessary permissions to authenticated users
GRANT SELECT ON article_edit_versions TO authenticated;

-- ============================================================================
-- 7. UTILITY VIEW
-- ============================================================================

-- View: Article version summary
CREATE OR REPLACE VIEW article_version_summary AS
SELECT
    a.id AS article_id,
    a.title AS current_title,
    COUNT(aev.id) AS total_versions,
    MAX(aev.version_number) AS latest_version_number,
    MIN(aev.created_at) AS first_version_created,
    MAX(aev.created_at) AS latest_version_created,
    (SELECT version_number FROM article_edit_versions WHERE article_id = a.id AND is_current = TRUE) AS current_version_number
FROM articles a
LEFT JOIN article_edit_versions aev ON a.id = aev.article_id
GROUP BY a.id, a.title;

COMMENT ON VIEW article_version_summary IS 'Summary of version information for each article';

GRANT SELECT ON article_version_summary TO authenticated;
