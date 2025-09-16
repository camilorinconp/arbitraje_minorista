// frontend/src/pages/Dashboard.tsx

import React, { useState } from 'react';
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
  createMinorista,
  runScraper,
  getMinoristas,
  Minorista,
} from '../api/gestionDatosApi';

const Dashboard: React.FC = () => {
  const [minoristas, setMinoristas] = useState<Minorista[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [openMinoristaDialog, setOpenMinoristaDialog] =
    useState<boolean>(false);
  const [nuevoMinoristaNombre, setNuevoMinoristaNombre] = useState<string>('');
  const [nuevoMinoristaUrl, setNuevoMinoristaUrl] = useState<string>('');
  const [openScraperDialog, setOpenScraperDialog] = useState<boolean>(false);
  const [urlProductoScrape, setUrlProductoScrape] = useState<string>('');
  const [minoristaSeleccionadoId, setMinoristaSeleccionadoId] = useState<
    number | ''
  >('');

  // Helper function para manejo de errores
  const handleError = (error: any, defaultMessage: string) => {
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
  };

  const showSuccess = (message: string) => {
    setSuccessMessage(message);
    // Auto-clear success message after 5 seconds
    setTimeout(() => setSuccessMessage(null), 5000);
  };

  const handleOpenScraperDialog = async () => {
    setIsLoading(true);
    try {
      const minoristasData = await getMinoristas();
      setMinoristas(minoristasData);
      setOpenScraperDialog(true);
    } catch (err) {
      handleError(
        err,
        'Error al cargar la lista de minoristas para el scraper.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleCrearMinorista = async () => {
    if (!nuevoMinoristaNombre.trim()) {
      setError('El nombre del minorista es requerido.');
      return;
    }
    if (!nuevoMinoristaUrl.trim()) {
      setError('La URL base del minorista es requerida.');
      return;
    }

    setIsLoading(true);
    try {
      await createMinorista({
        nombre: nuevoMinoristaNombre,
        url_base: nuevoMinoristaUrl,
      });
      setOpenMinoristaDialog(false);
      setNuevoMinoristaNombre('');
      setNuevoMinoristaUrl('');
      showSuccess('Minorista creado exitosamente.');
      // Aquí podríamos usar react-query para invalidar y recargar datos automáticamente
    } catch (err) {
      handleError(err, 'Error al crear minorista.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleActivarScraper = async () => {
    if (minoristaSeleccionadoId === '' || !urlProductoScrape) {
      setError(
        'Por favor, selecciona un minorista y proporciona una URL de producto.'
      );
      return;
    }

    setIsLoading(true);
    try {
      const producto = await runScraper(
        urlProductoScrape,
        minoristaSeleccionadoId as number
      );
      setOpenScraperDialog(false);
      setUrlProductoScrape('');
      setMinoristaSeleccionadoId('');
      showSuccess(
        `Producto "${producto.name}" scrapeado exitosamente por $${producto.price}`
      );
      // Aquí podríamos usar react-query para invalidar y recargar datos automáticamente
    } catch (err) {
      handleError(err, 'Error al activar el scraper.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Dashboard de Productos
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Aquí se muestran los productos rastreados y sus precios actuales.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            onClick={() => setOpenMinoristaDialog(true)}
            disabled={isLoading}
          >
            Añadir Minorista
          </Button>
          <Button
            variant="contained"
            onClick={handleOpenScraperDialog}
            disabled={isLoading}
          >
            {isLoading ? 'Cargando...' : 'Scrapear Producto'}
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ mt: 4 }}>
        <ListaProductos />
      </Box>

      {/* Diálogo para Añadir Minorista */}
      <Dialog
        open={openMinoristaDialog}
        onClose={() => setOpenMinoristaDialog(false)}
      >
        <DialogTitle>Añadir Nuevo Minorista</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Nombre del Minorista"
            type="text"
            fullWidth
            variant="standard"
            value={nuevoMinoristaNombre}
            onChange={(e) => setNuevoMinoristaNombre(e.target.value)}
          />
          <TextField
            margin="dense"
            label="URL Base del Minorista"
            type="url"
            fullWidth
            variant="standard"
            value={nuevoMinoristaUrl}
            onChange={(e) => setNuevoMinoristaUrl(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setOpenMinoristaDialog(false)}
            disabled={isLoading}
          >
            Cancelar
          </Button>
          <Button onClick={handleCrearMinorista} disabled={isLoading}>
            {isLoading ? 'Creando...' : 'Crear'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Diálogo para Activar Scraper */}
      <Dialog
        open={openScraperDialog}
        onClose={() => setOpenScraperDialog(false)}
      >
        <DialogTitle>Activar Scraper Manual</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="dense" sx={{ mt: 2 }}>
            <InputLabel id="minorista-select-label">Minorista</InputLabel>
            <Select
              labelId="minorista-select-label"
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
            label="URL del Producto a Scrapear"
            type="url"
            fullWidth
            variant="standard"
            value={urlProductoScrape}
            onChange={(e) => setUrlProductoScrape(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setOpenScraperDialog(false)}
            disabled={isLoading}
          >
            Cancelar
          </Button>
          <Button onClick={handleActivarScraper} disabled={isLoading}>
            {isLoading ? 'Scrapeando...' : 'Scrapear'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar para mensajes de éxito */}
      <Snackbar
        open={!!successMessage}
        autoHideDuration={5000}
        onClose={() => setSuccessMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSuccessMessage(null)}
          severity="success"
          sx={{ width: '100%' }}
        >
          {successMessage}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default Dashboard;
