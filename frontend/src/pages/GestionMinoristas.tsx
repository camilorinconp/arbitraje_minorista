import React from 'react';
import { Container, Typography, Box } from '@mui/material';
import ListaMinoristas from '../components/ListaMinoristas';
import FormularioMinorista from '../components/FormularioMinorista'; // Lo crearemos a continuación

const GestionMinoristas: React.FC = () => {
  return (
    <Container>
      <Typography variant="h4" gutterBottom>
        Gestión de Minoristas
      </Typography>
      
      <Box sx={{ my: 4 }}>
        <FormularioMinorista />
      </Box>

      <Box sx={{ my: 4 }}>
        <ListaMinoristas />
      </Box>
    </Container>
  );
};

export default GestionMinoristas;