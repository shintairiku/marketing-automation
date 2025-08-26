/**
 * IMAGE PLACEHOLDERS FEATURE
 * This migration adds support for image placeholders in article generation
 * and image generation capabilities using Vertex AI Imagen 4.0
 */

-- Add image_mode column to generated_articles_state to track image generation mode
ALTER TABLE generated_articles_state 
ADD COLUMN IF NOT EXISTS image_mode BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS image_settings JSONB DEFAULT '{}'::jsonb;

-- Create images table to store generated/uploaded images
CREATE TABLE IF NOT EXISTS images (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  -- User who owns this image (using text for Clerk compatibility)
  user_id TEXT NOT NULL,
  -- Organization context (if applicable)
  organization_id UUID REFERENCES organizations(id),
  -- Article this image belongs to (if applicable)
  article_id UUID REFERENCES articles(id),
  -- Generation process this image was created during (if applicable)
  generation_process_id UUID REFERENCES generated_articles_state(id),
  -- Original filename (for uploaded images)
  original_filename TEXT,
  -- File path/URL where the image is stored
  file_path TEXT NOT NULL,
  -- Image type: 'uploaded' or 'generated'
  image_type TEXT CHECK (image_type IN ('uploaded', 'generated')) NOT NULL,
  -- Alt text for the image
  alt_text TEXT,
  -- Caption for the image
  caption TEXT,
  -- Original prompt used for generation (for generated images)
  generation_prompt TEXT,
  -- Generation parameters used (for generated images)
  generation_params JSONB,
  -- Image metadata (dimensions, file size, etc.)
  metadata JSONB DEFAULT '{}'::jsonb,
  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()) NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()) NOT NULL
);

-- Enable RLS on images table
ALTER TABLE images ENABLE ROW LEVEL SECURITY;

-- RLS Policies for images
-- Users can manage their own images
CREATE POLICY "Users can manage their own images" ON images
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- Organization members can view images in their organization
CREATE POLICY "Organization members can view organization images" ON images
  FOR SELECT USING (
    organization_id IS NOT NULL AND
    EXISTS (
      SELECT 1 FROM organization_members 
      WHERE organization_members.organization_id = images.organization_id 
      AND organization_members.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

-- Create image_placeholders table to track placeholders in articles
CREATE TABLE IF NOT EXISTS image_placeholders (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  -- Article this placeholder belongs to
  article_id UUID REFERENCES articles(id),
  -- Generation process this placeholder was created during (if applicable)
  generation_process_id UUID REFERENCES generated_articles_state(id),
  -- Placeholder identifier (unique within the article)
  placeholder_id TEXT NOT NULL,
  -- Description of the image (Japanese)
  description_jp TEXT NOT NULL,
  -- English prompt for image generation
  prompt_en TEXT NOT NULL,
  -- Position in the article content (for ordering)
  position_index INTEGER NOT NULL,
  -- Image that replaced this placeholder (if any)
  replaced_with_image_id UUID REFERENCES images(id),
  -- Status: 'pending', 'replaced', 'generating'
  status TEXT CHECK (status IN ('pending', 'replaced', 'generating')) DEFAULT 'pending',
  -- Additional metadata
  metadata JSONB DEFAULT '{}'::jsonb,
  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()) NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()) NOT NULL,
  
  -- Unique constraint on article_id + placeholder_id
  UNIQUE(article_id, placeholder_id)
);

-- Enable RLS on image_placeholders table
ALTER TABLE image_placeholders ENABLE ROW LEVEL SECURITY;

-- RLS Policies for image_placeholders
-- Users can manage placeholders for their own articles
CREATE POLICY "Users can manage placeholders for their own articles" ON image_placeholders
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM articles 
      WHERE articles.id = image_placeholders.article_id 
      AND articles.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_images_user_id ON images(user_id);
CREATE INDEX IF NOT EXISTS idx_images_article_id ON images(article_id);
CREATE INDEX IF NOT EXISTS idx_images_generation_process_id ON images(generation_process_id);
CREATE INDEX IF NOT EXISTS idx_images_image_type ON images(image_type);

CREATE INDEX IF NOT EXISTS idx_image_placeholders_article_id ON image_placeholders(article_id);
CREATE INDEX IF NOT EXISTS idx_image_placeholders_generation_process_id ON image_placeholders(generation_process_id);
CREATE INDEX IF NOT EXISTS idx_image_placeholders_status ON image_placeholders(status);

-- Add triggers for updated_at timestamps
CREATE TRIGGER update_images_updated_at
  BEFORE UPDATE ON images
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_image_placeholders_updated_at
  BEFORE UPDATE ON image_placeholders
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to extract image placeholders from article content
CREATE OR REPLACE FUNCTION extract_image_placeholders(
  article_content TEXT,
  process_id UUID DEFAULT NULL,
  article_id_param UUID DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
  placeholder_pattern TEXT := '<!-- IMAGE_PLACEHOLDER: ([^|]+)\|([^|]+)\|([^>]+) -->';
  match RECORD;
  counter INTEGER := 0;
BEGIN
  -- Extract all image placeholders using regex
  FOR match IN
    SELECT 
      (regexp_matches(article_content, placeholder_pattern, 'g'))[1] as placeholder_id,
      (regexp_matches(article_content, placeholder_pattern, 'g'))[2] as description_jp,
      (regexp_matches(article_content, placeholder_pattern, 'g'))[3] as prompt_en,
      (regexp_match_indices(article_content, placeholder_pattern, 'g'))[1] as position
  LOOP
    counter := counter + 1;
    
    -- Insert placeholder into image_placeholders table
    INSERT INTO image_placeholders (
      article_id, 
      generation_process_id, 
      placeholder_id, 
      description_jp, 
      prompt_en, 
      position_index
    ) VALUES (
      article_id_param,
      process_id,
      match.placeholder_id,
      match.description_jp,
      match.prompt_en,
      counter
    )
    ON CONFLICT (article_id, placeholder_id) 
    DO UPDATE SET
      description_jp = EXCLUDED.description_jp,
      prompt_en = EXCLUDED.prompt_en,
      position_index = EXCLUDED.position_index,
      updated_at = TIMEZONE('utc'::text, now());
  END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to replace placeholder with image in article content
CREATE OR REPLACE FUNCTION replace_placeholder_with_image(
  article_id_param UUID,
  placeholder_id_param TEXT,
  image_id_param UUID,
  image_url TEXT,
  alt_text_param TEXT DEFAULT ''
)
RETURNS VOID AS $$
DECLARE
  current_content TEXT;
  placeholder_pattern TEXT;
  replacement_html TEXT;
  updated_content TEXT;
BEGIN
  -- Get current article content
  SELECT content INTO current_content FROM articles WHERE id = article_id_param;
  
  -- Create placeholder pattern for this specific placeholder
  placeholder_pattern := '<!-- IMAGE_PLACEHOLDER: ' || placeholder_id_param || '\|[^>]+ -->';
  
  -- Create replacement HTML
  replacement_html := '<img src="' || image_url || '" alt="' || alt_text_param || '" class="article-image" />';
  
  -- Replace placeholder with image HTML
  updated_content := regexp_replace(current_content, placeholder_pattern, replacement_html, 'g');
  
  -- Update article content
  UPDATE articles SET content = updated_content WHERE id = article_id_param;
  
  -- Update placeholder status
  UPDATE image_placeholders 
  SET 
    replaced_with_image_id = image_id_param,
    status = 'replaced',
    updated_at = TIMEZONE('utc'::text, now())
  WHERE article_id = article_id_param AND placeholder_id = placeholder_id_param;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE images IS 'Stores uploaded and generated images for articles';
COMMENT ON TABLE image_placeholders IS 'Tracks image placeholders in articles before they are replaced with actual images';
COMMENT ON COLUMN generated_articles_state.image_mode IS 'Whether this generation process includes image placeholders';
COMMENT ON COLUMN generated_articles_state.image_settings IS 'Image generation settings and preferences';

-- Update realtime publication to include new tables
DROP PUBLICATION IF EXISTS supabase_realtime;
CREATE PUBLICATION supabase_realtime FOR TABLE 
  products, prices, organizations, organization_members, invitations,
  article_generation_flows, flow_steps, generated_articles_state, articles,
  images, image_placeholders;