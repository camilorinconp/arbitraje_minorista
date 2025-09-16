-- supabase/migrations/20250915200000_add_strategic_indexes.sql

-- =============================================================================
-- TÍTULO: Añadir Índices Estratégicos para Performance de Consultas
-- Fecha: 15 Septiembre 2025
-- Propósito: Mejorar el rendimiento de las consultas más frecuentes en las
--            tablas productos y, especialmente, historial_precios, que se
--            espera que crezca rápidamente.
-- Referencia Guía: Sección #20 (Índices Estratégicos & Query Optimization)
-- =============================================================================

BEGIN;

-- 1. Índice en la tabla `productos`
-- Propósito: Acelerar la búsqueda de todos los productos pertenecientes a un minorista específico.
-- Tipo de consulta: SELECT * FROM productos WHERE id_minorista = [valor];
CREATE INDEX IF NOT EXISTS idx_productos_id_minorista ON public.productos (id_minorista);

-- 2. Índice compuesto en la tabla `historial_precios`
-- Propósito: Optimización crítica para la consulta más común: obtener el historial de precios de un producto, ordenado del más reciente al más antiguo.
-- Tipo de consulta: SELECT * FROM historial_precios WHERE id_producto = [valor] ORDER BY fecha_registro DESC;
CREATE INDEX IF NOT EXISTS idx_historial_precios_id_producto_fecha ON public.historial_precios (id_producto, fecha_registro DESC);

-- 3. Índice simple en la tabla `historial_precios`
-- Propósito: Facilitar consultas de análisis que agrupen o filtren por minorista.
-- Tipo de consulta: SELECT AVG(precio) FROM historial_precios WHERE id_minorista = [valor];
CREATE INDEX IF NOT EXISTS idx_historial_precios_id_minorista ON public.historial_precios (id_minorista);

COMMIT;
