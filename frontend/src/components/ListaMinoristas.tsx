import React, { useState, useEffect } from 'react';
import { getMinoristas, Minorista, runScraper } from '../api/gestionDatosApi';
import { 
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, 
  Paper, Typography, CircularProgress, Alert, Box, TextField, Button 
} from '@mui/material';

const ListaMinoristas: React.FC = () => {
  const [minoristas, setMinoristas] = useState<Minorista[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  // Estado para manejar los inputs de URL para cada minorista
  const [productUrls, setProductUrls] = useState<{ [key: number]: string }>({});

  const cargarMinoristas = async () => {
    try {
      setLoading(true);
      const data = await getMinoristas();
      setMinoristas(data);
    } catch (err) {
      setError('Error al cargar los minoristas. Por favor, intente de nuevo más tarde.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarMinoristas();
  }, []);

  const handleUrlChange = (minoristaId: number, url: string) => {
    setProductUrls(prev => ({ ...prev, [minoristaId]: url }));
  };

  const handleScrape = async (minoristaId: number) => {
    const productUrl = productUrls[minoristaId];
    if (!productUrl) {
      alert('Por favor, ingrese una URL de producto.');
      return;
    }

    try {
      const resultado = await runScraper(productUrl, minoristaId);
      alert(`Scraping exitoso para: ${resultado.nombre} - Precio: ${resultado.precio}`);
      // Opcional: Limpiar el input después de un scrapeo exitoso
      setProductUrls(prev => ({ ...prev, [minoristaId]: '' }));
      // Aquí se podría llamar a una función para recargar la lista de productos
    } catch (err) {
      alert('Error durante el scraping. Revise la consola para más detalles.');
      console.error(err);
    }
  };

  if (loading) {
    return <CircularProgress />;
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  return (
    <TableContainer component={Paper}>
      <Typography variant="h6" sx={{ p: 2 }}>
        Minoristas Registrados
      </Typography>
      <Table aria-label="tabla de minoristas">
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Nombre</TableCell>
            <TableCell>Selectores</TableCell>
            <TableCell sx={{ width: '40%' }}>Acciones de Scraping</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {minoristas.map((minorista) => (
            <TableRow key={minorista.id}>
              <TableCell>{minorista.id}</TableCell>
              <TableCell>{minorista.nombre}</TableCell>
              <TableCell>
                <code>{minorista.name_selector || 'N/A'}</code><br/>
                <code>{minorista.price_selector || 'N/A'}</code>
              </TableCell>
              <TableCell>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TextField
                    label="URL del Producto"
                    variant="outlined"
                    size="small"
                    fullWidth
                    value={productUrls[minorista.id] || ''}
                    onChange={(e) => handleUrlChange(minorista.id, e.target.value)}
                  />
                  <Button 
                    variant="contained" 
                    onClick={() => handleScrape(minorista.id)}
                    disabled={!productUrls[minorista.id]}
                  >
                    Scrapear
                  </Button>
                </Box>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default ListaMinoristas;