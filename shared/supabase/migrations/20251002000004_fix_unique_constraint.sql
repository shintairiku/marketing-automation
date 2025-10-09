/**
 * FIX UNIQUE CONSTRAINT FOR BRANCH SUPPORT
 *
 * The original unique constraint (process_id, step_name, step_index)
 * doesn't support branches properly.
 * We need to include branch_id in the constraint.
 */

-- Drop the old constraint
ALTER TABLE article_generation_step_snapshots
DROP CONSTRAINT IF EXISTS unique_process_step_index;

-- Add the new constraint that includes branch_id
ALTER TABLE article_generation_step_snapshots
ADD CONSTRAINT unique_process_step_branch UNIQUE(process_id, step_name, step_index, branch_id);

COMMENT ON CONSTRAINT unique_process_step_branch ON article_generation_step_snapshots
IS 'Ensures one snapshot per process/step/index/branch combination, allowing different branches to have same step';
