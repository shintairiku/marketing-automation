/**
 * Fix company_info.target_persona column length
 * The current VARCHAR(50) is too restrictive for detailed persona descriptions
 * Increasing to TEXT to allow for comprehensive persona descriptions
 */

-- Increase target_persona column size from VARCHAR(50) to TEXT
ALTER TABLE company_info 
ALTER COLUMN target_persona TYPE TEXT;

-- Update the column comment to reflect the change
COMMENT ON COLUMN company_info.target_persona IS 'Target customer persona (detailed description)';