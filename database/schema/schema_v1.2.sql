-- ============================================
-- AgriProfit Database Schema v1.2
-- PostgreSQL 14+
-- Production-Ready with All Fixes Applied
-- ============================================
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- ============================================
-- UTILITY FUNCTIONS
-- ============================================
-- Function: Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
-- Function: Auto-normalize district to title case
CREATE OR REPLACE FUNCTION normalize_district()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.district IS NOT NULL THEN
        NEW.district = INITCAP(TRIM(NEW.district));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
-- ============================================
-- TABLE: users
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number VARCHAR(10) NOT NULL
        CHECK (phone_number ~ '^[6-9][0-9]{9}$'),
    role VARCHAR(20) NOT NULL 
        CHECK (role IN ('farmer', 'admin')),
    district TEXT,
    language VARCHAR(10) NOT NULL DEFAULT 'en'
    CHECK (language IN ('en', 'ml')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);
-- Phone numbers stored without country code (India only)

-- Indexes for users
CREATE UNIQUE INDEX idx_users_phone_active
    ON users(phone_number)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_users_district 
    ON users(district);
CREATE INDEX idx_users_role 
    ON users(role);
-- Triggers for users
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER normalize_users_district
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION normalize_district();
-- ============================================
-- TABLE: otp_requests
-- ============================================
CREATE TABLE otp_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number VARCHAR(10) NOT NULL
        CHECK (phone_number ~ '^[6-9][0-9]{9}$'),
    otp_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
    CHECK (expires_at > created_at)

);
-- Indexes for otp_requests
CREATE INDEX idx_otp_phone_created
    ON otp_requests(phone_number, created_at DESC);
CREATE INDEX idx_otp_expires_at 
    ON otp_requests(expires_at);
-- ============================================
-- TABLE: commodities
-- ============================================
CREATE TABLE commodities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    name_local VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
-- Triggers for commodities
CREATE TRIGGER update_commodities_updated_at
    BEFORE UPDATE ON commodities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
-- ============================================
-- TABLE: price_history
-- ============================================
CREATE TABLE price_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    commodity_id UUID NOT NULL 
        REFERENCES commodities(id) ON DELETE CASCADE,
    mandi_name TEXT NOT NULL,
    price_date DATE NOT NULL,
    price DECIMAL(10,2) NOT NULL 
        CHECK (price >= 0),
    unit VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (commodity_id, mandi_name, price_date)
);
-- Indexes for price_history
CREATE INDEX idx_price_history_main
    ON price_history(commodity_id, mandi_name, price_date DESC);
CREATE INDEX idx_price_history_date
    ON price_history(price_date DESC);
-- Triggers for price_history
CREATE TRIGGER update_price_history_updated_at
    BEFORE UPDATE ON price_history
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
-- ============================================
-- TABLE: price_forecasts
-- ============================================
CREATE TABLE price_forecasts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    commodity_id UUID NOT NULL 
        REFERENCES commodities(id) ON DELETE CASCADE,
    mandi_name TEXT NOT NULL,
    forecast_date DATE NOT NULL,
    forecasted_price DECIMAL(10,2) NOT NULL 
        CHECK (forecasted_price >= 0),
    confidence_score DECIMAL(5,2) NOT NULL
        CHECK (confidence_score BETWEEN 0 AND 100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (commodity_id, mandi_name, forecast_date)
);
-- Indexes for price_forecasts
CREATE INDEX idx_price_forecasts_main
    ON price_forecasts(commodity_id, mandi_name, forecast_date DESC);
CREATE INDEX idx_price_forecasts_date
    ON price_forecasts(forecast_date);
-- Triggers for price_forecasts
CREATE TRIGGER update_price_forecasts_updated_at
    BEFORE UPDATE ON price_forecasts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
-- ============================================
-- TABLE: community_posts
-- ============================================
CREATE TABLE community_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL 
        REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    post_type VARCHAR(20) NOT NULL 
        CHECK (post_type IN ('normal', 'alert')),
    district TEXT,
    is_admin_override BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);
-- Indexes for community_posts
CREATE INDEX idx_posts_district_created
    ON community_posts(district, created_at DESC);
CREATE INDEX idx_posts_type_created
    ON community_posts(post_type, created_at DESC);
CREATE INDEX idx_posts_user_created
    ON community_posts(user_id, created_at DESC)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_posts_active
    ON community_posts(created_at DESC)
    WHERE deleted_at IS NULL;
-- Triggers for community_posts
CREATE TRIGGER update_community_posts_updated_at
    BEFORE UPDATE ON community_posts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER normalize_posts_district
    BEFORE INSERT OR UPDATE ON community_posts
    FOR EACH ROW
    EXECUTE FUNCTION normalize_district();
-- ============================================
-- TABLE: notifications
-- ============================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL 
        REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID 
        REFERENCES community_posts(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    read_at TIMESTAMP,
    CONSTRAINT check_read_at_consistency CHECK (
        (is_read = FALSE AND read_at IS NULL) OR
        (is_read = TRUE AND read_at IS NOT NULL)
    )
);
-- Indexes for notifications
CREATE INDEX idx_notifications_user_read_created
    ON notifications(user_id, is_read, created_at DESC);
CREATE INDEX idx_notifications_user_created
    ON notifications(user_id, created_at DESC);
CREATE INDEX idx_notifications_post_id
    ON notifications(post_id)
    WHERE post_id IS NOT NULL;
-- ============================================
-- TABLE: admin_actions
-- ============================================
CREATE TABLE admin_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admin_id UUID NOT NULL 
        REFERENCES users(id) ON DELETE RESTRICT,
    action_type VARCHAR(50) NOT NULL,
    action_metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
-- Indexes for admin_actions
CREATE INDEX idx_admin_actions_admin_created
    ON admin_actions(admin_id, created_at DESC);
CREATE INDEX idx_admin_actions_type_created
    ON admin_actions(action_type, created_at DESC);
CREATE INDEX idx_admin_actions_metadata
    ON admin_actions USING GIN(action_metadata);
-- ============================================
-- INITIAL DATA
-- ============================================
-- Insert sample commodities
INSERT INTO commodities (name, name_local) VALUES
    ('Rice', 'चावल'),
    ('Wheat', 'गेहूं'),
    ('Tomato', 'टमाटर'),
    ('Onion', 'प्याज'),
    ('Potato', 'आलू'),
    ('Cotton', 'कपास'),
    ('Sugarcane', 'गन्ना'),
    ('Maize', 'मक्का');
-- Insert bootstrap admin user (CHANGE PHONE NUMBER IN PRODUCTION)
INSERT INTO users (phone_number, role, district, language)
VALUES ('9999999999', 'admin', 'Delhi', 'en');
-- ============================================
-- MAINTENANCE FUNCTIONS
-- ============================================
-- Function: Cleanup expired OTPs
CREATE OR REPLACE FUNCTION cleanup_expired_otps()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM otp_requests
    WHERE created_at < NOW() - INTERVAL '24 hours';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
-- Function: Archive old read notifications
CREATE OR REPLACE FUNCTION archive_old_notifications()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM notifications
    WHERE is_read = TRUE
      AND created_at < NOW() - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
-- ============================================
-- MONITORING VIEWS
-- ============================================
-- View: Active users by role
CREATE OR REPLACE VIEW v_active_users_summary AS
SELECT 
    role,
    COUNT(*) as total_users,
    COUNT(DISTINCT district) as unique_districts
FROM users
WHERE deleted_at IS NULL
GROUP BY role;
-- View: Recent price updates
CREATE OR REPLACE VIEW v_recent_price_updates AS
SELECT 
    c.name as commodity_name,
    ph.mandi_name,
    ph.price_date,
    ph.price,
    ph.unit,
    ph.created_at
FROM price_history ph
JOIN commodities c ON ph.commodity_id = c.id
WHERE ph.price_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY ph.price_date DESC, c.name;
-- View: Unread notification counts
CREATE OR REPLACE VIEW v_unread_notifications_summary AS
SELECT 
    u.phone_number,
    u.district,
    COUNT(n.id) as unread_count
FROM users u
LEFT JOIN notifications n ON u.id = n.user_id AND n.is_read = FALSE
WHERE u.deleted_at IS NULL
GROUP BY u.id, u.phone_number, u.district
HAVING COUNT(n.id) > 0
ORDER BY unread_count DESC;
-- ============================================
-- SCHEDULED MAINTENANCE (Setup with pg_cron)
-- ============================================
-- Example pg_cron setup (requires pg_cron extension):
-- 
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- 
-- -- Run OTP cleanup daily at 2 AM
-- SELECT cron.schedule('cleanup-otps', '0 2 * * *', 'SELECT cleanup_expired_otps();');
-- 
-- -- Run notification archival weekly on Sunday at 3 AM
-- SELECT cron.schedule('archive-notifications', '0 3 * * 0', 'SELECT archive_old_notifications();');