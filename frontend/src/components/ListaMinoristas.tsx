import React, { useState, useEffect } from 'react';
import { getMinoristas, Minorista } from '../api/gestionDatosApi';
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Typography, CircularProgress, Alert } from '@mui/material';

const ListaMinoristas: React.FC = () => {
  const [minoristas, setMinoristas] = useState<Minorista[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
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

    cargarMinoristas();
  }, []);

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
            <TableCell>URL Base</TableCell>
            <TableCell>Activo</TableCell>
            <TableCell>Selector de Nombre</TableCell>
            <TableCell>Selector de Precio</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {minoristas.map((minorista) => (
            <TableRow key={minorista.id}>
              <TableCell>{minorista.id}</TableCell>
              <TableCell>{minorista.nombre}</TableCell>
              <TableCell>{minorista.url_base}</TableCell>
              <TableCell>{minorista.activo ? 'Sí' : 'No'}</TableCell>
              <TableCell><code>{minorista.name_selector || 'No definido'}</code></TableCell>
              <TableCell><code>{minorista.price_selector || 'No definido'}</code></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default ListaMinoristas;
