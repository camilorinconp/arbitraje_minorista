-- supabase/migrations/20250914210500_refactor_productos_table.sql

-- Renombrar la tabla 'products' a 'productos'
ALTER TABLE public.products RENAME TO productos;

-- Añadir columna 'id_minorista' (FK a la futura tabla 'minoristas')
ALTER TABLE public.productos
ADD COLUMN id_minorista BIGINT NULL;

-- Añadir columna 'identificador_producto' para rastrear el mismo producto en diferentes minoristas
ALTER TABLE public.productos
ADD COLUMN identificador_producto TEXT NULL;

-- Crear un índice para 'identificador_producto' para búsquedas eficientes
CREATE INDEX idx_productos_identificador_producto ON public.productos (identificador_producto);

-- Actualizar comentarios de la tabla y columnas
COMMENT ON TABLE public.productos IS 'Tabla para almacenar información de productos rastreados.';
COMMENT ON COLUMN public.productos.id IS 'Identificador único del producto.';
COMMENT ON COLUMN public.productos.name IS 'Nombre del producto.';
COMMENT ON COLUMN public.productos.price IS 'Precio actual del producto.';
COMMENT ON COLUMN public.productos.product_url IS 'URL del producto en el minorista.';
COMMENT ON COLUMN public.productos.image_url IS 'URL de la imagen del producto.';
COMMENT ON COLUMN public.productos.last_scraped_at IS 'Fecha y hora del último rastreo del producto.';
COMMENT ON COLUMN public.productos.created_at IS 'Fecha y hora de creación del registro del producto.';
COMMENT ON COLUMN public.productos.id_minorista IS 'Clave foránea al minorista asociado (futura).';
COMMENT ON COLUMN public.productos.identificador_producto IS 'Identificador único del producto (ej. UPC, ASIN) para correlacionar entre minoristas.';

-- Actualizar la política RLS para la tabla renombrada
ALTER TABLE public.productos ENABLE ROW LEVEL SECURITY;

-- Eliminar la política antigua si existiera (para evitar conflictos)
DROP POLICY IF EXISTS "Service Role Full Access" ON public.productos;

-- Crear política de acceso total para el rol de servicio en la tabla renombrada
CREATE POLICY "Acceso Total Rol Servicio Productos"
ON public.productos
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
