// frontend/src/hooks/useErrorHandling.ts

import { useState, useCallback } from 'react';

interface ErrorData {
  response?: {
    data?: {
      detail?: any;
    };
  };
  message?: string;
}

export const useErrorHandling = () => {
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleError = useCallback(
    (error: ErrorData, defaultMessage: string) => {
      console.error(error);
      let errorMessage = defaultMessage;

      if (error?.response?.data?.detail) {
        // Error del backend con detalle específico
        if (Array.isArray(error.response.data.detail)) {
          // Errores de validación de Pydantic
          errorMessage = error.response.data.detail
            .map((err: any) => `${err.field}: ${err.message}`)
            .join(', ');
        } else {
          errorMessage = error.response.data.detail;
        }
      } else if (error?.message) {
        errorMessage = error.message;
      }

      setError(errorMessage);
      // Auto-clear error after 8 seconds
      setTimeout(() => setError(null), 8000);
    },
    []
  );

  const showSuccess = useCallback((message: string) => {
    setSuccessMessage(message);
    // Auto-clear success message after 5 seconds
    setTimeout(() => setSuccessMessage(null), 5000);
  }, []);

  const clearError = useCallback(() => setError(null), []);
  const clearSuccess = useCallback(() => setSuccessMessage(null), []);

  return {
    error,
    successMessage,
    handleError,
    showSuccess,
    clearError,
    clearSuccess,
  };
};
