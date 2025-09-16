import React, { useState } from 'react';
import { TextField, Button, Box, Typography, Switch, FormControlLabel, Alert } from '@mui/material';
import { createMinorista, MinoristaBase } from '../api/gestionDatosApi';

const FormularioMinorista: React.FC = () => {
  const [formData, setFormData] = useState<MinoristaBase>({
    nombre: '',
    url_base: '',
    activo: true,
    name_selector: '',
    price_selector: '',
    image_selector: '',
    discovery_url: '',
    product_link_selector: '',
  });
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, checked, type } = e.target;
    setFormData((prev: MinoristaBase) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      // Asegurarse de que url_base sea una cadena válida antes de enviar
      const dataToSend = { ...formData, url_base: String(formData.url_base) };
      await createMinorista(dataToSend);
      setSuccess('Minorista creado exitosamente!');
      setFormData({
        nombre: '',
        url_base: '' as any,
        activo: true,
        name_selector: '',
        price_selector: '',
        image_selector: '',
      });
    } catch (err) {
      setError('Error al crear el minorista. Verifique los datos e intente de nuevo.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3, p: 3, border: '1px solid #ccc', borderRadius: '8px' }}>
      <Typography variant="h5" gutterBottom>
        Añadir Nuevo Minorista
      </Typography>
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      
      <TextField
        label="Nombre del Minorista"
        name="nombre"
        value={formData.nombre}
        onChange={handleChange}
        fullWidth
        margin="normal"
        required
      />
      <TextField
        label="URL Base (ej. https://www.ejemplo.com)"
        name="url_base"
        value={formData.url_base}
        onChange={handleChange}
        fullWidth
        margin="normal"
        required
        type="url"
      />
      <FormControlLabel
        control={
          <Switch
            checked={formData.activo}
            onChange={handleChange}
            name="activo"
            color="primary"
          />
        }
        label="Activo para Scrapeo"
        sx={{ mt: 1, mb: 2 }}
      />
      <TextField
        label="Selector CSS para Nombre (ej. h1.product-title)"
        name="name_selector"
        value={formData.name_selector}
        onChange={handleChange}
        fullWidth
        margin="normal"
      />
      <TextField
        label="Selector CSS para Precio (ej. span.price-value)"
        name="price_selector"
        value={formData.price_selector}
        onChange={handleChange}
        fullWidth
        margin="normal"
      />
      <TextField
        label="Selector CSS para Imagen (ej. img.product-image)"
        name="image_selector"
        value={formData.image_selector}
        onChange={handleChange}
        fullWidth
        margin="normal"
      />
      <Button type="submit" variant="contained" color="primary" disabled={loading} sx={{ mt: 2 }}>
        {loading ? 'Guardando...' : 'Guardar Minorista'}
      </Button>
    </Box>
  );
};

export default FormularioMinorista;
