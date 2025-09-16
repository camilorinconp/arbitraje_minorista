// frontend/src/pages/Dashboard.tsx

import React, { useState } from 'react';
import { Box, Container, Typography, Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField, FormControl, InputLabel, Select, MenuItem, Alert } from '@mui/material';
import ListaProductos from '../components/ListaProductos';
import { createMinorista, runScraper, getMinoristas, Minorista } from '../api/gestionDatosApi';

const Dashboard: React.FC = () => {
  const [minoristas, setMinoristas] = useState<Minorista[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [openMinoristaDialog, setOpenMinoristaDialog] = useState<boolean>(false);
  const [nuevoMinoristaNombre, setNuevoMinoristaNombre] = useState<string>('');
  const [nuevoMinoristaUrl, setNuevoMinoristaUrl] = useState<string>('');
  const [openScraperDialog, setOpenScraperDialog] = useState<boolean>(false);
  const [urlProductoScrape, setUrlProductoScrape] = useState<string>('');
  const [minoristaSeleccionadoId, setMinoristaSeleccionadoId] = useState<number | ''>('');

  const handleOpenScraperDialog = async () => {
    try {
      const minoristasData = await getMinoristas();
      setMinoristas(minoristasData);
      setOpenScraperDialog(true);
    } catch (err) {
      setError('Error al cargar la lista de minoristas para el scraper.');
    }
  };

  const handleCrearMinorista = async () => {
    try {
      await createMinorista({ nombre: nuevoMinoristaNombre, url_base: nuevoMinoristaUrl });
      setOpenMinoristaDialog(false);
      setNuevoMinoristaNombre('');
      setNuevoMinoristaUrl('');
      // Aquí podríamos usar react-query para invalidar y recargar datos automáticamente
    } catch (err) {
      setError('Error al crear minorista.');
      console.error(err);
    }
  };

  const handleActivarScraper = async () => {
    if (minoristaSeleccionadoId === '' || !urlProductoScrape) {
      alert('Por favor, selecciona un minorista y proporciona una URL de producto.');
      return;
    }
    try {
      await runScraper(urlProductoScrape, minoristaSeleccionadoId as number);
      setOpenScraperDialog(false);
      setUrlProductoScrape('');
      setMinoristaSeleccionadoId('');
      // Aquí podríamos usar react-query para invalidar y recargar datos automáticamente
    } catch (err) {
      setError('Error al activar el scraper.');
      console.error(err);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Dashboard de Productos
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Aquí se muestran los productos rastreados y sus precios actuales.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button variant="outlined" onClick={() => setOpenMinoristaDialog(true)}>
            Añadir Minorista
          </Button>
          <Button variant="contained" onClick={handleOpenScraperDialog}>
            Scrapear Producto
          </Button>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

      <Box sx={{ mt: 4 }}>
        <ListaProductos />
      </Box>

      {/* Diálogo para Añadir Minorista */}
      <Dialog open={openMinoristaDialog} onClose={() => setOpenMinoristaDialog(false)}>
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
          <Button onClick={() => setOpenMinoristaDialog(false)}>Cancelar</Button>
          <Button onClick={handleCrearMinorista}>Crear</Button>
        </DialogActions>
      </Dialog>

      {/* Diálogo para Activar Scraper */}
      <Dialog open={openScraperDialog} onClose={() => setOpenScraperDialog(false)}>
        <DialogTitle>Activar Scraper Manual</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="dense" sx={{ mt: 2 }}>
            <InputLabel id="minorista-select-label">Minorista</InputLabel>
            <Select
              labelId="minorista-select-label"
              value={minoristaSeleccionadoId}
              label="Minorista"
              onChange={(e) => setMinoristaSeleccionadoId(e.target.value as number)}
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
          <Button onClick={() => setOpenScraperDialog(false)}>Cancelar</Button>
          <Button onClick={handleActivarScraper}>Scrapear</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Dashboard;
