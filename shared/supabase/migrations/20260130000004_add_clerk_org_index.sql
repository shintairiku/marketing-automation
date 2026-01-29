-- Add index on clerk_organization_id for efficient lookups from Clerk webhooks
CREATE INDEX IF NOT EXISTS idx_organizations_clerk_org_id
    ON organizations(clerk_organization_id);
