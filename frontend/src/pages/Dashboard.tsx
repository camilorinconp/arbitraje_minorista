// frontend/src/pages/Dashboard.tsx

import React from 'react';
import {
  Box,
  Container,
  Typography,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Snackbar,
} from '@mui/material';
import ListaProductos from '../components/ListaProductos';
import {
  useErrorHandling,
  useMinoristas,
  useScraper,
  useDialogs,
  useFormData,
} from '../hooks';

const Dashboard: React.FC = () => {
  // Custom hooks para separar la lógica
  const {
    error,
    successMessage,
    handleError,
    showSuccess,
    clearError,
    clearSuccess,
  } = useErrorHandling();
  const {
    minoristas,
    isLoading: minoristaLoading,
    addMinorista,
  } = useMinoristas();
  const { isScrapingLoading, executeScraper } = useScraper();
  const {
    openMinoristaDialog,
    openScraperDialog,
    openMinoristaForm,
    closeMinoristaForm,
    openScraperForm,
    closeScraperForm,
  } = useDialogs();
  const {
    nuevoMinoristaNombre,
    setNuevoMinoristaNombre,
    nuevoMinoristaUrl,
    setNuevoMinoristaUrl,
    urlProductoScrape,
    setUrlProductoScrape,
    minoristaSeleccionadoId,
    setMinoristaSeleccionadoId,
    resetMinoristaForm,
    resetScraperForm,
  } = useFormData();

  // Determinar si hay alguna operación cargando
  const isLoading = minoristaLoading || isScrapingLoading;

  // Manejadores de eventos
  const handleOpenScraperDialog = async () => {
    try {
      openScraperForm();
    } catch (err) {
      handleError(err, 'Error al abrir el diálogo del scraper.');
    }
  };

  const handleCrearMinorista = async () => {
    if (!nuevoMinoristaNombre.trim()) {
      handleError(
        { message: 'El nombre del minorista es requerido.' },
        'Validation error'
      );
      return;
    }
    if (!nuevoMinoristaUrl.trim()) {
      handleError(
        { message: 'La URL base del minorista es requerida.' },
        'Validation error'
      );
      return;
    }

    try {
      await addMinorista(nuevoMinoristaNombre, nuevoMinoristaUrl);
      closeMinoristaForm();
      resetMinoristaForm();
      showSuccess('Minorista creado exitosamente.');
    } catch (err) {
      handleError(err, 'Error al crear minorista.');
    }
  };

  const handleActivarScraper = async () => {
    if (minoristaSeleccionadoId === '' || !urlProductoScrape) {
      handleError(
        {
          message:
            'Por favor, selecciona un minorista y proporciona una URL de producto.',
        },
        'Validation error'
      );
      return;
    }

    try {
      const producto = await executeScraper(
        urlProductoScrape,
        minoristaSeleccionadoId as number
      );
      closeScraperForm();
      resetScraperForm();
      showSuccess(
        `Producto scrapeado exitosamente: ${producto.name} - $${producto.price}`
      );
    } catch (err) {
      handleError(err, 'Error al ejecutar scraper.');
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4, mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Dashboard de Arbitraje de Precios
        </Typography>
        <Typography variant="h6" color="text.secondary" paragraph>
          Gestiona minoristas y ejecuta scraping de productos para encontrar las
          mejores oportunidades de arbitraje.
        </Typography>

        <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            color="primary"
            onClick={openMinoristaForm}
            disabled={isLoading}
          >
            Crear Minorista
          </Button>
          <Button
            variant="outlined"
            color="secondary"
            onClick={handleOpenScraperDialog}
            disabled={isLoading}
          >
            Ejecutar Scraper
          </Button>
        </Box>

        <ListaProductos />

        {/* Dialog para crear minorista */}
        <Dialog
          open={openMinoristaDialog}
          onClose={closeMinoristaForm}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>Crear Nuevo Minorista</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              margin="dense"
              label="Nombre del Minorista"
              fullWidth
              variant="outlined"
              value={nuevoMinoristaNombre}
              onChange={(e) => setNuevoMinoristaNombre(e.target.value)}
              sx={{ mb: 2 }}
            />
            <TextField
              margin="dense"
              label="URL Base"
              fullWidth
              variant="outlined"
              value={nuevoMinoristaUrl}
              onChange={(e) => setNuevoMinoristaUrl(e.target.value)}
              placeholder="https://ejemplo.com"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={closeMinoristaForm} disabled={isLoading}>
              Cancelar
            </Button>
            <Button
              onClick={handleCrearMinorista}
              disabled={isLoading}
              variant="contained"
            >
              Crear
            </Button>
          </DialogActions>
        </Dialog>

        {/* Dialog para scraper */}
        <Dialog
          open={openScraperDialog}
          onClose={closeScraperForm}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>Ejecutar Scraper</DialogTitle>
          <DialogContent>
            <FormControl fullWidth sx={{ mb: 2, mt: 1 }}>
              <InputLabel>Minorista</InputLabel>
              <Select
                value={minoristaSeleccionadoId}
                label="Minorista"
                onChange={(e) =>
                  setMinoristaSeleccionadoId(e.target.value as number)
                }
              >
                {minoristas.map((minorista) => (
                  <MenuItem key={minorista.id} value={minorista.id}>
                    {minorista.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              margin="dense"
              label="URL del Producto"
              fullWidth
              variant="outlined"
              value={urlProductoScrape}
              onChange={(e) => setUrlProductoScrape(e.target.value)}
              placeholder="https://ejemplo.com/producto"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={closeScraperForm} disabled={isLoading}>
              Cancelar
            </Button>
            <Button
              onClick={handleActivarScraper}
              disabled={isLoading}
              variant="contained"
            >
              Ejecutar
            </Button>
          </DialogActions>
        </Dialog>

        {/* Mensajes de error */}
        <Snackbar
          open={!!error}
          autoHideDuration={8000}
          onClose={clearError}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        >
          <Alert onClose={clearError} severity="error" sx={{ width: '100%' }}>
            {error}
          </Alert>
        </Snackbar>

        {/* Mensajes de éxito */}
        <Snackbar
          open={!!successMessage}
          autoHideDuration={5000}
          onClose={clearSuccess}
          anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        >
          <Alert
            onClose={clearSuccess}
            severity="success"
            sx={{ width: '100%' }}
          >
            {successMessage}
          </Alert>
        </Snackbar>
      </Box>
    </Container>
  );
};

export default Dashboard;
