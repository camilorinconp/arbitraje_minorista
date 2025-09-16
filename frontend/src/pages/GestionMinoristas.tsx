import React, { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  Alert,
} from '@mui/material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ListaMinoristas from '../components/ListaMinoristas';
import FormularioMinorista from '../components/FormularioMinorista';
import {
  getMinoristas,
  createMinorista,
  updateMinorista,
  deleteMinorista,
  MinoristaBase,
  Minorista,
} from '../api/gestionDatosApi';

const GestionMinoristas: React.FC = () => {
  const queryClient = useQueryClient();
  const [openFormDialog, setOpenFormDialog] = useState(false);
  const [minoristaAEditar, setMinoristaAEditar] = useState<
    Minorista | undefined
  >(undefined);

  const {
    data: minoristas,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['minoristas'],
    queryFn: getMinoristas,
  });

  const createMinoristaMutation = useMutation({
    mutationFn: createMinorista,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['minoristas'] });
      setOpenFormDialog(false);
      setMinoristaAEditar(undefined);
    },
    onError: (err) => {
      console.error('Error al crear minorista:', err);
      // Aquí podrías manejar el error de forma más amigable para el usuario
    },
  });

  const updateMinoristaMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: MinoristaBase }) =>
      updateMinorista(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['minoristas'] });
      setOpenFormDialog(false);
      setMinoristaAEditar(undefined);
    },
    onError: (err) => {
      console.error('Error al actualizar minorista:', err);
    },
  });

  const deleteMinoristaMutation = useMutation({
    mutationFn: deleteMinorista,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['minoristas'] });
    },
    onError: (err) => {
      console.error('Error al eliminar minorista:', err);
    },
  });

  const handleSaveMinorista = async (minoristaData: MinoristaBase) => {
    if (minoristaAEditar) {
      await updateMinoristaMutation.mutateAsync({
        id: minoristaAEditar.id,
        data: minoristaData,
      });
    } else {
      await createMinoristaMutation.mutateAsync(minoristaData);
    }
  };

  const handleEdit = (minorista: Minorista) => {
    setMinoristaAEditar(minorista);
    setOpenFormDialog(true);
  };

  const handleDelete = (id: number) => {
    if (
      window.confirm('¿Estás seguro de que quieres eliminar este minorista?')
    ) {
      deleteMinoristaMutation.mutate(id);
    }
  };

  const handleOpenCreateDialog = () => {
    setMinoristaAEditar(undefined);
    setOpenFormDialog(true);
  };

  const handleCloseFormDialog = () => {
    setOpenFormDialog(false);
    setMinoristaAEditar(undefined);
  };

  return (
    <Container>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 4,
        }}
      >
        <Typography variant="h4" gutterBottom>
          Gestión de Minoristas
        </Typography>
        <Button variant="contained" onClick={handleOpenCreateDialog}>
          Añadir Nuevo Minorista
        </Button>
      </Box>

      {isError && (
        <Alert severity="error">
          Error al cargar minoristas: {error?.message}
        </Alert>
      )}

      <ListaMinoristas
        minoristas={minoristas || []}
        isLoading={isLoading}
        isError={isError}
        error={error as Error}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />

      <Dialog
        open={openFormDialog}
        onClose={handleCloseFormDialog}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          {minoristaAEditar ? 'Editar Minorista' : 'Añadir Nuevo Minorista'}
        </DialogTitle>
        <DialogContent>
          <FormularioMinorista
            minoristaInicial={minoristaAEditar}
            onSave={handleSaveMinorista}
            onCancel={handleCloseFormDialog}
            isLoading={
              createMinoristaMutation.isPending ||
              updateMinoristaMutation.isPending
            }
            error={
              createMinoristaMutation.isError
                ? createMinoristaMutation.error?.message
                : updateMinoristaMutation.isError
                  ? updateMinoristaMutation.error?.message
                  : null
            }
          />
        </DialogContent>
      </Dialog>
    </Container>
  );
};

export default GestionMinoristas;
