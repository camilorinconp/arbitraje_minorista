// frontend/src/hooks/useFormData.ts

import { useState, useCallback } from 'react';

export const useFormData = () => {
  // Estados para formulario de minorista
  const [nuevoMinoristaNombre, setNuevoMinoristaNombre] = useState<string>('');
  const [nuevoMinoristaUrl, setNuevoMinoristaUrl] = useState<string>('');

  // Estados para formulario de scraper
  const [urlProductoScrape, setUrlProductoScrape] = useState<string>('');
  const [minoristaSeleccionadoId, setMinoristaSeleccionadoId] = useState<
    number | ''
  >('');

  // Funciones para resetear formularios
  const resetMinoristaForm = useCallback(() => {
    setNuevoMinoristaNombre('');
    setNuevoMinoristaUrl('');
  }, []);

  const resetScraperForm = useCallback(() => {
    setUrlProductoScrape('');
    setMinoristaSeleccionadoId('');
  }, []);

  return {
    // Estados de minorista
    nuevoMinoristaNombre,
    setNuevoMinoristaNombre,
    nuevoMinoristaUrl,
    setNuevoMinoristaUrl,

    // Estados de scraper
    urlProductoScrape,
    setUrlProductoScrape,
    minoristaSeleccionadoId,
    setMinoristaSeleccionadoId,

    // Funciones de reset
    resetMinoristaForm,
    resetScraperForm,
  };
};
