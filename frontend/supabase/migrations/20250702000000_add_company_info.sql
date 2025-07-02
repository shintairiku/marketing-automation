/**
 * COMPANY INFO FEATURE
 * This migration adds company information management for users
 * to store company details that will be used in SEO article generation
 */

-- Create company_info table
CREATE TABLE IF NOT EXISTS company_info (
  id TEXT PRIMARY KEY DEFAULT (gen_random_uuid()::text),
  -- User who owns this company (using text for Clerk compatibility)
  user_id TEXT NOT NULL,
  
  -- Required fields
  name VARCHAR(200) NOT NULL,
  website_url VARCHAR(500) NOT NULL,
  description TEXT NOT NULL,
  usp TEXT NOT NULL,
  target_persona VARCHAR(50) NOT NULL,
  
  -- Default company setting
  is_default BOOLEAN DEFAULT FALSE NOT NULL,
  
  -- Optional detailed settings
  brand_slogan VARCHAR(200),
  target_keywords VARCHAR(500),
  industry_terms VARCHAR(500),
  avoid_terms VARCHAR(500),
  popular_articles TEXT,
  target_area VARCHAR(200),
  
  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()) NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, now()) NOT NULL
);

-- Enable RLS on company_info table
ALTER TABLE company_info ENABLE ROW LEVEL SECURITY;

-- RLS Policies for company_info
-- Users can manage their own company information
CREATE POLICY "Users can manage their own company info" ON company_info
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_company_info_user_id ON company_info(user_id);
CREATE INDEX IF NOT EXISTS idx_company_info_user_default ON company_info(user_id, is_default);

-- Add trigger for updated_at timestamp
CREATE TRIGGER update_company_info_updated_at
  BEFORE UPDATE ON company_info
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE company_info IS 'Stores company information for users to use in SEO article generation';
COMMENT ON COLUMN company_info.user_id IS 'Clerk user ID who owns this company information';
COMMENT ON COLUMN company_info.name IS 'Company name';
COMMENT ON COLUMN company_info.website_url IS 'Company website URL';
COMMENT ON COLUMN company_info.description IS 'Company description/overview';
COMMENT ON COLUMN company_info.usp IS 'Unique Selling Proposition - company strengths and differentiators';
COMMENT ON COLUMN company_info.target_persona IS 'Target customer persona';
COMMENT ON COLUMN company_info.is_default IS 'Whether this is the default company for the user';
COMMENT ON COLUMN company_info.brand_slogan IS 'Brand slogan or catchphrase (optional)';
COMMENT ON COLUMN company_info.target_keywords IS 'Keywords for SEO targeting (optional)';
COMMENT ON COLUMN company_info.industry_terms IS 'Industry-specific terms to use (optional)';
COMMENT ON COLUMN company_info.avoid_terms IS 'Terms to avoid in content (optional)';
COMMENT ON COLUMN company_info.popular_articles IS 'Popular article titles/URLs for reference (optional)';
COMMENT ON COLUMN company_info.target_area IS 'Target geographic area or local keywords (optional)';

-- Update realtime publication to include the new table
DROP PUBLICATION IF EXISTS supabase_realtime;
CREATE PUBLICATION supabase_realtime FOR TABLE 
  products, prices, organizations, organization_members, invitations,
  article_generation_flows, flow_steps, generated_articles_state, articles,
  images, image_placeholders, company_info;