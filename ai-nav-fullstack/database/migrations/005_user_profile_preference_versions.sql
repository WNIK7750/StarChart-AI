ALTER TABLE user_profiles ADD COLUMN version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0);
ALTER TABLE user_preferences ADD COLUMN version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0);

