-- Fix the foreign key constraint issue in process_events trigger
-- The issue: BEFORE trigger tries to insert into process_events before the parent record exists in generated_articles_state

-- 1. Drop the existing trigger
DROP TRIGGER IF EXISTS trigger_publish_process_event ON generated_articles_state;

-- 2. Update the trigger function to work with AFTER triggers
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
  
  -- Insert event record (now the parent record exists, so no foreign key violation)
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
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Create the new AFTER trigger
CREATE TRIGGER trigger_publish_process_event
  AFTER INSERT OR UPDATE ON generated_articles_state
  FOR EACH ROW EXECUTE FUNCTION publish_process_event();

-- 4. Also add a function to update realtime fields during the initial insert
-- This function will be called by BEFORE INSERT to set the realtime channel
CREATE OR REPLACE FUNCTION set_realtime_channel()
RETURNS TRIGGER AS $$
BEGIN
  -- Set realtime channel name and updated timestamp
  NEW.realtime_channel := 'process_' || NEW.id::text;
  NEW.updated_at := NOW();
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5. Create BEFORE INSERT trigger for setting realtime channel
CREATE TRIGGER trigger_set_realtime_channel
  BEFORE INSERT ON generated_articles_state
  FOR EACH ROW EXECUTE FUNCTION set_realtime_channel();

-- Log the fix completion
DO $$
BEGIN
  RAISE NOTICE 'Foreign key constraint fix applied successfully at %', NOW();
  RAISE NOTICE 'Changed trigger timing from BEFORE to AFTER INSERT/UPDATE';
  RAISE NOTICE 'Added separate BEFORE INSERT trigger for realtime channel setup';
  RAISE NOTICE 'Events will now be created after the parent record exists';
END $$;