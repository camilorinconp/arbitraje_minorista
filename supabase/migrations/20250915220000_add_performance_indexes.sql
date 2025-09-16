-- Migration: Add performance indexes for frequent queries
-- Created: 2024-12-16

-- Index for product lookups by retailer (used in scheduler)
CREATE INDEX IF NOT EXISTS idx_productos_minorista_activo
ON productos(id_minorista);

-- Composite index for product lookups by URL and retailer
CREATE INDEX IF NOT EXISTS idx_productos_url_minorista
ON productos(product_url, id_minorista);

-- Index for recent scraping queries
CREATE INDEX IF NOT EXISTS idx_productos_last_scraped
ON productos(last_scraped_at DESC);

-- Index for price history queries by product
CREATE INDEX IF NOT EXISTS idx_historial_producto_fecha
ON historial_precios(id_producto, fecha_registro DESC);

-- Index for price history queries by retailer
CREATE INDEX IF NOT EXISTS idx_historial_minorista_fecha
ON historial_precios(id_minorista, fecha_registro DESC);

-- Composite index for latest price queries
CREATE INDEX IF NOT EXISTS idx_historial_producto_minorista_fecha
ON historial_precios(id_producto, id_minorista, fecha_registro DESC);

-- Index for active retailers queries
CREATE INDEX IF NOT EXISTS idx_minoristas_activo
ON minoristas(activo)
WHERE activo = true;

-- Index for retailers with discovery configuration
CREATE INDEX IF NOT EXISTS idx_minoristas_discovery
ON minoristas(activo, discovery_url, product_link_selector)
WHERE activo = true AND discovery_url IS NOT NULL AND product_link_selector IS NOT NULL;

-- Index for product identification
CREATE INDEX IF NOT EXISTS idx_productos_identificador
ON productos(identificador_producto)
WHERE identificador_producto IS NOT NULL;

-- Update table statistics
ANALYZE productos;
ANALYZE minoristas;
ANALYZE historial_precios;