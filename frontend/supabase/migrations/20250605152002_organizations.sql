/**
 * ORGANIZATIONS
 * Note: This table contains organization data for team-based functionality.
 * Organizations can have multiple members and manage their own subscriptions.
 */
create table organizations (
  -- UUID primary key
  id uuid default gen_random_uuid() primary key,
  -- Organization name
  name text not null,
  -- Reference to the organization owner (auth.users)
  owner_user_id uuid references auth.users not null,
  -- Clerk organization ID for Clerk integration (optional)
  clerk_organization_id text unique,
  -- Stripe customer ID for billing (optional)
  stripe_customer_id text,
  -- Timestamps
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS
alter table organizations enable row level security;

-- RLS Policies for organizations
-- Owners can do everything with their organizations
create policy "Organization owners can manage their organizations" on organizations
  for all using (auth.uid() = owner_user_id);

/**
 * ORGANIZATION_MEMBERS
 * Note: This table manages the relationship between users and organizations.
 * It stores membership information including roles.
 */
create type organization_role as enum ('owner', 'admin', 'member');

create table organization_members (
  -- Composite primary key
  organization_id uuid references organizations(id) on delete cascade,
  user_id uuid references auth.users on delete cascade,
  primary key (organization_id, user_id),
  -- Role within the organization
  role organization_role not null default 'member',
  -- Clerk membership ID for Clerk integration (optional)
  clerk_membership_id text,
  -- When the user joined the organization
  joined_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS
alter table organization_members enable row level security;

-- RLS Policies for organization_members
-- Organization owners and admins can manage members
create policy "Organization owners and admins can manage members" on organization_members
  for all using (
    exists (
      select 1 from organizations 
      where organizations.id = organization_members.organization_id 
      and organizations.owner_user_id = auth.uid()
    ) or
    exists (
      select 1 from organization_members om
      where om.organization_id = organization_members.organization_id 
      and om.user_id = auth.uid() 
      and om.role in ('owner', 'admin')
    )
  );

-- Members can view their own membership and other members in their organizations
create policy "Members can view organization memberships" on organization_members
  for select using (
    user_id = auth.uid() or
    exists (
      select 1 from organization_members om
      where om.organization_id = organization_members.organization_id 
      and om.user_id = auth.uid()
    )
  );

/**
 * INVITATIONS
 * Note: This table manages invitations to join organizations.
 */
create type invitation_status as enum ('pending', 'accepted', 'declined', 'expired');

create table invitations (
  -- UUID primary key
  id uuid default gen_random_uuid() primary key,
  -- Organization being invited to
  organization_id uuid references organizations(id) on delete cascade not null,
  -- Email address of the invitee
  email text not null,
  -- Role to be assigned when invitation is accepted
  role organization_role not null default 'member',
  -- Current status of the invitation
  status invitation_status not null default 'pending',
  -- User who sent the invitation
  invited_by_user_id uuid references auth.users not null,
  -- Unique token for accepting the invitation
  token text unique not null default encode(gen_random_bytes(32), 'hex'),
  -- When the invitation expires
  expires_at timestamp with time zone default (timezone('utc'::text, now()) + interval '7 days') not null,
  -- Timestamps
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS
alter table invitations enable row level security;

-- RLS Policies for invitations
-- Organization owners and admins can manage invitations for their organizations
create policy "Organization owners and admins can manage invitations" on invitations
  for all using (
    exists (
      select 1 from organizations 
      where organizations.id = invitations.organization_id 
      and organizations.owner_user_id = auth.uid()
    ) or
    exists (
      select 1 from organization_members om
      where om.organization_id = invitations.organization_id 
      and om.user_id = auth.uid() 
      and om.role in ('owner', 'admin')
    )
  );

-- Invited users can view invitations sent to their email
create policy "Users can view invitations sent to them" on invitations
  for select using (
    email = (select email from auth.users where auth.users.id = auth.uid())
  );

/**
 * ORGANIZATION_SUBSCRIPTIONS
 * Note: This table manages Stripe subscriptions at the organization level.
 * This replaces individual user subscriptions for team plans.
 */
create table organization_subscriptions (
  -- Subscription ID from Stripe
  id text primary key,
  -- Organization this subscription belongs to
  organization_id uuid references organizations(id) on delete cascade not null,
  -- Subscription status
  status subscription_status not null,
  -- Metadata from Stripe
  metadata jsonb,
  -- Price ID from Stripe
  price_id text references prices,
  -- Number of seats/users covered by this subscription
  quantity integer not null default 1,
  -- If true the subscription has been canceled by the user and will be deleted at the end of the billing period
  cancel_at_period_end boolean default false,
  -- Timestamps (same structure as individual subscriptions)
  created timestamp with time zone default timezone('utc'::text, now()) not null,
  current_period_start timestamp with time zone default timezone('utc'::text, now()) not null,
  current_period_end timestamp with time zone default timezone('utc'::text, now()) not null,
  ended_at timestamp with time zone,
  cancel_at timestamp with time zone,
  canceled_at timestamp with time zone,
  trial_start timestamp with time zone,
  trial_end timestamp with time zone
);

-- Enable RLS
alter table organization_subscriptions enable row level security;

-- RLS Policies for organization_subscriptions
-- Organization owners and admins can view subscription data
create policy "Organization owners and admins can view subscriptions" on organization_subscriptions
  for select using (
    exists (
      select 1 from organizations 
      where organizations.id = organization_subscriptions.organization_id 
      and organizations.owner_user_id = auth.uid()
    ) or
    exists (
      select 1 from organization_members om
      where om.organization_id = organization_subscriptions.organization_id 
      and om.user_id = auth.uid() 
      and om.role in ('owner', 'admin')
    )
  );

-- Only system (via service role) can insert/update/delete subscription data
-- This will be handled by Stripe webhooks and backend services

/**
 * TRIGGERS FOR UPDATED_AT
 */
-- Function to update updated_at timestamp
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = timezone('utc'::text, now());
  return new;
end;
$$ language plpgsql;

-- Trigger for organizations table
create trigger update_organizations_updated_at
  before update on organizations
  for each row execute function update_updated_at_column();

/**
 * AUTOMATIC ORGANIZATION MEMBERSHIP FOR OWNERS
 * When an organization is created, automatically add the owner as a member with 'owner' role.
 */
create or replace function handle_new_organization()
returns trigger as $$
begin
  insert into organization_members (organization_id, user_id, role)
  values (new.id, new.owner_user_id, 'owner');
  return new;
end;
$$ language plpgsql security definer;

create trigger on_organization_created
  after insert on organizations
  for each row execute function handle_new_organization();

-- Add the member view policy after organization_members table is created
create policy "Organization members can view their organizations" on organizations
  for select using (
    exists (
      select 1 from organization_members 
      where organization_members.organization_id = organizations.id 
      and organization_members.user_id = auth.uid()
    )
  );

/**
 * REALTIME SUBSCRIPTIONS
 * Allow realtime listening on organization-related tables for members.
 */
drop publication if exists supabase_realtime;
create publication supabase_realtime for table products, prices, organizations, organization_members, invitations;