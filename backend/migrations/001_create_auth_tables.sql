-- Migration 001: Create authentication tables
-- Created: 2024-09-16
-- Description: Create users and refresh_tokens tables for JWT authentication

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),

    -- User status
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE NOT NULL,
    is_superuser BOOLEAN DEFAULT FALSE NOT NULL,

    -- Roles and permissions
    role VARCHAR(50) DEFAULT 'user' NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    last_login TIMESTAMPTZ,

    -- Verification tokens
    verification_token VARCHAR(255),
    reset_token VARCHAR(255),
    reset_token_expires TIMESTAMPTZ
);

-- Create refresh_tokens table
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    token VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    revoked BOOLEAN DEFAULT FALSE NOT NULL,

    -- Session metadata
    user_agent TEXT,
    ip_address VARCHAR(45),

    -- Foreign key constraint
    CONSTRAINT fk_refresh_tokens_user_id
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token);
CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(reset_token);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON refresh_tokens(token);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_revoked ON refresh_tokens(revoked);

-- Create function to update updated_at automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for users table
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: Admin123!)
-- Note: In production, change this password immediately
INSERT INTO users (
    email,
    username,
    hashed_password,
    full_name,
    is_active,
    is_verified,
    is_superuser,
    role
) VALUES (
    'admin@arbitraje.com',
    'admin',
    '$2b$12$LQv3c1yqBPVHmEQrOk8A9eNpJNZDOsq6m5pGHSd5g6CYhC4GXdnXK', -- Admin123!
    'System Administrator',
    TRUE,
    TRUE,
    TRUE,
    'admin'
) ON CONFLICT (email) DO NOTHING;

-- Add some sample users for testing (only in development)
INSERT INTO users (
    email,
    username,
    hashed_password,
    full_name,
    role
) VALUES
(
    'scraper@arbitraje.com',
    'scraper_user',
    '$2b$12$LQv3c1yqBPVHmEQrOk8A9eNpJNZDOsq6m5pGHSd5g6CYhC4GXdnXK', -- Admin123!
    'Scraper Service Account',
    'scraper'
),
(
    'user@arbitraje.com',
    'regular_user',
    '$2b$12$LQv3c1yqBPVHmEQrOk8A9eNpJNZDOsq6m5pGHSd5g6CYhC4GXdnXK', -- Admin123!
    'Regular User',
    'user'
) ON CONFLICT (email) DO NOTHING;