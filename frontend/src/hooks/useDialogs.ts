// frontend/src/hooks/useDialogs.ts

import { useState, useCallback } from 'react';

export const useDialogs = () => {
  const [openMinoristaDialog, setOpenMinoristaDialog] =
    useState<boolean>(false);
  const [openScraperDialog, setOpenScraperDialog] = useState<boolean>(false);

  const openMinoristaForm = useCallback(() => setOpenMinoristaDialog(true), []);
  const closeMinoristaForm = useCallback(
    () => setOpenMinoristaDialog(false),
    []
  );

  const openScraperForm = useCallback(() => setOpenScraperDialog(true), []);
  const closeScraperForm = useCallback(() => setOpenScraperDialog(false), []);

  return {
    openMinoristaDialog,
    openScraperDialog,
    openMinoristaForm,
    closeMinoristaForm,
    openScraperForm,
    closeScraperForm,
  };
};
