-- Fix style_guide_templates user_id to use TEXT instead of UUID for Clerk compatibility

-- Drop existing RLS policies
DROP POLICY IF EXISTS "Users can manage their own style guide templates" ON style_guide_templates;
DROP POLICY IF EXISTS "Organization members can view organization style templates" ON style_guide_templates;
DROP POLICY IF EXISTS "Organization admins can manage organization style templates" ON style_guide_templates;

-- Drop foreign key constraint that references auth.users
ALTER TABLE style_guide_templates 
DROP CONSTRAINT IF EXISTS style_guide_templates_user_id_fkey;

-- Alter user_id column to TEXT
ALTER TABLE style_guide_templates 
ALTER COLUMN user_id TYPE text;

-- Recreate RLS policies with correct user_id handling
CREATE POLICY "Users can manage their own style guide templates" ON style_guide_templates
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

-- Organization members can view organization templates
CREATE POLICY "Organization members can view organization style templates" ON style_guide_templates
  FOR SELECT USING (
    organization_id IS NOT NULL AND
    EXISTS (
      SELECT 1 FROM organization_members 
      WHERE organization_members.organization_id = style_guide_templates.organization_id 
      AND organization_members.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

-- Organization admins can manage organization templates
CREATE POLICY "Organization admins can manage organization style templates" ON style_guide_templates
  FOR ALL USING (
    organization_id IS NOT NULL AND
    EXISTS (
      SELECT 1 FROM organization_members 
      WHERE organization_members.organization_id = style_guide_templates.organization_id 
      AND organization_members.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
      AND organization_members.role IN ('owner', 'admin')
    )
  );

-- Update realtime publication
DROP PUBLICATION IF EXISTS supabase_realtime;
CREATE PUBLICATION supabase_realtime FOR TABLE 
  products, prices, organizations, organization_members, invitations,
  article_generation_flows, flow_steps, generated_articles_state, articles, style_guide_templates;