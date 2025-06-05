/**
 * PROMPT_TEMPLATES
 * Note: This table stores reusable prompt templates for flow steps.
 * Templates can be used across multiple flows and organizations.
 */
create table prompt_templates (
  -- UUID primary key
  id uuid default gen_random_uuid() primary key,
  -- Template name
  name text not null,
  -- Template content/prompt text
  content text not null,
  -- Description of what this template does
  description text,
  -- Timestamps
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS
alter table prompt_templates enable row level security;

-- RLS Policies for prompt_templates
-- All authenticated users can read prompt templates
create policy "Authenticated users can read prompt templates" on prompt_templates
  for select using (auth.role() = 'authenticated');

-- Only admins/system can manage prompt templates (for now)
-- In the future, this might be expanded to allow organization admins to create custom templates

/**
 * ARTICLE_GENERATION_FLOWS
 * Note: This table stores customizable article generation workflow definitions.
 * Flows can be organization-specific or user-specific templates.
 */
create table article_generation_flows (
  -- UUID primary key
  id uuid default gen_random_uuid() primary key,
  -- Organization this flow belongs to (nullable for user-specific flows)
  organization_id uuid references organizations(id) on delete cascade,
  -- User who created this flow (nullable for organization-wide flows)
  user_id uuid references auth.users on delete cascade,
  -- Flow name
  name text not null,
  -- Flow description
  description text,
  -- Whether this is a template flow that can be copied
  is_template boolean default false,
  -- Timestamps
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null,
  
  -- Constraint: flow must belong to either an organization or a user, but not both
  constraint flow_ownership_check check (
    (organization_id is not null and user_id is null) or
    (organization_id is null and user_id is not null)
  )
);

-- Enable RLS
alter table article_generation_flows enable row level security;

-- RLS Policies for article_generation_flows
-- Users can view and manage flows they created
create policy "Users can manage their own flows" on article_generation_flows
  for all using (auth.uid() = user_id);

-- Organization members can view organization flows
create policy "Organization members can view organization flows" on article_generation_flows
  for select using (
    organization_id is not null and
    exists (
      select 1 from organization_members 
      where organization_members.organization_id = article_generation_flows.organization_id 
      and organization_members.user_id = auth.uid()
    )
  );

-- Organization owners and admins can manage organization flows
create policy "Organization admins can manage organization flows" on article_generation_flows
  for all using (
    organization_id is not null and
    exists (
      select 1 from organization_members 
      where organization_members.organization_id = article_generation_flows.organization_id 
      and organization_members.user_id = auth.uid()
      and organization_members.role in ('owner', 'admin')
    )
  );

-- Everyone can view template flows
create policy "Anyone can view template flows" on article_generation_flows
  for select using (is_template = true);

/**
 * FLOW_STEPS
 * Note: This table defines the individual steps within article generation flows.
 * Each step specifies which agent to use, prompts, tools, and configuration.
 */
create type step_type as enum (
  'keyword_analysis',
  'persona_generation', 
  'theme_proposal',
  'research_planning',
  'research_execution',
  'research_synthesis',
  'outline_generation',
  'section_writing',
  'editing',
  'custom'
);

create table flow_steps (
  -- UUID primary key
  id uuid default gen_random_uuid() primary key,
  -- Flow this step belongs to
  flow_id uuid references article_generation_flows(id) on delete cascade not null,
  -- Order of this step in the flow
  step_order integer not null,
  -- Type of step
  step_type step_type not null,
  -- Agent name to use for this step
  agent_name text,
  -- Prompt template to use (optional)
  prompt_template_id uuid references prompt_templates(id),
  -- Tool configuration (JSON)
  tool_config jsonb,
  -- Expected output schema (JSON)
  output_schema jsonb,
  -- Whether this step requires user interaction
  is_interactive boolean default false,
  -- Whether this step can be skipped
  skippable boolean default false,
  -- Additional configuration (JSON)
  config jsonb,
  
  -- Unique constraint on flow_id + step_order
  unique(flow_id, step_order)
);

-- Enable RLS
alter table flow_steps enable row level security;

-- RLS Policies for flow_steps
-- Users can view steps for flows they have access to
create policy "Users can view flow steps they have access to" on flow_steps
  for select using (
    exists (
      select 1 from article_generation_flows 
      where article_generation_flows.id = flow_steps.flow_id
      and (
        -- User owns the flow
        article_generation_flows.user_id = auth.uid() or
        -- User is member of organization that owns the flow
        (article_generation_flows.organization_id is not null and
         exists (
           select 1 from organization_members 
           where organization_members.organization_id = article_generation_flows.organization_id 
           and organization_members.user_id = auth.uid()
         )) or
        -- Flow is a template
        article_generation_flows.is_template = true
      )
    )
  );

-- Users can manage steps for flows they can manage
create policy "Users can manage flow steps they can manage" on flow_steps
  for all using (
    exists (
      select 1 from article_generation_flows 
      where article_generation_flows.id = flow_steps.flow_id
      and (
        -- User owns the flow
        article_generation_flows.user_id = auth.uid() or
        -- User is admin of organization that owns the flow
        (article_generation_flows.organization_id is not null and
         exists (
           select 1 from organization_members 
           where organization_members.organization_id = article_generation_flows.organization_id 
           and organization_members.user_id = auth.uid()
           and organization_members.role in ('owner', 'admin')
         ))
      )
    )
  );

/**
 * GENERATED_ARTICLES_STATE
 * Note: This table persists the state of article generation processes.
 * It allows resuming generation flows and tracking progress.
 */
create type generation_status as enum (
  'in_progress',
  'user_input_required',
  'paused',
  'completed',
  'error',
  'cancelled'
);

create table generated_articles_state (
  -- UUID primary key (unique ID for each generation process)
  id uuid default gen_random_uuid() primary key,
  -- Flow being executed
  flow_id uuid references article_generation_flows(id) not null,
  -- User who initiated the generation
  user_id uuid references auth.users not null,
  -- Organization context (if applicable)
  organization_id uuid references organizations(id),
  -- Current step being executed
  current_step_id uuid references flow_steps(id),
  -- Overall status of the generation process
  status generation_status not null default 'in_progress',
  -- Article context (JSON - stores the ArticleContext data)
  article_context jsonb not null,
  -- Generated content at each step (JSON)
  generated_content jsonb,
  -- Final article ID (if generation completed successfully)
  article_id uuid, -- This will reference an articles table when it exists
  -- Error message (if status is 'error')
  error_message text,
  -- Timestamps
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS
alter table generated_articles_state enable row level security;

-- RLS Policies for generated_articles_state
-- Users can view and manage their own generation processes
create policy "Users can manage their own generation processes" on generated_articles_state
  for all using (auth.uid() = user_id);

-- Organization members can view generation processes in their organization
create policy "Organization members can view organization generations" on generated_articles_state
  for select using (
    organization_id is not null and
    exists (
      select 1 from organization_members 
      where organization_members.organization_id = generated_articles_state.organization_id 
      and organization_members.user_id = auth.uid()
    )
  );

/**
 * ARTICLES
 * Note: This table stores the final generated articles.
 * Updated to include organization and generation process references.
 */
create table articles (
  -- UUID primary key
  id uuid default gen_random_uuid() primary key,
  -- User who created the article
  user_id uuid references auth.users not null,
  -- Organization context (if applicable)
  organization_id uuid references organizations(id),
  -- Generation process that created this article
  generation_process_id uuid references generated_articles_state(id),
  -- Article title
  title text not null,
  -- Article content (HTML)
  content text not null,
  -- SEO keywords
  keywords text[],
  -- Target audience/persona
  target_audience text,
  -- Article status
  status text default 'draft',
  -- Timestamps
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS
alter table articles enable row level security;

-- RLS Policies for articles
-- Users can view and manage their own articles
create policy "Users can manage their own articles" on articles
  for all using (auth.uid() = user_id);

-- Organization members can view articles in their organization
create policy "Organization members can view organization articles" on articles
  for select using (
    organization_id is not null and
    exists (
      select 1 from organization_members 
      where organization_members.organization_id = articles.organization_id 
      and organization_members.user_id = auth.uid()
    )
  );

/**
 * TRIGGERS FOR UPDATED_AT
 */
-- Add triggers for updated_at timestamps
create trigger update_prompt_templates_updated_at
  before update on prompt_templates
  for each row execute function update_updated_at_column();

create trigger update_article_generation_flows_updated_at
  before update on article_generation_flows
  for each row execute function update_updated_at_column();

create trigger update_generated_articles_state_updated_at
  before update on generated_articles_state
  for each row execute function update_updated_at_column();

create trigger update_articles_updated_at
  before update on articles
  for each row execute function update_updated_at_column();

/**
 * DEFAULT FLOW TEMPLATES
 * Insert some default flow templates that users can copy and customize.
 */

-- Default SEO Article Generation Flow
insert into article_generation_flows (id, name, description, is_template, user_id, organization_id)
values (
  gen_random_uuid(),
  'Default SEO Article Generation',
  'Complete SEO article generation workflow with keyword analysis, persona development, research, and writing',
  true,
  null,
  null
);

-- Get the ID of the flow we just created for adding steps
do $$
declare
  default_flow_id uuid;
begin
  select id into default_flow_id 
  from article_generation_flows 
  where name = 'Default SEO Article Generation' and is_template = true;
  
  -- Insert default flow steps
  insert into flow_steps (flow_id, step_order, step_type, agent_name, is_interactive, skippable) values
  (default_flow_id, 1, 'keyword_analysis', 'serp_keyword_analysis_agent', false, false),
  (default_flow_id, 2, 'persona_generation', 'persona_generator_agent', true, false),
  (default_flow_id, 3, 'theme_proposal', 'theme_agent', true, false),
  (default_flow_id, 4, 'research_planning', 'research_planner_agent', true, false),
  (default_flow_id, 5, 'research_execution', 'researcher_agent', false, false),
  (default_flow_id, 6, 'research_synthesis', 'research_synthesizer_agent', false, false),
  (default_flow_id, 7, 'outline_generation', 'outline_agent', true, false),
  (default_flow_id, 8, 'section_writing', 'section_writer_agent', false, false),
  (default_flow_id, 9, 'editing', 'editor_agent', false, false);
end $$;

/**
 * REALTIME SUBSCRIPTIONS
 * Update realtime subscriptions to include new tables.
 */
drop publication if exists supabase_realtime;
create publication supabase_realtime for table 
  products, prices, organizations, organization_members, invitations,
  article_generation_flows, flow_steps, generated_articles_state, articles;