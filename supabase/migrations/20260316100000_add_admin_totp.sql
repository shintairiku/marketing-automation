-- Admin TOTP (Time-based One-Time Password) secrets table
-- Custom TOTP system for admin page protection

CREATE TABLE IF NOT EXISTS public.admin_totp_secrets (
    id uuid DEFAULT extensions.uuid_generate_v4() PRIMARY KEY,
    user_id text NOT NULL UNIQUE,
    encrypted_secret text NOT NULL,
    is_confirmed boolean DEFAULT false NOT NULL,
    backup_codes jsonb DEFAULT '[]'::jsonb NOT NULL,
    failed_attempts integer DEFAULT 0 NOT NULL,
    locked_until timestamptz,
    last_failed_at timestamptz,
    created_at timestamptz DEFAULT now() NOT NULL,
    updated_at timestamptz DEFAULT now() NOT NULL,
    last_verified_at timestamptz,
    reset_at timestamptz,
    reset_by text
);

ALTER TABLE public.admin_totp_secrets ENABLE ROW LEVEL SECURITY;

-- service_role has full access (backend uses service_role key)
CREATE POLICY "service_role_full_access" ON public.admin_totp_secrets
    FOR ALL USING (true) WITH CHECK (true);

CREATE INDEX idx_admin_totp_user_id ON public.admin_totp_secrets(user_id);
