-- Fix user_id fields to support Clerk user IDs
-- Clerk uses user IDs like "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV" which are not valid UUIDs

-- STEP 1: Drop ALL policies from all tables to ensure clean slate
-- This is more comprehensive than trying to list each specific policy
DO $$ 
DECLARE
    rec record;
BEGIN
    -- Drop all policies from all tables
    FOR rec IN 
        SELECT schemaname, tablename, policyname 
        FROM pg_policies 
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', rec.policyname, rec.schemaname, rec.tablename);
    END LOOP;
END $$;

-- STEP 2: Drop foreign key constraints and primary key constraints
-- generated_articles_state table
ALTER TABLE generated_articles_state 
DROP CONSTRAINT IF EXISTS generated_articles_state_user_id_fkey;

-- articles table
ALTER TABLE articles 
DROP CONSTRAINT IF EXISTS articles_user_id_fkey;

-- organization_members table
ALTER TABLE organization_members 
DROP CONSTRAINT IF EXISTS organization_members_user_id_fkey;

ALTER TABLE organization_members 
DROP CONSTRAINT IF EXISTS organization_members_pkey;

-- organizations table
ALTER TABLE organizations 
DROP CONSTRAINT IF EXISTS organizations_owner_user_id_fkey;

-- invitations table
ALTER TABLE invitations 
DROP CONSTRAINT IF EXISTS invitations_invited_by_user_id_fkey;

-- article_generation_flows table
ALTER TABLE article_generation_flows 
DROP CONSTRAINT IF EXISTS article_generation_flows_user_id_fkey;

-- STEP 3: Alter column types
ALTER TABLE generated_articles_state 
ALTER COLUMN user_id TYPE text;

ALTER TABLE articles 
ALTER COLUMN user_id TYPE text;

ALTER TABLE organization_members 
ALTER COLUMN user_id TYPE text;

ALTER TABLE organizations 
ALTER COLUMN owner_user_id TYPE text;

ALTER TABLE invitations 
ALTER COLUMN invited_by_user_id TYPE text;

ALTER TABLE article_generation_flows 
ALTER COLUMN user_id TYPE text;

-- STEP 4: Re-add primary key constraint for organization_members
ALTER TABLE organization_members 
ADD CONSTRAINT organization_members_pkey PRIMARY KEY (organization_id, user_id);

-- STEP 5: Recreate RLS policies with updated user_id handling
CREATE POLICY "Users can manage their own generation processes" ON generated_articles_state
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Users can manage their own articles" ON articles
  FOR ALL USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Organization owners and admins can manage members" ON organization_members
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM organizations 
      WHERE organizations.id = organization_members.organization_id 
      AND organizations.owner_user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    ) OR
    EXISTS (
      SELECT 1 FROM organization_members om
      WHERE om.organization_id = organization_members.organization_id 
      AND om.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
      AND om.role IN ('owner', 'admin')
    )
  );

CREATE POLICY "Members can view organization memberships" ON organization_members
  FOR SELECT USING (
    user_id = current_setting('request.jwt.claims', true)::json->>'sub' OR
    EXISTS (
      SELECT 1 FROM organization_members om
      WHERE om.organization_id = organization_members.organization_id 
      AND om.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

CREATE POLICY "Organization owners can manage their organizations" ON organizations
  FOR ALL USING (owner_user_id = current_setting('request.jwt.claims', true)::json->>'sub');

CREATE POLICY "Organization members can view their organizations" ON organizations
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM organization_members 
      WHERE organization_members.organization_id = organizations.id 
      AND organization_members.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

CREATE POLICY "Organization members can view organization generations" ON generated_articles_state
  FOR SELECT USING (
    organization_id IS NOT NULL AND
    EXISTS (
      SELECT 1 FROM organization_members 
      WHERE organization_members.organization_id = generated_articles_state.organization_id 
      AND organization_members.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

CREATE POLICY "Organization members can view organization articles" ON articles
  FOR SELECT USING (
    organization_id IS NOT NULL AND
    EXISTS (
      SELECT 1 FROM organization_members 
      WHERE organization_members.organization_id = articles.organization_id 
      AND organization_members.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

CREATE POLICY "Organization owners and admins can manage invitations" ON invitations
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM organizations 
      WHERE organizations.id = invitations.organization_id 
      AND organizations.owner_user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    ) OR
    EXISTS (
      SELECT 1 FROM organization_members om
      WHERE om.organization_id = invitations.organization_id 
      AND om.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
      AND om.role IN ('owner', 'admin')
    )
  );

-- Note: Removing "Users can view invitations sent to them" policy as it would need 
-- more complex handling for Clerk users

CREATE POLICY "Organization owners and admins can view subscriptions" ON organization_subscriptions
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM organizations 
      WHERE organizations.id = organization_subscriptions.organization_id 
      AND organizations.owner_user_id = current_setting('request.jwt.claims', true)::json->>'sub'
    ) OR
    EXISTS (
      SELECT 1 FROM organization_members om
      WHERE om.organization_id = organization_subscriptions.organization_id 
      AND om.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
      AND om.role IN ('owner', 'admin')
    )
  );

CREATE POLICY "Users can view flows they have access to" ON article_generation_flows
  FOR SELECT USING (
    -- User owns the flow
    user_id = current_setting('request.jwt.claims', true)::json->>'sub' OR
    -- User is member of organization that owns the flow
    (organization_id IS NOT NULL AND
     EXISTS (
       SELECT 1 FROM organization_members 
       WHERE organization_members.organization_id = article_generation_flows.organization_id 
       AND organization_members.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
     )) OR
    -- Flow is a template
    is_template = true
  );

CREATE POLICY "Users can manage flows they own or have admin access to" ON article_generation_flows
  FOR ALL USING (
    -- User owns the flow
    user_id = current_setting('request.jwt.claims', true)::json->>'sub' OR
    -- User is admin of organization that owns the flow
    (organization_id IS NOT NULL AND
     EXISTS (
       SELECT 1 FROM organization_members 
       WHERE organization_members.organization_id = article_generation_flows.organization_id 
       AND organization_members.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
       AND role IN ('owner', 'admin')
     ))
  );

CREATE POLICY "Users can view flow steps they have access to" ON flow_steps
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM article_generation_flows 
      WHERE article_generation_flows.id = flow_steps.flow_id
      AND (
        -- User owns the flow
        article_generation_flows.user_id = current_setting('request.jwt.claims', true)::json->>'sub' OR
        -- User is member of organization that owns the flow
        (article_generation_flows.organization_id IS NOT NULL AND
         EXISTS (
           SELECT 1 FROM organization_members 
           WHERE organization_members.organization_id = article_generation_flows.organization_id 
           AND organization_members.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
         )) OR
        -- Flow is a template
        article_generation_flows.is_template = true
      )
    )
  );

CREATE POLICY "Users can manage flow steps they can manage" ON flow_steps
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM article_generation_flows 
      WHERE article_generation_flows.id = flow_steps.flow_id
      AND (
        -- User owns the flow
        article_generation_flows.user_id = current_setting('request.jwt.claims', true)::json->>'sub' OR
        -- User is admin of organization that owns the flow
        (article_generation_flows.organization_id IS NOT NULL AND
         EXISTS (
           SELECT 1 FROM organization_members 
           WHERE organization_members.organization_id = article_generation_flows.organization_id 
           AND organization_members.user_id = current_setting('request.jwt.claims', true)::json->>'sub'
           AND organization_members.role IN ('owner', 'admin')
         ))
      )
    )
  );

-- STEP 6: Update the automatic organization membership function
CREATE OR REPLACE FUNCTION handle_new_organization()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO organization_members (organization_id, user_id, role)
  VALUES (NEW.id, NEW.owner_user_id, 'owner');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER; 