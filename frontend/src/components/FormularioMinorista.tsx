import React, { useState, useEffect } from 'react';
import {
  TextField,
  Button,
  Box,
  Typography,
  Switch,
  FormControlLabel,
  Alert,
} from '@mui/material';
import { MinoristaBase, Minorista } from '../api/gestionDatosApi';

interface FormularioMinoristaProps {
  minoristaInicial?: Minorista; // Para edición
  onSave: (minorista: MinoristaBase) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
  error?: string | null;
}

const FormularioMinorista: React.FC<FormularioMinoristaProps> = ({
  minoristaInicial,
  onSave,
  onCancel,
  isLoading,
  error,
}) => {
  const [formData, setFormData] = useState<MinoristaBase>(
    minoristaInicial
      ? {
          nombre: minoristaInicial.nombre,
          url_base: minoristaInicial.url_base,
          activo: minoristaInicial.activo,
          name_selector: minoristaInicial.name_selector,
          price_selector: minoristaInicial.price_selector,
          image_selector: minoristaInicial.image_selector,
          discovery_url: minoristaInicial.discovery_url,
          product_link_selector: minoristaInicial.product_link_selector,
        }
      : {
          nombre: '',
          url_base: '',
          activo: true,
          name_selector: '',
          price_selector: '',
          image_selector: '',
          discovery_url: '',
          product_link_selector: '',
        }
  );

  useEffect(() => {
    if (minoristaInicial) {
      setFormData({
        nombre: minoristaInicial.nombre,
        url_base: minoristaInicial.url_base,
        activo: minoristaInicial.activo,
        name_selector: minoristaInicial.name_selector,
        price_selector: minoristaInicial.price_selector,
        image_selector: minoristaInicial.image_selector,
        discovery_url: minoristaInicial.discovery_url,
        product_link_selector: minoristaInicial.product_link_selector,
      });
    } else {
      setFormData({
        nombre: '',
        url_base: '',
        activo: true,
        name_selector: '',
        price_selector: '',
        image_selector: '',
        discovery_url: '',
        product_link_selector: '',
      });
    }
  }, [minoristaInicial]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, checked, type } = e.target;
    setFormData((prev: MinoristaBase) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSave(formData);
  };

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{ mt: 3, p: 3, border: '1px solid #ccc', borderRadius: '8px' }}
    >
      <Typography variant="h5" gutterBottom>
        {minoristaInicial ? 'Editar Minorista' : 'Añadir Nuevo Minorista'}
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

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
        value={formData.name_selector || ''}
        onChange={handleChange}
        fullWidth
        margin="normal"
      />
      <TextField
        label="Selector CSS para Precio (ej. span.price-value)"
        name="price_selector"
        value={formData.price_selector || ''}
        onChange={handleChange}
        fullWidth
        margin="normal"
      />
      <TextField
        label="Selector CSS para Imagen (ej. img.product-image)"
        name="image_selector"
        value={formData.image_selector || ''}
        onChange={handleChange}
        fullWidth
        margin="normal"
      />
      <TextField
        label="URL de Descubrimiento (ej. https://www.ejemplo.com/ofertas)"
        name="discovery_url"
        value={formData.discovery_url || ''}
        onChange={handleChange}
        fullWidth
        margin="normal"
        type="url"
      />
      <TextField
        label="Selector CSS para Enlace de Producto (ej. a.product-card)"
        name="product_link_selector"
        value={formData.product_link_selector || ''}
        onChange={handleChange}
        fullWidth
        margin="normal"
      />
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 2 }}>
        <Button onClick={onCancel} disabled={isLoading}>
          Cancelar
        </Button>
        <Button
          type="submit"
          variant="contained"
          color="primary"
          disabled={isLoading}
        >
          {isLoading ? 'Guardando...' : 'Guardar'}
        </Button>
      </Box>
    </Box>
  );
};

export default FormularioMinorista;
