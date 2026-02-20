-- Contact Inquiries table for user support requests
CREATE TABLE IF NOT EXISTS contact_inquiries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'general',
  subject TEXT NOT NULL,
  message TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new',
  admin_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_contact_inquiries_user_id ON contact_inquiries(user_id);
CREATE INDEX IF NOT EXISTS idx_contact_inquiries_status ON contact_inquiries(status);
CREATE INDEX IF NOT EXISTS idx_contact_inquiries_created_at ON contact_inquiries(created_at DESC);

-- RLS
ALTER TABLE contact_inquiries ENABLE ROW LEVEL SECURITY;

-- Users can create inquiries (authenticated)
CREATE POLICY "Users can create inquiries"
  ON contact_inquiries FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- Users can read their own inquiries
CREATE POLICY "Users can read own inquiries"
  ON contact_inquiries FOR SELECT
  TO authenticated
  USING (user_id = auth.uid()::text);

-- Service role has full access (for admin operations)
CREATE POLICY "Service role full access"
  ON contact_inquiries FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
