// frontend/src/hooks/useScraper.ts

import { useState, useCallback } from 'react';
import { runScraper } from '../api/gestionDatosApi';

export const useScraper = () => {
  const [isScrapingLoading, setIsScrapingLoading] = useState<boolean>(false);

  const executeScraper = useCallback(
    async (productUrl: string, minoristaId: number) => {
      setIsScrapingLoading(true);
      try {
        const result = await runScraper(productUrl, minoristaId);
        return result;
      } catch (error) {
        throw error; // Re-throw para que el componente maneje el error
      } finally {
        setIsScrapingLoading(false);
      }
    },
    []
  );

  return {
    isScrapingLoading,
    executeScraper,
  };
};
