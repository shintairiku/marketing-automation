-- Fix duplicate articles issue
-- This migration prevents duplicate articles with the same generation_process_id
-- and ensures we always get the most complete article

BEGIN;

-- 1. First, identify and remove duplicate articles keeping only the most recent/complete one
-- Delete dependent image_placeholders first
WITH duplicate_processes AS (
    SELECT generation_process_id, COUNT(*) as count
    FROM articles 
    WHERE generation_process_id IS NOT NULL 
    GROUP BY generation_process_id 
    HAVING COUNT(*) > 1
),
articles_to_keep AS (
    SELECT DISTINCT ON (a.generation_process_id) a.id
    FROM articles a
    INNER JOIN duplicate_processes dp ON a.generation_process_id = dp.generation_process_id
    ORDER BY a.generation_process_id, LENGTH(a.content) DESC, a.updated_at DESC
)
DELETE FROM image_placeholders 
WHERE article_id IN (
    SELECT id FROM articles 
    WHERE generation_process_id IN (SELECT generation_process_id FROM duplicate_processes)
    AND id NOT IN (SELECT id FROM articles_to_keep)
);

-- Then delete the duplicate articles
WITH duplicate_processes AS (
    SELECT generation_process_id, COUNT(*) as count
    FROM articles 
    WHERE generation_process_id IS NOT NULL 
    GROUP BY generation_process_id 
    HAVING COUNT(*) > 1
),
articles_to_keep AS (
    SELECT DISTINCT ON (a.generation_process_id) a.id
    FROM articles a
    INNER JOIN duplicate_processes dp ON a.generation_process_id = dp.generation_process_id
    ORDER BY a.generation_process_id, LENGTH(a.content) DESC, a.updated_at DESC
)
DELETE FROM articles 
WHERE generation_process_id IN (SELECT generation_process_id FROM duplicate_processes)
AND id NOT IN (SELECT id FROM articles_to_keep);

-- 2. Add unique constraint to prevent future duplicates
CREATE UNIQUE INDEX unique_generation_process_id 
ON articles (generation_process_id) 
WHERE generation_process_id IS NOT NULL;

-- 3. Create index to improve query performance
CREATE INDEX IF NOT EXISTS idx_articles_generation_process_id_updated_at 
ON articles(generation_process_id, updated_at DESC) 
WHERE generation_process_id IS NOT NULL;

-- 4. Create index to improve content length queries
CREATE INDEX IF NOT EXISTS idx_articles_content_length 
ON articles(generation_process_id, LENGTH(content) DESC) 
WHERE generation_process_id IS NOT NULL;

-- 5. Add comment for documentation
COMMENT ON INDEX unique_generation_process_id IS 
'Ensures only one article per generation process to prevent duplicates';

-- 6. Update RLS policies to ensure proper access control
-- Refresh the RLS policy for articles to ensure it works with the new constraint
DROP POLICY IF EXISTS "Users can manage their own articles" ON articles;
CREATE POLICY "Users can manage their own articles" ON articles
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

COMMIT;