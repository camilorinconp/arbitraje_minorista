// frontend/src/hooks/useMinoristas.ts

import { useState, useEffect, useCallback } from 'react';
import {
  getMinoristas,
  createMinorista,
  Minorista,
} from '../api/gestionDatosApi';

export const useMinoristas = () => {
  const [minoristas, setMinoristas] = useState<Minorista[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const loadMinoristas = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getMinoristas();
      setMinoristas(data);
    } catch (error) {
      throw error; // Re-throw para que el componente maneje el error
    } finally {
      setIsLoading(false);
    }
  }, []);

  const addMinorista = useCallback(async (nombre: string, urlBase: string) => {
    setIsLoading(true);
    try {
      const nuevoMinorista = await createMinorista({
        nombre,
        url_base: urlBase,
      });
      setMinoristas((prev) => [...prev, nuevoMinorista]);
      return nuevoMinorista;
    } catch (error) {
      throw error; // Re-throw para que el componente maneje el error
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Cargar minoristas al montar el hook
  useEffect(() => {
    loadMinoristas().catch(console.error);
  }, [loadMinoristas]);

  return {
    minoristas,
    isLoading,
    loadMinoristas,
    addMinorista,
  };
};
