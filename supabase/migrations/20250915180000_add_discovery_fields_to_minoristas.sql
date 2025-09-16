-- supabase/migrations/20250915180000_add_discovery_fields_to_minoristas.sql

-- Añadir columnas para el descubrimiento de productos
ALTER TABLE public.minoristas
ADD COLUMN discovery_url TEXT NULL,
ADD COLUMN product_link_selector TEXT NULL;

-- Añadir comentarios para las nuevas columnas para claridad
COMMENT ON COLUMN public.minoristas.discovery_url IS 'URL de la página de categoría o de ofertas para descubrir nuevos productos.';
COMMENT ON COLUMN public.minoristas.product_link_selector IS 'Selector CSS para extraer los enlaces a las páginas de productos individuales desde la discovery_url.';
