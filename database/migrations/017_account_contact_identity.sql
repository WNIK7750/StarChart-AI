-- Enforce case-insensitive email identity at the database boundary.
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_accounts_email_normalized
ON user_accounts(lower(email))
WHERE email IS NOT NULL;
