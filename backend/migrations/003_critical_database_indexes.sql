-- Migration 003: Critical database indexes for performance optimization
-- Created: 2024-09-16
-- Description: Add critical indexes for core tables to improve query performance

-- Performance indexes for producto table
CREATE INDEX IF NOT EXISTS idx_producto_plataforma_activo
ON producto(plataforma, activo)
WHERE activo = true;

CREATE INDEX IF NOT EXISTS idx_producto_precio_descuento
ON producto(precio_actual, porcentaje_descuento);

CREATE INDEX IF NOT EXISTS idx_producto_fecha_actualizacion
ON producto(fecha_actualizacion DESC);

CREATE INDEX IF NOT EXISTS idx_producto_categoria_precio
ON producto(categoria, precio_actual);

-- Performance indexes for oportunidad_arbitraje table
CREATE INDEX IF NOT EXISTS idx_oportunidad_diferencia_porcentaje
ON oportunidad_arbitraje(diferencia_porcentaje DESC);

CREATE INDEX IF NOT EXISTS idx_oportunidad_fecha_deteccion
ON oportunidad_arbitraje(fecha_deteccion DESC);

CREATE INDEX IF NOT EXISTS idx_oportunidad_activa
ON oportunidad_arbitraje(activa)
WHERE activa = true;

-- Composite index for filtering active opportunities by profit margin
CREATE INDEX IF NOT EXISTS idx_oportunidad_activa_diferencia
ON oportunidad_arbitraje(activa, diferencia_porcentaje DESC)
WHERE activa = true AND diferencia_porcentaje > 5.0;

-- Performance indexes for seguimiento_precio table
CREATE INDEX IF NOT EXISTS idx_seguimiento_producto_fecha
ON seguimiento_precio(producto_id, fecha_seguimiento DESC);

CREATE INDEX IF NOT EXISTS idx_seguimiento_fecha_precio
ON seguimiento_precio(fecha_seguimiento DESC, precio);

-- Partial index for recent price tracking
CREATE INDEX IF NOT EXISTS idx_seguimiento_reciente
ON seguimiento_precio(producto_id, precio, fecha_seguimiento)
WHERE fecha_seguimiento > NOW() - INTERVAL '30 days';

-- Index for price change analysis
CREATE INDEX IF NOT EXISTS idx_seguimiento_cambio_precio
ON seguimiento_precio(producto_id, cambio_precio)
WHERE cambio_precio IS NOT NULL AND cambio_precio != 0;

-- Performance indexes for scraping_session table (if exists)
CREATE INDEX IF NOT EXISTS idx_scraping_session_fecha_estado
ON scraping_session(fecha_inicio DESC, estado);

CREATE INDEX IF NOT EXISTS idx_scraping_session_plataforma
ON scraping_session(plataforma, fecha_inicio DESC);

-- Indexes for authentication tables (from migration 001)
-- These enhance the existing auth indexes for better performance

-- Enhanced user queries
CREATE INDEX IF NOT EXISTS idx_users_last_login_role
ON users(last_login DESC, role)
WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_users_verification_status
ON users(is_verified, is_active, created_at);

-- Enhanced refresh token queries
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_cleanup
ON refresh_tokens(expires_at, revoked)
WHERE expires_at < NOW() OR revoked = true;

-- Composite index for active user sessions
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_active_sessions
ON refresh_tokens(user_id, created_at DESC)
WHERE revoked = false AND expires_at > NOW();

-- Performance indexes for metrics and monitoring
CREATE INDEX IF NOT EXISTS idx_producto_monitoring
ON producto(plataforma, fecha_actualizacion, activo)
WHERE activo = true AND fecha_actualizacion > NOW() - INTERVAL '24 hours';

-- Index for detecting stale products
CREATE INDEX IF NOT EXISTS idx_producto_stale
ON producto(fecha_actualizacion ASC, plataforma)
WHERE activo = true AND fecha_actualizacion < NOW() - INTERVAL '6 hours';

-- Add constraints for data integrity
ALTER TABLE producto
ADD CONSTRAINT IF NOT EXISTS chk_precio_positivo
CHECK (precio_actual > 0);

ALTER TABLE oportunidad_arbitraje
ADD CONSTRAINT IF NOT EXISTS chk_diferencia_valida
CHECK (diferencia_porcentaje >= -100 AND diferencia_porcentaje <= 1000);

ALTER TABLE seguimiento_precio
ADD CONSTRAINT IF NOT EXISTS chk_precio_seguimiento_positivo
CHECK (precio > 0);

-- Create function to analyze index usage
CREATE OR REPLACE FUNCTION get_index_usage_stats()
RETURNS TABLE(
    schemaname TEXT,
    tablename TEXT,
    indexname TEXT,
    num_scans BIGINT,
    num_tup_read BIGINT,
    num_tup_fetch BIGINT,
    usage_ratio NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        schemaname::TEXT,
        tablename::TEXT,
        indexname::TEXT,
        idx_scan as num_scans,
        idx_tup_read as num_tup_read,
        idx_tup_fetch as num_tup_fetch,
        CASE
            WHEN idx_scan = 0 THEN 0::NUMERIC
            ELSE ROUND((idx_tup_read::NUMERIC / idx_scan), 2)
        END as usage_ratio
    FROM pg_stat_user_indexes
    WHERE schemaname = 'public'
    ORDER BY idx_scan DESC;
END;
$$ LANGUAGE plpgsql;

-- Create function to identify slow queries
CREATE OR REPLACE FUNCTION get_slow_queries()
RETURNS TABLE(
    query TEXT,
    calls BIGINT,
    total_time DOUBLE PRECISION,
    mean_time DOUBLE PRECISION,
    rows BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        query::TEXT,
        calls,
        total_exec_time as total_time,
        mean_exec_time as mean_time,
        rows
    FROM pg_stat_statements
    WHERE mean_exec_time > 100  -- queries taking more than 100ms
    ORDER BY mean_exec_time DESC
    LIMIT 20;
EXCEPTION WHEN OTHERS THEN
    -- pg_stat_statements might not be enabled
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON INDEX idx_producto_plataforma_activo IS 'Optimizes queries filtering active products by platform';
COMMENT ON INDEX idx_oportunidad_diferencia_porcentaje IS 'Optimizes sorting arbitrage opportunities by profit margin';
COMMENT ON INDEX idx_seguimiento_producto_fecha IS 'Optimizes price history queries for specific products';
COMMENT ON INDEX idx_users_last_login_role IS 'Optimizes user activity queries by role';

-- Create maintenance function for index statistics
CREATE OR REPLACE FUNCTION update_table_statistics()
RETURNS TEXT AS $$
DECLARE
    table_record RECORD;
    result_text TEXT := '';
BEGIN
    -- Update statistics for all tables
    FOR table_record IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
    LOOP
        EXECUTE 'ANALYZE ' || table_record.tablename;
        result_text := result_text || table_record.tablename || ' ';
    END LOOP;

    RETURN 'Statistics updated for tables: ' || result_text;
END;
$$ LANGUAGE plpgsql;