import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
  IconButton,
  Alert,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { Minorista } from '../api/gestionDatosApi';

interface ListaMinoristasProps {
  minoristas: Minorista[];
  onEdit: (minorista: Minorista) => void;
  onDelete: (id: number) => void;
  isLoading?: boolean;
  isError?: boolean;
  error?: Error | null;
}

const ListaMinoristas: React.FC<ListaMinoristasProps> = ({
  minoristas,
  onEdit,
  onDelete,
  isLoading,
  isError,
  error,
}) => {
  if (isLoading) {
    return <Typography>Cargando minoristas...</Typography>;
  }

  if (isError) {
    return (
      <Alert severity="error">
        Error al cargar minoristas: {error?.message}
      </Alert>
    );
  }

  return (
    <TableContainer component={Paper}>
      <Typography variant="h6" sx={{ p: 2 }}>
        Minoristas Registrados
      </Typography>
      {minoristas.length === 0 ? (
        <Alert severity="info">No hay minoristas registrados aún.</Alert>
      ) : (
        <Table aria-label="tabla de minoristas">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Nombre</TableCell>
              <TableCell>URL Base</TableCell>
              <TableCell>Activo</TableCell>
              <TableCell>Selectores</TableCell>
              <TableCell>Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {minoristas.map((minorista) => (
              <TableRow key={minorista.id}>
                <TableCell>{minorista.id}</TableCell>
                <TableCell>{minorista.nombre}</TableCell>
                <TableCell>{minorista.url_base}</TableCell>
                <TableCell>{minorista.activo ? 'Sí' : 'No'}</TableCell>
                <TableCell>
                  <code>{minorista.name_selector || 'N/A'}</code>
                  <br />
                  <code>{minorista.price_selector || 'N/A'}</code>
                  <br />
                  <code>{minorista.image_selector || 'N/A'}</code>
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <IconButton
                      color="primary"
                      onClick={() => onEdit(minorista)}
                      size="small"
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      color="error"
                      onClick={() => onDelete(minorista.id)}
                      size="small"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </TableContainer>
  );
};

export default ListaMinoristas;
