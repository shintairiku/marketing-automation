/**
 * STYLE_GUIDE_TEMPLATES
 * This migration adds style guide templates functionality
 */

-- Create enum for template types
CREATE TYPE style_template_type AS ENUM (
  'writing_tone',
  'vocabulary',
  'structure',
  'branding',
  'seo_focus',
  'custom'
);

-- Create style guide templates table
CREATE TABLE style_guide_templates (
  -- UUID primary key
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  -- User who created this template
  user_id UUID REFERENCES auth.users NOT NULL,
  -- Organization this template belongs to (nullable for personal templates)
  organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  -- Template name
  name TEXT NOT NULL,
  -- Template description
  description TEXT,
  -- Template type category
  template_type style_template_type DEFAULT 'custom',
  -- Template content/settings
  settings JSONB NOT NULL DEFAULT '{}'::jsonb,
  -- Whether this is active/enabled
  is_active BOOLEAN DEFAULT true,
  -- Whether this is the default template for the user/org
  is_default BOOLEAN DEFAULT false,
  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE style_guide_templates ENABLE ROW LEVEL SECURITY;

-- RLS Policies for style_guide_templates
-- Users can manage their own templates
CREATE POLICY "Users can manage their own style guide templates" ON style_guide_templates
  FOR ALL USING (auth.uid()::text = user_id::text);

-- Organization members can view organization templates
CREATE POLICY "Organization members can view organization style templates" ON style_guide_templates
  FOR SELECT USING (
    organization_id IS NOT NULL AND
    EXISTS (
      SELECT 1 FROM organization_members 
      WHERE organization_members.organization_id::text = style_guide_templates.organization_id::text 
      AND organization_members.user_id::text = auth.uid()::text
    )
  );

-- Organization admins can manage organization templates
CREATE POLICY "Organization admins can manage organization style templates" ON style_guide_templates
  FOR ALL USING (
    organization_id IS NOT NULL AND
    EXISTS (
      SELECT 1 FROM organization_members 
      WHERE organization_members.organization_id::text = style_guide_templates.organization_id::text 
      AND organization_members.user_id::text = auth.uid()::text
      AND organization_members.role IN ('owner', 'admin')
    )
  );

-- Add triggers for updated_at timestamps
CREATE TRIGGER update_style_guide_templates_updated_at
  BEFORE UPDATE ON style_guide_templates
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add index for performance
CREATE INDEX idx_style_guide_templates_user_id ON style_guide_templates(user_id);
CREATE INDEX idx_style_guide_templates_org_id ON style_guide_templates(organization_id);
CREATE INDEX idx_style_guide_templates_active ON style_guide_templates(is_active) WHERE is_active = true;

-- Function to ensure only one default template per user/organization
CREATE OR REPLACE FUNCTION ensure_single_default_style_template()
RETURNS TRIGGER AS $$
BEGIN
  -- If setting this template as default, unset all other defaults for the same user/org
  IF NEW.is_default = true THEN
    -- For personal templates
    IF NEW.organization_id IS NULL THEN
      UPDATE style_guide_templates 
      SET is_default = false 
      WHERE user_id = NEW.user_id 
        AND organization_id IS NULL 
        AND id != NEW.id 
        AND is_default = true;
    -- For organization templates
    ELSE
      UPDATE style_guide_templates 
      SET is_default = false 
      WHERE organization_id = NEW.organization_id 
        AND id != NEW.id 
        AND is_default = true;
    END IF;
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for default template management
CREATE TRIGGER ensure_single_default_style_template_trigger
  BEFORE INSERT OR UPDATE ON style_guide_templates
  FOR EACH ROW 
  WHEN (NEW.is_default = true)
  EXECUTE FUNCTION ensure_single_default_style_template();

-- Add style guide template reference to generated_articles_state
ALTER TABLE generated_articles_state 
ADD COLUMN style_template_id UUID REFERENCES style_guide_templates(id);

-- Add index for the new column
CREATE INDEX idx_generated_articles_state_style_template ON generated_articles_state(style_template_id);

-- Comments for documentation
COMMENT ON TABLE style_guide_templates IS 'Store reusable style guide templates for article generation';
COMMENT ON COLUMN style_guide_templates.settings IS 'JSON object containing style guide configuration (tone, vocabulary, structure, etc.)';
COMMENT ON COLUMN style_guide_templates.template_type IS 'Category of the style template for organization';
COMMENT ON COLUMN style_guide_templates.is_default IS 'Whether this template is the default for the user/organization';

-- Insert a default system template (optional)
INSERT INTO style_guide_templates (
  id, 
  user_id, 
  organization_id, 
  name, 
  description, 
  template_type, 
  settings, 
  is_active, 
  is_default
) 
SELECT 
  gen_random_uuid(),
  id,
  NULL,
  'デフォルトスタイル',
  '標準的な記事作成スタイル。親しみやすく、分かりやすい文章で、読者に寄り添うトーン。',
  'writing_tone',
  jsonb_build_object(
    'tone', '親しみやすく分かりやすい',
    'style', 'ですます調',
    'approach', '読者に寄り添う',
    'vocabulary', '専門用語を避け、簡単な言葉で説明',
    'structure', '見出しを使って情報を整理',
    'special_instructions', '具体例や体験談を交えて説得力を持たせる'
  ),
  true,
  true
FROM auth.users 
WHERE email IS NOT NULL -- Only for existing users
LIMIT 0; -- Set to 0 to disable auto-creation, change to remove LIMIT to enable

-- Update realtime publication to include the new table
DROP PUBLICATION IF EXISTS supabase_realtime;
CREATE PUBLICATION supabase_realtime FOR TABLE 
  products, prices, organizations, organization_members, invitations,
  article_generation_flows, flow_steps, generated_articles_state, articles, style_guide_templates;