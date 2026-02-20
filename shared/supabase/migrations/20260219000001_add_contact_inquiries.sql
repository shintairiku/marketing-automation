-- Contact inquiries table for user support
CREATE TABLE IF NOT EXISTS contact_inquiries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL,
  user_email text NOT NULL,
  user_name text,
  category text NOT NULL DEFAULT 'general',
  subject text NOT NULL,
  message text NOT NULL,
  status text NOT NULL DEFAULT 'new',
  admin_notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Index for efficient queries
CREATE INDEX idx_contact_inquiries_user_id ON contact_inquiries(user_id);
CREATE INDEX idx_contact_inquiries_status ON contact_inquiries(status);
CREATE INDEX idx_contact_inquiries_created_at ON contact_inquiries(created_at DESC);

-- RLS
ALTER TABLE contact_inquiries ENABLE ROW LEVEL SECURITY;

-- Users can view their own inquiries
CREATE POLICY "Users can view own inquiries"
  ON contact_inquiries FOR SELECT
  USING (auth.uid()::text = user_id);

-- Service role can do everything (backend uses service role key)
CREATE POLICY "Service role full access"
  ON contact_inquiries FOR ALL
  USING (true);

-- Comment
COMMENT ON TABLE contact_inquiries IS 'ユーザーからのお問い合わせ';
COMMENT ON COLUMN contact_inquiries.category IS 'カテゴリ: general, bug_report, feature_request, billing, other';
COMMENT ON COLUMN contact_inquiries.status IS 'ステータス: new, in_progress, resolved, closed';
