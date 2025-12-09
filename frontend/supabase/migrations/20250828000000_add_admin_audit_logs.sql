-- Create admin audit logs table for tracking admin actions
CREATE TABLE admin_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    admin_user_id TEXT NOT NULL,
    admin_email TEXT NOT NULL,
    action TEXT NOT NULL,
    request_method TEXT NOT NULL,
    request_path TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    target_resource TEXT,
    details JSONB DEFAULT '{}',
    session_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX idx_admin_audit_logs_timestamp ON admin_audit_logs (timestamp);
CREATE INDEX idx_admin_audit_logs_admin_user_id ON admin_audit_logs (admin_user_id);
CREATE INDEX idx_admin_audit_logs_action ON admin_audit_logs (action);

-- Enable RLS (Row Level Security)
ALTER TABLE admin_audit_logs ENABLE ROW LEVEL SECURITY;

-- Create policy that only allows service role to access (admin-only data)
CREATE POLICY "Only service role can access admin audit logs" ON admin_audit_logs
    FOR ALL USING (auth.role() = 'service_role');