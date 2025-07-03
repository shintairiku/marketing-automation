/**
 * GCS SUPPORT FEATURE
 * This migration adds Google Cloud Storage support to the images table
 * for cloud-based image storage and serving
 */

-- Add GCS-related columns to images table
ALTER TABLE images 
ADD COLUMN IF NOT EXISTS gcs_url TEXT,
ADD COLUMN IF NOT EXISTS gcs_path TEXT,
ADD COLUMN IF NOT EXISTS storage_type TEXT DEFAULT 'local' CHECK (storage_type IN ('local', 'gcs', 'hybrid'));

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_images_storage_type ON images(storage_type);
CREATE INDEX IF NOT EXISTS idx_images_gcs_path ON images(gcs_path) WHERE gcs_path IS NOT NULL;

-- Update existing images to have storage_type 'local'
UPDATE images SET storage_type = 'local' WHERE storage_type IS NULL;

-- Create function to get preferred image URL (GCS first, then local fallback)
CREATE OR REPLACE FUNCTION get_preferred_image_url(
    gcs_url_param TEXT,
    file_path_param TEXT,
    fallback_base_url TEXT DEFAULT 'http://localhost:8008'
)
RETURNS TEXT AS $$
BEGIN
    -- Return GCS URL if available
    IF gcs_url_param IS NOT NULL AND gcs_url_param != '' THEN
        RETURN gcs_url_param;
    END IF;
    
    -- Fallback to local URL
    IF file_path_param IS NOT NULL AND file_path_param != '' THEN
        -- Extract filename from path
        RETURN fallback_base_url || '/images/' || 
               CASE 
                   WHEN file_path_param LIKE '%/%' THEN 
                       split_part(file_path_param, '/', -1)
                   ELSE 
                       file_path_param
               END;
    END IF;
    
    -- No URL available
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create function to migrate local images to GCS (for future use)
CREATE OR REPLACE FUNCTION migrate_image_to_gcs(
    image_id_param UUID,
    gcs_url_param TEXT,
    gcs_path_param TEXT
)
RETURNS VOID AS $$
BEGIN
    UPDATE images 
    SET 
        gcs_url = gcs_url_param,
        gcs_path = gcs_path_param,
        storage_type = CASE 
            WHEN file_path IS NOT NULL THEN 'hybrid'
            ELSE 'gcs'
        END,
        updated_at = TIMEZONE('utc'::text, now())
    WHERE id = image_id_param;
END;
$$ LANGUAGE plpgsql;

-- Create view for image URLs with preference logic
CREATE OR REPLACE VIEW image_urls AS
SELECT 
    i.*,
    get_preferred_image_url(i.gcs_url, i.file_path) as preferred_url,
    CASE 
        WHEN i.gcs_url IS NOT NULL THEN i.gcs_url
        ELSE NULL
    END as cloud_url,
    CASE 
        WHEN i.file_path IS NOT NULL THEN 
            'http://localhost:8008/images/' || 
            CASE 
                WHEN i.file_path LIKE '%/%' THEN 
                    split_part(i.file_path, '/', -1)
                ELSE 
                    i.file_path
            END
        ELSE NULL
    END as local_url
FROM images i;

-- Add comments for documentation
COMMENT ON COLUMN images.gcs_url IS 'Public URL for image stored in Google Cloud Storage';
COMMENT ON COLUMN images.gcs_path IS 'Path within GCS bucket (e.g., images/2025/06/25/filename.jpg)';
COMMENT ON COLUMN images.storage_type IS 'Storage location: local, gcs, or hybrid (both)';
COMMENT ON FUNCTION get_preferred_image_url IS 'Returns preferred image URL (GCS first, local fallback)';
COMMENT ON FUNCTION migrate_image_to_gcs IS 'Migrates an existing image record to include GCS information';
COMMENT ON VIEW image_urls IS 'View providing preferred, cloud, and local URLs for all images';

-- Create trigger to automatically update preferred URLs in article content
CREATE OR REPLACE FUNCTION update_article_image_urls()
RETURNS TRIGGER AS $$
DECLARE
    article_record RECORD;
    old_url TEXT;
    new_url TEXT;
    updated_content TEXT;
BEGIN
    -- Only process if GCS URL is being added/updated
    IF NEW.gcs_url IS DISTINCT FROM OLD.gcs_url AND NEW.gcs_url IS NOT NULL THEN
        -- Find articles that reference this image
        FOR article_record IN 
            SELECT DISTINCT a.id, a.content 
            FROM articles a
            WHERE a.content LIKE '%' || 
                CASE 
                    WHEN OLD.file_path LIKE '%/%' THEN 
                        split_part(OLD.file_path, '/', -1)
                    ELSE 
                        OLD.file_path
                END || '%'
        LOOP
            -- Construct old and new URLs
            old_url := 'http://localhost:8008/images/' || 
                CASE 
                    WHEN OLD.file_path LIKE '%/%' THEN 
                        split_part(OLD.file_path, '/', -1)
                    ELSE 
                        OLD.file_path
                END;
            new_url := NEW.gcs_url;
            
            -- Replace URLs in article content
            updated_content := REPLACE(article_record.content, old_url, new_url);
            
            -- Update article if content changed
            IF updated_content != article_record.content THEN
                UPDATE articles 
                SET 
                    content = updated_content,
                    updated_at = TIMEZONE('utc'::text, now())
                WHERE id = article_record.id;
                
                RAISE NOTICE 'Updated image URLs in article %', article_record.id;
            END IF;
        END LOOP;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic URL updates
DROP TRIGGER IF EXISTS trigger_update_article_image_urls ON images;
CREATE TRIGGER trigger_update_article_image_urls
    AFTER UPDATE ON images
    FOR EACH ROW EXECUTE FUNCTION update_article_image_urls();

-- Update realtime publication to include updated view
DROP PUBLICATION IF EXISTS supabase_realtime;
CREATE PUBLICATION supabase_realtime FOR TABLE 
  products, prices, organizations, organization_members, invitations,
  article_generation_flows, flow_steps, generated_articles_state, articles,
  images, image_placeholders;