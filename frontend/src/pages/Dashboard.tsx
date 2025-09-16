// frontend/src/pages/Dashboard.tsx

import React from 'react';
import { Box, Container, Typography } from '@mui/material';
import ListaProductos from '../components/ListaProductos';

const Dashboard: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Dashboard de Productos
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          Aquí se muestran los productos rastreados y sus precios actuales.
        </Typography>
        
        {/* Integración del componente que muestra la lista de productos */}
        <Box sx={{ mt: 4 }}>
          <ListaProductos />
        </Box>
      </Box>
    </Container>
  );
};

export default Dashboard;
