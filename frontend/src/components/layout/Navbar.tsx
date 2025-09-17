// frontend/src/components/layout/Navbar.tsx

import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Menu,
  MenuItem,
  Avatar,
  Box,
  IconButton,
  Divider,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  AccountCircle,
  Logout,
  Dashboard,
  Store,
  AdminPanelSettings,
  Settings,
} from '@mui/icons-material';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const Navbar: React.FC = () => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const { user, logout, hasRole, hasPermission } = useAuth();
  const navigate = useNavigate();

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Error during logout:', error);
      // Navigate to login anyway
      navigate('/login');
    } finally {
      handleClose();
    }
  };

  const handleProfile = () => {
    navigate('/profile');
    handleClose();
  };

  const getUserInitials = (fullName: string): string => {
    return fullName
      .split(' ')
      .map((name) => name.charAt(0))
      .slice(0, 2)
      .join('')
      .toUpperCase();
  };

  const getRoleColor = (role: string): string => {
    switch (role) {
      case 'admin':
        return '#f44336'; // Red
      case 'scraper':
        return '#ff9800'; // Orange
      default:
        return '#2196f3'; // Blue
    }
  };

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          <Link
            to="/dashboard"
            style={{
              color: 'inherit',
              textDecoration: 'none',
            }}
          >
            Herramienta de Arbitraje
          </Link>
        </Typography>

        {/* Navigation Links */}
        <Box sx={{ display: 'flex', gap: 1, mr: 2 }}>
          <Button
            color="inherit"
            component={Link}
            to="/dashboard"
            startIcon={<Dashboard />}
          >
            Dashboard
          </Button>

          {hasPermission('write') && (
            <Button
              color="inherit"
              component={Link}
              to="/minoristas"
              startIcon={<Store />}
            >
              Minoristas
            </Button>
          )}

          {hasRole('admin') && (
            <Button
              color="inherit"
              component={Link}
              to="/admin"
              startIcon={<AdminPanelSettings />}
            >
              Admin
            </Button>
          )}
        </Box>

        {/* User Menu */}
        {user && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography
              variant="body2"
              sx={{ display: { xs: 'none', sm: 'block' } }}
            >
              {user.full_name}
            </Typography>

            <IconButton size="large" onClick={handleMenu} color="inherit">
              <Avatar
                sx={{
                  bgcolor: getRoleColor(user.role),
                  width: 32,
                  height: 32,
                  fontSize: '0.875rem',
                }}
              >
                {getUserInitials(user.full_name)}
              </Avatar>
            </IconButton>

            <Menu
              id="menu-appbar"
              anchorEl={anchorEl}
              anchorOrigin={{
                vertical: 'bottom',
                horizontal: 'right',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              open={Boolean(anchorEl)}
              onClose={handleClose}
              PaperProps={{
                sx: { minWidth: 200 },
              }}
            >
              {/* User Info */}
              <MenuItem disabled>
                <Box>
                  <Typography variant="subtitle2" noWrap>
                    {user.full_name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" noWrap>
                    {user.email}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{
                      display: 'block',
                      color: getRoleColor(user.role),
                      fontWeight: 'bold',
                      textTransform: 'uppercase',
                      fontSize: '0.675rem',
                    }}
                  >
                    {user.role}
                  </Typography>
                </Box>
              </MenuItem>

              <Divider />

              <MenuItem onClick={handleProfile}>
                <ListItemIcon>
                  <AccountCircle fontSize="small" />
                </ListItemIcon>
                <ListItemText>Perfil</ListItemText>
              </MenuItem>

              <MenuItem
                onClick={() => {
                  navigate('/settings');
                  handleClose();
                }}
              >
                <ListItemIcon>
                  <Settings fontSize="small" />
                </ListItemIcon>
                <ListItemText>Configuración</ListItemText>
              </MenuItem>

              <Divider />

              <MenuItem onClick={handleLogout}>
                <ListItemIcon>
                  <Logout fontSize="small" />
                </ListItemIcon>
                <ListItemText>Cerrar Sesión</ListItemText>
              </MenuItem>
            </Menu>
          </Box>
        )}
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
