// frontend/src/components/ListaProductos.tsx

import React, { useEffect, useState } from 'react';
import { getProductos, getMinoristas, createMinorista, activarScraper, Producto, Minorista } from '../api/gestionDatosApi';
import { 
  Container, 
  Typography, 
  CircularProgress, 
  Alert, 
  List, 
  ListItem, 
  ListItemText, 
  ListItemAvatar, 
  Avatar, 
  Divider, 
  Box, 
  Button, 
  TextField, 
  Dialog, 
  DialogActions, 
  DialogContent, 
  DialogTitle, 
  Select, 
  MenuItem, 
  InputLabel, 
  FormControl
} from '@mui/material';

const ListaProductos: React.FC = () => {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [minoristas, setMinoristas] = useState<Minorista[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [openMinoristaDialog, setOpenMinoristaDialog] = useState<boolean>(false);
  const [nuevoMinoristaNombre, setNuevoMinoristaNombre] = useState<string>('');
  const [nuevoMinoristaUrl, setNuevoMinoristaUrl] = useState<string>('');
  const [openScraperDialog, setOpenScraperDialog] = useState<boolean>(false);
  const [urlProductoScrape, setUrlProductoScrape] = useState<string>('');
  const [minoristaSeleccionadoId, setMinoristaSeleccionadoId] = useState<number | ''>('');

  const cargarDatos = async () => {
    try {
      setLoading(true);
      const [productosData, minoristasData] = await Promise.all([
        getProductos(),
        getMinoristas()
      ]);
      setProductos(productosData);
      setMinoristas(minoristasData);
    } catch (err) {
      setError('Error al cargar los datos.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarDatos();
  }, []);

  const handleCrearMinorista = async () => {
    try {
      await createMinorista({ nombre: nuevoMinoristaNombre, url_base: nuevoMinoristaUrl });
      setOpenMinoristaDialog(false);
      setNuevoMinoristaNombre('');
      setNuevoMinoristaUrl('');
      cargarDatos(); // Recargar minoristas
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
      await activarScraper(urlProductoScrape, minoristaSeleccionadoId as number);
      setOpenScraperDialog(false);
      setUrlProductoScrape('');
      setMinoristaSeleccionadoId('');
      cargarDatos(); // Recargar productos
    } catch (err) {
      setError('Error al activar el scraper.');
      console.error(err);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Panel de Arbitraje Minorista
      </Typography>

      <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
        <Button variant="contained" onClick={() => setOpenMinoristaDialog(true)}>
          Añadir Minorista
        </Button>
        <Button variant="contained" onClick={() => setOpenScraperDialog(true)}>
          Activar Scraper
        </Button>
      </Box>

      <Typography variant="h5" component="h2" gutterBottom sx={{ mt: 4 }}>
        Productos Rastreados
      </Typography>
      {productos.length === 0 ? (
        <Alert severity="info">No hay productos rastreados aún. ¡Añade un minorista y usa el scraper!</Alert>
      ) : (
        <List>
          {productos.map((producto) => (
            <React.Fragment key={producto.id}>
              <ListItem alignItems="flex-start">
                <ListItemAvatar>
                  <Avatar alt={producto.nombre} src={producto.url_imagen || undefined} />
                </ListItemAvatar>
                <ListItemText
                  primary={
                    <Typography variant="h6">
                      <a href={producto.url_producto} target="_blank" rel="noopener noreferrer">
                        {producto.nombre}
                      </a>
                    </Typography>
                  }
                  secondary={
                    <Box>
                      <Typography component="span" variant="body2" color="text.primary">
                        Precio: ${producto.precio.toFixed(2)}
                      </Typography>
                      <br />
                      <Typography component="span" variant="body2" color="text.secondary">
                        Minorista: {producto.minorista?.nombre || 'Desconocido'}
                      </Typography>
                      <br />
                      <Typography component="span" variant="body2" color="text.secondary">
                        Último rastreo: {new Date(producto.ultima_fecha_rastreo).toLocaleString()}
                      </Typography>
                    </Box>
                  }
                />
              </ListItem>
              <Divider variant="inset" component="li" />
            </React.Fragment>
          ))}
        </List>
      )}

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
        <DialogTitle>Activar Scraper</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="dense">
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

export default ListaProductos;