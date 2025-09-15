-- supabase/migrations/20250915022854_add_scraper_selectors_to_minoristas.sql

-- Añadir columnas para los selectores CSS a la tabla de minoristas
ALTER TABLE public.minoristas
ADD COLUMN name_selector TEXT NULL,
ADD COLUMN price_selector TEXT NULL,
ADD COLUMN image_selector TEXT NULL;

-- Añadir comentarios para las nuevas columnas para claridad
COMMENT ON COLUMN public.minoristas.name_selector IS 'Selector CSS para extraer el nombre del producto.';
COMMENT ON COLUMN public.minoristas.price_selector IS 'Selector CSS para extraer el precio del producto.';
COMMENT ON COLUMN public.minoristas.image_selector IS 'Selector CSS para extraer la URL de la imagen del producto.';
