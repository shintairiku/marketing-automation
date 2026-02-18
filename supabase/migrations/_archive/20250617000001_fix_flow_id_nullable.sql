/**
 * FIX FLOW_ID NULLABLE
 * Make flow_id nullable in generated_articles_state table for backward compatibility
 * with the existing article generation system that doesn't use flows yet.
 */

-- Make flow_id nullable to support existing article generation without flows
ALTER TABLE generated_articles_state 
ALTER COLUMN flow_id DROP NOT NULL;

-- Add comment to clarify the usage
COMMENT ON COLUMN generated_articles_state.flow_id IS 'Optional flow ID for flow-based generation. NULL for traditional generation.';

-- Update the policy to handle both flow-based and traditional generation
DROP POLICY IF EXISTS "Users can manage their own generation processes" ON generated_articles_state;

CREATE POLICY "Users can manage their own generation processes" ON generated_articles_state
  FOR ALL USING (
    -- Clerk users: check JWT claims
    (current_setting('request.jwt.claims', true)::json->>'sub' IS NOT NULL AND 
     user_id = current_setting('request.jwt.claims', true)::json->>'sub') OR
    -- Supabase Auth users: check auth.uid()
    (auth.uid() IS NOT NULL AND user_id::text = auth.uid()::text)
  );