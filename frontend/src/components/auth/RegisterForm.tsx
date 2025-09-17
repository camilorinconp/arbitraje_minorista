// frontend/src/components/auth/RegisterForm.tsx

import React, { useState } from 'react';
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  Alert,
  IconButton,
  InputAdornment,
  Link,
  CircularProgress,
} from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
import { useAuth } from '../../contexts/AuthContext';

interface RegisterFormProps {
  onSwitchToLogin?: () => void;
  onRegistrationSuccess?: () => void;
}

const RegisterForm: React.FC<RegisterFormProps> = ({
  onSwitchToLogin,
  onRegistrationSuccess,
}) => {
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    full_name: '',
    password: '',
    password_confirm: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { register, isLoading } = useAuth();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    // Clear messages when user starts typing
    if (error) setError(null);
    if (success) setSuccess(null);
  };

  const validateForm = (): string | null => {
    if (!formData.email.trim()) {
      return 'Email es requerido';
    }

    if (!formData.username.trim()) {
      return 'Username es requerido';
    }

    if (formData.username.length < 3) {
      return 'Username debe tener al menos 3 caracteres';
    }

    if (!formData.full_name.trim()) {
      return 'Nombre completo es requerido';
    }

    if (!formData.password) {
      return 'Password es requerido';
    }

    if (formData.password.length < 8) {
      return 'Password debe tener al menos 8 caracteres';
    }

    // Password complexity check
    const hasUppercase = /[A-Z]/.test(formData.password);
    const hasLowercase = /[a-z]/.test(formData.password);
    const hasNumbers = /\d/.test(formData.password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(formData.password);

    if (!hasUppercase || !hasLowercase || !hasNumbers || !hasSpecialChar) {
      return 'Password debe contener mayúsculas, minúsculas, números y símbolos';
    }

    if (formData.password !== formData.password_confirm) {
      return 'Las passwords no coinciden';
    }

    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setIsSubmitting(true);

    // Validate form
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      setIsSubmitting(false);
      return;
    }

    try {
      await register({
        email: formData.email.trim(),
        username: formData.username.trim(),
        full_name: formData.full_name.trim(),
        password: formData.password,
        password_confirm: formData.password_confirm,
      });

      setSuccess('Cuenta creada exitosamente. Ya puedes iniciar sesión.');

      // Reset form
      setFormData({
        email: '',
        username: '',
        full_name: '',
        password: '',
        password_confirm: '',
      });

      // Call success callback
      if (onRegistrationSuccess) {
        onRegistrationSuccess();
      }

      // Auto-switch to login after 2 seconds
      setTimeout(() => {
        if (onSwitchToLogin) {
          onSwitchToLogin();
        }
      }, 2000);
    } catch (err: any) {
      console.error('Registration error:', err);

      if (err.response?.status === 400) {
        if (err.response.data?.detail?.includes('email')) {
          setError('Este email ya está registrado');
        } else if (err.response.data?.detail?.includes('username')) {
          setError('Este username ya está en uso');
        } else {
          setError(err.response.data?.detail || 'Datos inválidos');
        }
      } else if (err.response?.status === 429) {
        setError('Demasiados intentos. Intenta de nuevo más tarde');
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Error al crear la cuenta. Intenta de nuevo');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  const toggleConfirmPasswordVisibility = () => {
    setShowConfirmPassword(!showConfirmPassword);
  };

  const isFormLoading = isLoading || isSubmitting;

  return (
    <Paper
      elevation={3}
      sx={{
        p: 4,
        maxWidth: 500,
        width: '100%',
        mx: 'auto',
      }}
    >
      <Box component="form" onSubmit={handleSubmit}>
        <Typography
          variant="h4"
          component="h1"
          gutterBottom
          align="center"
          sx={{ mb: 3 }}
        >
          Crear Cuenta
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        <TextField
          fullWidth
          label="Email"
          name="email"
          type="email"
          value={formData.email}
          onChange={handleChange}
          margin="normal"
          required
          disabled={isFormLoading}
          autoComplete="email"
          autoFocus
        />

        <TextField
          fullWidth
          label="Username"
          name="username"
          type="text"
          value={formData.username}
          onChange={handleChange}
          margin="normal"
          required
          disabled={isFormLoading}
          autoComplete="username"
          helperText="Mínimo 3 caracteres"
        />

        <TextField
          fullWidth
          label="Nombre Completo"
          name="full_name"
          type="text"
          value={formData.full_name}
          onChange={handleChange}
          margin="normal"
          required
          disabled={isFormLoading}
          autoComplete="name"
        />

        <TextField
          fullWidth
          label="Password"
          name="password"
          type={showPassword ? 'text' : 'password'}
          value={formData.password}
          onChange={handleChange}
          margin="normal"
          required
          disabled={isFormLoading}
          autoComplete="new-password"
          helperText="Mínimo 8 caracteres con mayúsculas, minúsculas, números y símbolos"
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  onClick={togglePasswordVisibility}
                  edge="end"
                  disabled={isFormLoading}
                >
                  {showPassword ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </InputAdornment>
            ),
          }}
        />

        <TextField
          fullWidth
          label="Confirmar Password"
          name="password_confirm"
          type={showConfirmPassword ? 'text' : 'password'}
          value={formData.password_confirm}
          onChange={handleChange}
          margin="normal"
          required
          disabled={isFormLoading}
          autoComplete="new-password"
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  onClick={toggleConfirmPasswordVisibility}
                  edge="end"
                  disabled={isFormLoading}
                >
                  {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </InputAdornment>
            ),
          }}
        />

        <Button
          type="submit"
          fullWidth
          variant="contained"
          size="large"
          disabled={isFormLoading}
          sx={{ mt: 3, mb: 2 }}
        >
          {isFormLoading ? (
            <CircularProgress size={24} color="inherit" />
          ) : (
            'Crear Cuenta'
          )}
        </Button>

        {onSwitchToLogin && (
          <Box sx={{ textAlign: 'center', mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              ¿Ya tienes cuenta?{' '}
              <Link
                component="button"
                type="button"
                onClick={onSwitchToLogin}
                sx={{ cursor: 'pointer' }}
                disabled={isFormLoading}
              >
                Inicia sesión aquí
              </Link>
            </Typography>
          </Box>
        )}
      </Box>
    </Paper>
  );
};

export default RegisterForm;
