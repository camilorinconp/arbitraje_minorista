import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Container, Button } from '@mui/material';
import ListaProductos from './components/ListaProductos';
import GestionMinoristas from './pages/GestionMinoristas';

function App() {
  return (
    <Router>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Herramienta de Arbitraje
          </Typography>
          <Button color="inherit" component={Link} to="/">Productos</Button>
          <Button color="inherit" component={Link} to="/minoristas">Gestionar Minoristas</Button>
        </Toolbar>
      </AppBar>
      <Container sx={{ mt: 4 }}>
        <Routes>
          <Route path="/" element={<ListaProductos />} />
          <Route path="/minoristas" element={<GestionMinoristas />} />
        </Routes>
      </Container>
    </Router>
  );
}

export default App;
