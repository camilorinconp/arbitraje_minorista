// frontend/src/components/auth/ProtectedRoute.tsx

import React, { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Box, CircularProgress, Typography, Alert } from '@mui/material';
import { useAuth } from '../../contexts/AuthContext';

interface ProtectedRouteProps {
  children: ReactNode;
  requireRole?: string;
  requirePermission?: string;
  fallbackPath?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireRole,
  requirePermission,
  fallbackPath = '/login',
}) => {
  const { isAuthenticated, isLoading, hasRole, hasPermission, user } =
    useAuth();
  const location = useLocation();

  // Show loading while auth state is being determined
  if (isLoading) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="50vh"
        gap={2}
      >
        <CircularProgress size={40} />
        <Typography variant="body1" color="text.secondary">
          Verificando autenticación...
        </Typography>
      </Box>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to={fallbackPath} state={{ from: location }} replace />;
  }

  // Check role requirement
  if (requireRole && !hasRole(requireRole)) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="50vh"
        gap={2}
        p={3}
      >
        <Alert severity="error" sx={{ maxWidth: 500 }}>
          <Typography variant="h6" gutterBottom>
            Acceso Denegado
          </Typography>
          <Typography variant="body2">
            No tienes permisos para acceder a esta página. Se requiere el rol:{' '}
            <strong>{requireRole}</strong>
          </Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            Tu rol actual: <strong>{user?.role}</strong>
          </Typography>
        </Alert>
      </Box>
    );
  }

  // Check permission requirement
  if (requirePermission && !hasPermission(requirePermission)) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="50vh"
        gap={2}
        p={3}
      >
        <Alert severity="error" sx={{ maxWidth: 500 }}>
          <Typography variant="h6" gutterBottom>
            Permisos Insuficientes
          </Typography>
          <Typography variant="body2">
            No tienes el permiso necesario para acceder a esta página.
          </Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            Permiso requerido: <strong>{requirePermission}</strong>
          </Typography>
          <Typography variant="body2">
            Tu rol: <strong>{user?.role}</strong>
          </Typography>
        </Alert>
      </Box>
    );
  }

  // User is authenticated and has required permissions
  return <>{children}</>;
};

export default ProtectedRoute;

// Convenience components for common use cases
export const AdminRoute: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ProtectedRoute requireRole="admin">{children}</ProtectedRoute>
);

export const ScraperRoute: React.FC<{ children: ReactNode }> = ({
  children,
}) => <ProtectedRoute requirePermission="scrape">{children}</ProtectedRoute>;

export const WriteRoute: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ProtectedRoute requirePermission="write">{children}</ProtectedRoute>
);

export const ReadRoute: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ProtectedRoute requirePermission="read">{children}</ProtectedRoute>
);
