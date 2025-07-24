/**
 * ADD CURRENT_STEP COLUMN TO GENERATED_ARTICLES_STATE
 * This migration adds the missing current_step column to track the current step in the generation process.
 */

-- Add current_step column to generated_articles_state table
ALTER TABLE generated_articles_state 
ADD COLUMN IF NOT EXISTS current_step TEXT;

-- Create index for faster queries on current_step
CREATE INDEX IF NOT EXISTS idx_generated_articles_state_current_step 
ON generated_articles_state(current_step);

-- Add comment for documentation
COMMENT ON COLUMN generated_articles_state.current_step IS 'Current step identifier in the article generation process';

-- Update the trigger to handle the new column
-- (The existing trigger will automatically handle this column since it updates last_activity_at on any update)

-- Optional: Initialize current_step for existing records if needed
-- UPDATE generated_articles_state 
-- SET current_step = 'unknown' 
-- WHERE current_step IS NULL AND status NOT IN ('completed', 'cancelled');