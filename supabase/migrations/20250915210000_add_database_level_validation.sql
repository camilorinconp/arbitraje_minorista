-- supabase/migrations/20250915210000_add_database_level_validation.sql

-- =============================================================================
-- TÍTULO: Añadir Constraints de Validación a Nivel de Base de Datos (Capa 1)
-- Fecha: 15 Septiembre 2025
-- Propósito: Implementar la primera capa de la "Estrategia de Validación de 3
--            Capas" para garantizar la integridad de los datos en el nivel más
--            fundamental. Estos constraints previenen la inserción de datos
--            inválidos independientemente de la lógica de la aplicación.
-- Referencia Guía: Sección #28 (Three-Layer Validation Strategy)
-- =============================================================================

BEGIN;

-- 1. Tabla `productos`
-- Propósito: Asegurar que el precio de un producto sea siempre un valor positivo.
ALTER TABLE public.productos
ADD CONSTRAINT check_productos_precio_positivo CHECK (price > 0);

-- 2. Tabla `historial_precios`
-- Propósito: Asegurar que el precio registrado en el historial sea siempre positivo.
ALTER TABLE public.historial_precios
ADD CONSTRAINT check_historial_precio_positivo CHECK (precio > 0);

-- 3. Tabla `minoristas`
-- Propósito: Asegurar que el nombre del minorista no sea una cadena vacía.
ALTER TABLE public.minoristas
ADD CONSTRAINT check_minorista_nombre_no_vacio CHECK (nombre <> '');

COMMIT;
