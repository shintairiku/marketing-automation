/**
 * ENHANCED ARTICLE GENERATION SYSTEM
 * This migration adds enhanced state tracking and recovery capabilities
 * for the article generation process.
 */

-- Add new columns to generated_articles_state for enhanced tracking
ALTER TABLE generated_articles_state 
ADD COLUMN IF NOT EXISTS current_step_name TEXT,
ADD COLUMN IF NOT EXISTS progress_percentage INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS is_waiting_for_input BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS input_type TEXT,
ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()),
ADD COLUMN IF NOT EXISTS auto_resume_eligible BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS resume_from_step TEXT,
ADD COLUMN IF NOT EXISTS step_history JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS process_metadata JSONB DEFAULT '{}'::jsonb;

-- Create index for faster queries on active processes
CREATE INDEX IF NOT EXISTS idx_generated_articles_state_status 
ON generated_articles_state(status);

CREATE INDEX IF NOT EXISTS idx_generated_articles_state_user_status 
ON generated_articles_state(user_id, status);

CREATE INDEX IF NOT EXISTS idx_generated_articles_state_last_activity 
ON generated_articles_state(last_activity_at DESC);

-- Add new status enum values if they don't exist
DO $$ 
BEGIN
    -- Check and add new status values
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = 'generation_status' AND e.enumlabel = 'resuming') THEN
        ALTER TYPE generation_status ADD VALUE 'resuming';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = 'generation_status' AND e.enumlabel = 'auto_progressing') THEN
        ALTER TYPE generation_status ADD VALUE 'auto_progressing';
    END IF;
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Create a function to update last_activity_at automatically
CREATE OR REPLACE FUNCTION update_last_activity()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_activity_at = TIMEZONE('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update last_activity_at
DROP TRIGGER IF EXISTS trigger_update_last_activity ON generated_articles_state;
CREATE TRIGGER trigger_update_last_activity
    BEFORE UPDATE ON generated_articles_state
    FOR EACH ROW EXECUTE FUNCTION update_last_activity();

-- Function to add step to history
CREATE OR REPLACE FUNCTION add_step_to_history(
    process_id UUID,
    step_name TEXT,
    step_status TEXT,
    step_data JSONB DEFAULT '{}'::jsonb
)
RETURNS VOID AS $$
DECLARE
    new_step JSONB;
    current_history JSONB;
BEGIN
    -- Create new step entry
    new_step := jsonb_build_object(
        'step_name', step_name,
        'status', step_status,
        'timestamp', TIMEZONE('utc'::text, now()),
        'data', step_data
    );
    
    -- Get current history
    SELECT COALESCE(step_history, '[]'::jsonb) INTO current_history
    FROM generated_articles_state
    WHERE id = process_id;
    
    -- Add new step to history
    UPDATE generated_articles_state
    SET step_history = current_history || new_step
    WHERE id = process_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get process recovery information
CREATE OR REPLACE FUNCTION get_process_recovery_info(process_id UUID)
RETURNS TABLE(
    can_resume BOOLEAN,
    resume_step TEXT,
    current_data JSONB,
    waiting_for_input BOOLEAN,
    input_type TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (s.status IN ('user_input_required', 'paused', 'error') AND s.auto_resume_eligible),
        s.resume_from_step,
        s.generated_content,
        s.is_waiting_for_input,
        s.input_type
    FROM generated_articles_state s
    WHERE s.id = process_id;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old completed processes (optional, for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_processes(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM generated_articles_state
    WHERE status IN ('completed', 'cancelled')
    AND updated_at < (TIMEZONE('utc'::text, now()) - INTERVAL '1 day' * days_old);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Update RLS policies to handle new functionality
CREATE POLICY "Users can resume their own processes" ON generated_articles_state
  FOR UPDATE USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub')
  WITH CHECK (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- Add comments for documentation
COMMENT ON COLUMN generated_articles_state.current_step_name IS 'Human-readable name of the current step';
COMMENT ON COLUMN generated_articles_state.progress_percentage IS 'Overall progress percentage (0-100)';
COMMENT ON COLUMN generated_articles_state.is_waiting_for_input IS 'Whether the process is waiting for user input';
COMMENT ON COLUMN generated_articles_state.input_type IS 'Type of input required (select_persona, approve_plan, etc.)';
COMMENT ON COLUMN generated_articles_state.last_activity_at IS 'Timestamp of last activity on this process';
COMMENT ON COLUMN generated_articles_state.auto_resume_eligible IS 'Whether this process can be automatically resumed';
COMMENT ON COLUMN generated_articles_state.resume_from_step IS 'Step to resume from when restarting';
COMMENT ON COLUMN generated_articles_state.step_history IS 'Array of completed steps with timestamps and data';
COMMENT ON COLUMN generated_articles_state.process_metadata IS 'Additional metadata for the process (research progress, etc.)';

-- Update realtime publication to include the enhanced table
DROP PUBLICATION IF EXISTS supabase_realtime;
CREATE PUBLICATION supabase_realtime FOR TABLE 
  products, prices, organizations, organization_members, invitations,
  article_generation_flows, flow_steps, generated_articles_state, articles;