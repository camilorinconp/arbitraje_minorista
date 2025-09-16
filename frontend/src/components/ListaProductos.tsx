// frontend/src/components/ListaProductos.tsx

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getProductos } from '../api/gestionDatosApi';
import { 
  Typography, 
  CircularProgress, 
  Alert, 
  List, 
  ListItem, 
  ListItemText, 
  ListItemAvatar, 
  Avatar, 
  Divider, 
  Box
} from '@mui/material';

const ListaProductos: React.FC = () => {
  const { data: productos, error, isLoading, isError } = useQuery({
    queryKey: ['productos'],
    queryFn: getProductos,
  });

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (isError) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Error al cargar los productos: {error.message}
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h5" component="h2" gutterBottom>
        Productos Rastreados
      </Typography>
      {productos?.length === 0 ? (
        <Alert severity="info">No hay productos rastreados aún. Intenta scrapear un producto para empezar.</Alert>
      ) : (
        <List>
          {productos?.map((producto) => (
            <React.Fragment key={producto.id}>
              <ListItem alignItems="flex-start">
                <ListItemAvatar>
                  <Avatar alt={producto.name} src={producto.image_url || undefined} />
                </ListItemAvatar>
                <ListItemText
                  primary={
                    <Typography variant="h6">
                      <a href={producto.product_url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none', color: 'inherit' }}>
                        {producto.name}
                      </a>
                    </Typography>
                  }
                  secondary={
                    <Box>
                      <Typography component="span" variant="body2" color="text.primary" sx={{ fontWeight: 'bold' }}>
                        Precio: ${producto.price.toFixed(2)}
                      </Typography>
                      <br />
                      <Typography component="span" variant="body2" color="text.secondary">
                        Minorista: {producto.minorista?.nombre || 'Desconocido'}
                      </Typography>
                      <br />
                      <Typography component="span" variant="body2" color="text.secondary">
                        Último rastreo: {new Date(producto.last_scraped_at).toLocaleString()}
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
    </Box>
  );
};

export default ListaProductos;
