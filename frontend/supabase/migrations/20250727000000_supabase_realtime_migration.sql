/**
 * SUPABASE REALTIME MIGRATION
 * 
 * This migration implements the transition from WebSocket-based communication 
 * to Supabase Realtime for the article generation system.
 * 
 * Key Changes:
 * 1. Enhanced process state tracking with realtime fields
 * 2. New process_events table for event streaming
 * 3. Background task management table
 * 4. Database triggers for automatic realtime publishing
 * 5. Updated realtime publications
 */

-- ============================================================================
-- 1. ENHANCE EXISTING GENERATED_ARTICLES_STATE TABLE
-- ============================================================================

-- Add realtime-specific fields to existing table
ALTER TABLE generated_articles_state 
ADD COLUMN IF NOT EXISTS realtime_channel TEXT,
ADD COLUMN IF NOT EXISTS last_realtime_event JSONB,
ADD COLUMN IF NOT EXISTS realtime_subscriptions JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS executing_step TEXT,
ADD COLUMN IF NOT EXISTS step_execution_start TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS step_execution_metadata JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS background_task_id TEXT,
ADD COLUMN IF NOT EXISTS task_priority INTEGER DEFAULT 5,
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 3,
ADD COLUMN IF NOT EXISTS user_input_timeout TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS input_reminder_sent BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS interaction_history JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS process_type TEXT DEFAULT 'article_generation',
ADD COLUMN IF NOT EXISTS parent_process_id UUID REFERENCES generated_articles_state(id),
ADD COLUMN IF NOT EXISTS process_tags TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS step_durations JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS total_processing_time INTERVAL,
ADD COLUMN IF NOT EXISTS estimated_completion_time TIMESTAMP WITH TIME ZONE;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_generated_articles_state_realtime_channel 
ON generated_articles_state(realtime_channel);

CREATE INDEX IF NOT EXISTS idx_generated_articles_state_executing_step 
ON generated_articles_state(executing_step) WHERE executing_step IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_generated_articles_state_background_task 
ON generated_articles_state(background_task_id) WHERE background_task_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_generated_articles_state_user_input_timeout 
ON generated_articles_state(user_input_timeout) WHERE user_input_timeout IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_generated_articles_state_process_type 
ON generated_articles_state(process_type);

-- ============================================================================
-- 2. CREATE PROCESS_EVENTS TABLE FOR REALTIME EVENT STREAMING
-- ============================================================================

CREATE TABLE IF NOT EXISTS process_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  process_id UUID NOT NULL REFERENCES generated_articles_state(id) ON DELETE CASCADE,
  
  -- Event details
  event_type TEXT NOT NULL,
  event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_sequence INTEGER NOT NULL,
  
  -- Event metadata
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  published_at TIMESTAMP WITH TIME ZONE,
  acknowledged_by TEXT[] DEFAULT '{}', -- User IDs who acknowledged this event
  delivery_attempts INTEGER DEFAULT 0,
  
  -- Event categorization
  event_category TEXT DEFAULT 'system',
  event_priority INTEGER DEFAULT 5,
  event_source TEXT DEFAULT 'backend',
  
  -- Retention and cleanup
  expires_at TIMESTAMP WITH TIME ZONE,
  archived BOOLEAN DEFAULT FALSE,
  
  -- Ensure unique sequence per process
  CONSTRAINT unique_process_sequence UNIQUE(process_id, event_sequence)
);

-- Create indexes for efficient querying
CREATE INDEX idx_process_events_process_id ON process_events(process_id);
CREATE INDEX idx_process_events_created_at ON process_events(created_at DESC);
CREATE INDEX idx_process_events_type ON process_events(event_type);
CREATE INDEX idx_process_events_category ON process_events(event_category);
CREATE INDEX idx_process_events_published ON process_events(published_at DESC) WHERE published_at IS NOT NULL;
CREATE INDEX idx_process_events_undelivered ON process_events(process_id, event_sequence) 
  WHERE delivery_attempts < 3 AND acknowledged_by = '{}';

-- Add comments for documentation
COMMENT ON TABLE process_events IS 'Real-time events for article generation processes';
COMMENT ON COLUMN process_events.event_sequence IS 'Sequential number ensuring event order per process';
COMMENT ON COLUMN process_events.acknowledged_by IS 'Array of user IDs who have acknowledged this event';
COMMENT ON COLUMN process_events.delivery_attempts IS 'Number of times event delivery was attempted';
COMMENT ON COLUMN process_events.expires_at IS 'When this event should be cleaned up';

-- ============================================================================
-- 3. CREATE BACKGROUND_TASKS TABLE FOR TASK MANAGEMENT
-- ============================================================================

CREATE TABLE IF NOT EXISTS background_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  process_id UUID NOT NULL REFERENCES generated_articles_state(id) ON DELETE CASCADE,
  
  -- Task definition
  task_type TEXT NOT NULL,
  task_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  
  -- Task status and timing
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'paused')),
  priority INTEGER DEFAULT 5,
  scheduled_for TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  started_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  
  -- Error handling
  error_message TEXT,
  error_details JSONB,
  retry_count INTEGER DEFAULT 0,
  max_retries INTEGER DEFAULT 3,
  retry_delay_seconds INTEGER DEFAULT 60,
  
  -- Worker management
  worker_id TEXT,
  worker_hostname TEXT,
  heartbeat_at TIMESTAMP WITH TIME ZONE,
  
  -- Task dependencies
  depends_on UUID[] DEFAULT '{}',
  blocks_tasks UUID[] DEFAULT '{}',
  
  -- Metadata
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by TEXT,
  tags TEXT[] DEFAULT '{}',
  
  -- Performance tracking
  execution_time INTERVAL,
  estimated_duration INTERVAL,
  resource_usage JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for task management
CREATE INDEX idx_background_tasks_status ON background_tasks(status);
CREATE INDEX idx_background_tasks_scheduled ON background_tasks(scheduled_for) 
  WHERE status IN ('pending', 'paused');
CREATE INDEX idx_background_tasks_process_id ON background_tasks(process_id);
CREATE INDEX idx_background_tasks_priority_status ON background_tasks(priority DESC, status);
CREATE INDEX idx_background_tasks_worker ON background_tasks(worker_id) WHERE worker_id IS NOT NULL;
CREATE INDEX idx_background_tasks_type ON background_tasks(task_type);
CREATE INDEX idx_background_tasks_retry ON background_tasks(retry_count, max_retries) 
  WHERE status = 'failed' AND retry_count < max_retries;

-- Add comments
COMMENT ON TABLE background_tasks IS 'Background task queue for article generation processes';
COMMENT ON COLUMN background_tasks.depends_on IS 'Array of task IDs this task depends on';
COMMENT ON COLUMN background_tasks.blocks_tasks IS 'Array of task IDs blocked by this task';
COMMENT ON COLUMN background_tasks.resource_usage IS 'JSON tracking CPU, memory, API calls etc.';

-- ============================================================================
-- 4. CREATE TASK_DEPENDENCIES TABLE (IF NEEDED)
-- ============================================================================

CREATE TABLE IF NOT EXISTS task_dependencies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_task_id UUID NOT NULL REFERENCES background_tasks(id) ON DELETE CASCADE,
  dependent_task_id UUID NOT NULL REFERENCES background_tasks(id) ON DELETE CASCADE,
  dependency_type TEXT DEFAULT 'sequential' CHECK (dependency_type IN ('sequential', 'parallel', 'conditional')),
  condition_expression TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  CONSTRAINT unique_task_dependency UNIQUE(parent_task_id, dependent_task_id)
);

CREATE INDEX idx_task_dependencies_parent ON task_dependencies(parent_task_id);
CREATE INDEX idx_task_dependencies_dependent ON task_dependencies(dependent_task_id);

-- ============================================================================
-- 5. DATABASE FUNCTIONS FOR REALTIME EVENT PUBLISHING
-- ============================================================================

-- Function to publish realtime events
CREATE OR REPLACE FUNCTION publish_process_event()
RETURNS TRIGGER AS $$
DECLARE
  event_data JSONB;
  channel_name TEXT;
  next_sequence INTEGER;
  event_type_name TEXT;
BEGIN
  -- Determine channel name (process-specific)
  channel_name := 'process_' || NEW.id::text;
  
  -- Determine event type based on operation and changes
  IF TG_OP = 'INSERT' THEN
    event_type_name := 'process_created';
  ELSIF TG_OP = 'UPDATE' THEN
    -- More specific event types based on what changed
    IF OLD.status IS DISTINCT FROM NEW.status THEN
      event_type_name := 'status_changed';
    ELSIF OLD.current_step_name IS DISTINCT FROM NEW.current_step_name THEN
      event_type_name := 'step_changed';
    ELSIF OLD.progress_percentage IS DISTINCT FROM NEW.progress_percentage THEN
      event_type_name := 'progress_updated';
    ELSIF OLD.is_waiting_for_input IS DISTINCT FROM NEW.is_waiting_for_input THEN
      event_type_name := CASE 
        WHEN NEW.is_waiting_for_input THEN 'input_required' 
        ELSE 'input_resolved' 
      END;
    ELSE
      event_type_name := 'process_updated';
    END IF;
  ELSE
    event_type_name := 'process_changed';
  END IF;
  
  -- Prepare comprehensive event data
  event_data := jsonb_build_object(
    'process_id', NEW.id,
    'status', NEW.status,
    'current_step', NEW.current_step_name,
    'executing_step', NEW.executing_step,
    'progress_percentage', NEW.progress_percentage,
    'is_waiting_for_input', NEW.is_waiting_for_input,
    'input_type', NEW.input_type,
    'updated_at', NEW.updated_at,
    'event_type', event_type_name,
    'user_id', NEW.user_id,
    'organization_id', NEW.organization_id,
    'background_task_id', NEW.background_task_id,
    'retry_count', NEW.retry_count,
    'error_message', NEW.error_message,
    -- Include relevant context data
    'article_context', NEW.article_context,
    'process_metadata', NEW.process_metadata,
    'step_history', NEW.step_history,
    -- Change tracking for updates
    'changes', CASE WHEN TG_OP = 'UPDATE' THEN
      jsonb_build_object(
        'status', jsonb_build_object('old', OLD.status, 'new', NEW.status),
        'current_step', jsonb_build_object('old', OLD.current_step_name, 'new', NEW.current_step_name),
        'progress', jsonb_build_object('old', OLD.progress_percentage, 'new', NEW.progress_percentage)
      )
    ELSE NULL END
  );
  
  -- Get next sequence number for this process
  SELECT COALESCE(MAX(event_sequence), 0) + 1 
  INTO next_sequence
  FROM process_events 
  WHERE process_id = NEW.id;
  
  -- Insert event record (which will trigger realtime notification)
  INSERT INTO process_events (
    process_id, 
    event_type, 
    event_data, 
    event_sequence,
    event_category,
    event_source,
    published_at
  ) VALUES (
    NEW.id,
    event_type_name,
    event_data,
    next_sequence,
    'process_state',
    'database_trigger',
    NOW()
  );
  
  -- Update realtime fields in the process record
  NEW.realtime_channel := channel_name;
  NEW.last_realtime_event := event_data;
  NEW.updated_at := NOW();
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to automatically update task status
CREATE OR REPLACE FUNCTION update_task_status()
RETURNS TRIGGER AS $$
BEGIN
  -- Update timestamps based on status changes
  IF TG_OP = 'UPDATE' THEN
    IF OLD.status != NEW.status THEN
      CASE NEW.status
        WHEN 'running' THEN
          NEW.started_at := NOW();
          NEW.heartbeat_at := NOW();
        WHEN 'completed', 'failed', 'cancelled' THEN
          NEW.completed_at := NOW();
          IF NEW.started_at IS NOT NULL THEN
            NEW.execution_time := NOW() - NEW.started_at;
          END IF;
        ELSE
          -- Keep existing timestamps
      END CASE;
    END IF;
  END IF;
  
  -- Always update the updated_at timestamp
  NEW.updated_at := NOW();
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old events
CREATE OR REPLACE FUNCTION cleanup_old_events(days_old INTEGER DEFAULT 7)
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  -- Delete events older than specified days, but keep important ones
  DELETE FROM process_events
  WHERE created_at < (NOW() - INTERVAL '1 day' * days_old)
    AND event_type NOT IN ('process_created', 'generation_completed', 'generation_error')
    AND archived = FALSE;
  
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  
  -- Archive instead of delete for important events
  UPDATE process_events 
  SET archived = TRUE
  WHERE created_at < (NOW() - INTERVAL '1 day' * days_old * 2)
    AND event_type IN ('process_created', 'generation_completed', 'generation_error')
    AND archived = FALSE;
  
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get next available task
CREATE OR REPLACE FUNCTION get_next_background_task(
  worker_id_param TEXT,
  task_types TEXT[] DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
  task_id UUID;
BEGIN
  -- Get the highest priority pending task
  SELECT id INTO task_id
  FROM background_tasks
  WHERE status = 'pending'
    AND scheduled_for <= NOW()
    AND (task_types IS NULL OR task_type = ANY(task_types))
    AND (depends_on = '{}' OR NOT EXISTS (
      SELECT 1 FROM background_tasks dep 
      WHERE dep.id = ANY(background_tasks.depends_on) 
        AND dep.status NOT IN ('completed', 'cancelled')
    ))
  ORDER BY priority DESC, created_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;
  
  -- Claim the task
  IF task_id IS NOT NULL THEN
    UPDATE background_tasks
    SET status = 'running',
        worker_id = worker_id_param,
        started_at = NOW(),
        heartbeat_at = NOW()
    WHERE id = task_id;
  END IF;
  
  RETURN task_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 6. CREATE TRIGGERS
-- ============================================================================

-- Trigger for process state changes
DROP TRIGGER IF EXISTS trigger_publish_process_event ON generated_articles_state;
CREATE TRIGGER trigger_publish_process_event
  BEFORE INSERT OR UPDATE ON generated_articles_state
  FOR EACH ROW EXECUTE FUNCTION publish_process_event();

-- Trigger for background task updates
DROP TRIGGER IF EXISTS trigger_update_task_status ON background_tasks;
CREATE TRIGGER trigger_update_task_status
  BEFORE INSERT OR UPDATE ON background_tasks
  FOR EACH ROW EXECUTE FUNCTION update_task_status();

-- Trigger to automatically update updated_at on process_events
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: process_events doesn't have updated_at, but background_tasks trigger handles it

-- ============================================================================
-- 7. UPDATE REALTIME PUBLICATIONS
-- ============================================================================

-- Drop existing publication if it exists
DROP PUBLICATION IF EXISTS supabase_realtime;

-- Create new publication with all tables including new ones
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
  style_guide_templates;

-- Enable realtime for new tables (set replica identity)
ALTER TABLE process_events REPLICA IDENTITY FULL;
ALTER TABLE background_tasks REPLICA IDENTITY FULL;
ALTER TABLE task_dependencies REPLICA IDENTITY FULL;

-- Ensure existing tables have proper replica identity
ALTER TABLE generated_articles_state REPLICA IDENTITY FULL;

-- ============================================================================
-- 8. ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on new tables
ALTER TABLE process_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE background_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_dependencies ENABLE ROW LEVEL SECURITY;

-- RLS policies for process_events
CREATE POLICY "Users can view events for their processes" ON process_events
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM generated_articles_state 
      WHERE id = process_events.process_id 
        AND user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

CREATE POLICY "System can insert events" ON process_events
  FOR INSERT WITH CHECK (true); -- Backend system inserts

CREATE POLICY "Users can acknowledge their events" ON process_events
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM generated_articles_state 
      WHERE id = process_events.process_id 
        AND user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  ) WITH CHECK (
    EXISTS (
      SELECT 1 FROM generated_articles_state 
      WHERE id = process_events.process_id 
        AND user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

-- RLS policies for background_tasks  
CREATE POLICY "Users can view tasks for their processes" ON background_tasks
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM generated_articles_state 
      WHERE id = background_tasks.process_id 
        AND user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

CREATE POLICY "System can manage background tasks" ON background_tasks
  FOR ALL WITH CHECK (true); -- Backend system manages tasks

-- RLS policies for task_dependencies
CREATE POLICY "Users can view task dependencies for their processes" ON task_dependencies
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM background_tasks bt
      JOIN generated_articles_state gas ON bt.process_id = gas.id
      WHERE bt.id IN (task_dependencies.parent_task_id, task_dependencies.dependent_task_id)
        AND gas.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

-- ============================================================================
-- 9. UTILITY FUNCTIONS FOR APPLICATION USE
-- ============================================================================

-- Function to create a new process event manually
CREATE OR REPLACE FUNCTION create_process_event(
  p_process_id UUID,
  p_event_type TEXT,
  p_event_data JSONB DEFAULT '{}'::jsonb,
  p_event_category TEXT DEFAULT 'manual',
  p_event_source TEXT DEFAULT 'application'
)
RETURNS UUID AS $$
DECLARE
  event_id UUID;
  next_sequence INTEGER;
BEGIN
  -- Get next sequence number
  SELECT COALESCE(MAX(event_sequence), 0) + 1 
  INTO next_sequence
  FROM process_events 
  WHERE process_id = p_process_id;
  
  -- Insert the event
  INSERT INTO process_events (
    process_id,
    event_type,
    event_data,
    event_sequence,
    event_category,
    event_source,
    published_at
  ) VALUES (
    p_process_id,
    p_event_type,
    p_event_data,
    next_sequence,
    p_event_category,
    p_event_source,
    NOW()
  ) RETURNING id INTO event_id;
  
  RETURN event_id;
END;
$$ LANGUAGE plpgsql;

-- Function to mark process as waiting for input
CREATE OR REPLACE FUNCTION mark_process_waiting_for_input(
  p_process_id UUID,
  p_input_type TEXT,
  p_timeout_minutes INTEGER DEFAULT 30
)
RETURNS VOID AS $$
BEGIN
  UPDATE generated_articles_state
  SET 
    is_waiting_for_input = TRUE,
    input_type = p_input_type,
    user_input_timeout = NOW() + INTERVAL '1 minute' * p_timeout_minutes,
    input_reminder_sent = FALSE,
    status = 'user_input_required'
  WHERE id = p_process_id;
  
  -- Create corresponding event
  PERFORM create_process_event(
    p_process_id,
    'user_input_required',
    jsonb_build_object(
      'input_type', p_input_type,
      'timeout_at', NOW() + INTERVAL '1 minute' * p_timeout_minutes
    ),
    'user_interaction',
    'system'
  );
END;
$$ LANGUAGE plpgsql;

-- Function to resolve user input
CREATE OR REPLACE FUNCTION resolve_user_input(
  p_process_id UUID,
  p_user_response JSONB
)
RETURNS VOID AS $$
BEGIN
  UPDATE generated_articles_state
  SET 
    is_waiting_for_input = FALSE,
    input_type = NULL,
    user_input_timeout = NULL,
    input_reminder_sent = FALSE,
    status = 'in_progress',
    interaction_history = interaction_history || jsonb_build_object(
      'timestamp', NOW(),
      'action', 'input_resolved',
      'response', p_user_response
    )
  WHERE id = p_process_id;
  
  -- Create corresponding event
  PERFORM create_process_event(
    p_process_id,
    'user_input_resolved',
    jsonb_build_object(
      'user_response', p_user_response,
      'resolved_at', NOW()
    ),
    'user_interaction',
    'system'
  );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 10. PERFORMANCE OPTIMIZATIONS
-- ============================================================================

-- Partial index for active processes
CREATE INDEX IF NOT EXISTS idx_active_processes ON generated_articles_state(id, status, updated_at)
  WHERE status IN ('in_progress', 'user_input_required', 'paused');

-- Composite index for efficient event querying (removed time-based WHERE clause due to immutability requirements)
CREATE INDEX IF NOT EXISTS idx_recent_events ON process_events(process_id, event_sequence DESC, created_at DESC);

-- Composite index for task queue operations
CREATE INDEX IF NOT EXISTS idx_task_queue ON background_tasks(status, priority DESC, scheduled_for ASC)
  WHERE status IN ('pending', 'running');

-- Index for cleanup operations
CREATE INDEX IF NOT EXISTS idx_events_cleanup ON process_events(created_at, archived)
  WHERE archived = FALSE;

-- ============================================================================
-- 11. INITIAL DATA AND SETUP
-- ============================================================================

-- Update existing processes to have realtime channels
UPDATE generated_articles_state 
SET realtime_channel = 'process_' || id::text
WHERE realtime_channel IS NULL;

-- ============================================================================
-- 12. COMMENTS AND DOCUMENTATION
-- ============================================================================

COMMENT ON COLUMN generated_articles_state.realtime_channel IS 'Supabase Realtime channel name for this process';
COMMENT ON COLUMN generated_articles_state.executing_step IS 'Currently executing step (may differ from current_step_name)';
COMMENT ON COLUMN generated_articles_state.background_task_id IS 'ID of the background task processing this step';
COMMENT ON COLUMN generated_articles_state.user_input_timeout IS 'When user input request expires';
COMMENT ON COLUMN generated_articles_state.interaction_history IS 'History of user interactions with this process';

-- Add migration completion marker
INSERT INTO process_events (
  process_id,
  event_type,
  event_data,
  event_sequence,
  event_category,
  event_source
)
SELECT 
  id,
  'migration_completed',
  jsonb_build_object(
    'migration_version', '20250727000000',
    'migration_description', 'Supabase Realtime Migration',
    'features_added', ARRAY['realtime_events', 'background_tasks', 'enhanced_tracking']
  ),
  COALESCE((SELECT MAX(event_sequence) FROM process_events pe WHERE pe.process_id = gas.id), 0) + 1,
  'system',
  'migration'
FROM generated_articles_state gas
WHERE status IN ('in_progress', 'user_input_required', 'paused');

-- Log migration completion
DO $$
BEGIN
  RAISE NOTICE 'Supabase Realtime Migration completed successfully at %', NOW();
  RAISE NOTICE 'Added tables: process_events, background_tasks, task_dependencies';
  RAISE NOTICE 'Enhanced table: generated_articles_state with realtime fields';
  RAISE NOTICE 'Created triggers: publish_process_event, update_task_status';
  RAISE NOTICE 'Updated realtime publication to include new tables';
  RAISE NOTICE 'Configured RLS policies for secure access';
END $$;