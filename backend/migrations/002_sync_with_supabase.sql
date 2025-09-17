-- Migration 002: Sync authentication tables with Supabase
-- Created: 2024-09-16
-- Description: Ensure compatibility with Supabase auth while maintaining custom user system

-- Note: This migration assumes we're using our custom auth system alongside Supabase
-- The users table is separate from Supabase's auth.users table

-- Add indexes for better query performance with auth operations
CREATE INDEX IF NOT EXISTS idx_users_email_active ON users(email, is_active);
CREATE INDEX IF NOT EXISTS idx_users_role_active ON users(role, is_active);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login);

-- Add composite index for refresh token queries
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_expires ON refresh_tokens(user_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_revoked ON refresh_tokens(token, revoked);

-- Create function to clean up expired refresh tokens
CREATE OR REPLACE FUNCTION cleanup_expired_refresh_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM refresh_tokens
    WHERE expires_at < NOW() OR revoked = TRUE;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Add RLS (Row Level Security) policies if using Supabase
-- Note: These are optional and depend on your Supabase setup

-- Enable RLS on users table (optional, for Supabase compatibility)
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create policy for users to read their own data
-- CREATE POLICY "Users can read own data" ON users
--     FOR SELECT USING (auth.uid()::text = id::text);

-- Create policy for users to update their own data
-- CREATE POLICY "Users can update own data" ON users
--     FOR UPDATE USING (auth.uid()::text = id::text);

-- Add constraint to ensure email uniqueness (case insensitive)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique_lower
ON users (LOWER(email));

-- Add constraint to ensure username uniqueness (case insensitive)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique_lower
ON users (LOWER(username));

-- Add check constraint for valid roles
ALTER TABLE users ADD CONSTRAINT IF NOT EXISTS chk_user_role
CHECK (role IN ('user', 'admin', 'scraper'));

-- Add check constraint for valid email format (basic)
ALTER TABLE users ADD CONSTRAINT IF NOT EXISTS chk_user_email_format
CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- Create view for active users (commonly queried)
CREATE OR REPLACE VIEW active_users AS
SELECT
    id,
    email,
    username,
    full_name,
    role,
    is_verified,
    created_at,
    last_login
FROM users
WHERE is_active = TRUE;

-- Create view for user session info
CREATE OR REPLACE VIEW user_sessions AS
SELECT
    u.id as user_id,
    u.email,
    u.username,
    u.role,
    rt.token,
    rt.expires_at,
    rt.created_at as session_created,
    rt.user_agent,
    rt.ip_address,
    rt.revoked
FROM users u
JOIN refresh_tokens rt ON u.id = rt.user_id
WHERE u.is_active = TRUE;

-- Add comments for documentation
COMMENT ON TABLE users IS 'Custom user authentication table for JWT-based auth system';
COMMENT ON TABLE refresh_tokens IS 'JWT refresh tokens for session management';
COMMENT ON COLUMN users.role IS 'User role: user, admin, or scraper';
COMMENT ON COLUMN users.is_verified IS 'Whether user email has been verified';
COMMENT ON COLUMN refresh_tokens.revoked IS 'Whether token has been manually revoked';

-- Create maintenance function to update user statistics
CREATE OR REPLACE FUNCTION update_user_stats()
RETURNS TABLE(
    total_users INTEGER,
    active_users INTEGER,
    verified_users INTEGER,
    admin_users INTEGER,
    scraper_users INTEGER,
    recent_logins INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*)::INTEGER FROM users) as total_users,
        (SELECT COUNT(*)::INTEGER FROM users WHERE is_active = TRUE) as active_users,
        (SELECT COUNT(*)::INTEGER FROM users WHERE is_verified = TRUE) as verified_users,
        (SELECT COUNT(*)::INTEGER FROM users WHERE role = 'admin') as admin_users,
        (SELECT COUNT(*)::INTEGER FROM users WHERE role = 'scraper') as scraper_users,
        (SELECT COUNT(*)::INTEGER FROM users WHERE last_login > NOW() - INTERVAL '24 hours') as recent_logins;
END;
$$ LANGUAGE plpgsql;