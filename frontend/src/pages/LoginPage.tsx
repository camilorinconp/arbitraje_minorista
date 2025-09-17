// frontend/src/pages/LoginPage.tsx

import React, { useState, useEffect } from 'react';
import { Container, Box, Tabs, Tab } from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import LoginForm from '../components/auth/LoginForm';
import RegisterForm from '../components/auth/RegisterForm';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`auth-tabpanel-${index}`}
      aria-labelledby={`auth-tab-${index}`}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
};

const LoginPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Redirect if already authenticated
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      // Get the intended destination from navigation state, or default to dashboard
      const intendedPath =
        (location.state as any)?.from?.pathname || '/dashboard';
      navigate(intendedPath, { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate, location]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const switchToLogin = () => {
    setActiveTab(0);
  };

  const switchToRegister = () => {
    setActiveTab(1);
  };

  const handleRegistrationSuccess = () => {
    // Switch to login tab after successful registration
    setTimeout(() => {
      setActiveTab(0);
    }, 1500);
  };

  // Don't render anything while checking auth state
  if (isLoading) {
    return null;
  }

  // Don't render if already authenticated (will redirect)
  if (isAuthenticated) {
    return null;
  }

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          py: 4,
        }}
      >
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            aria-label="auth tabs"
            centered
          >
            <Tab label="Iniciar Sesión" id="auth-tab-0" />
            <Tab label="Crear Cuenta" id="auth-tab-1" />
          </Tabs>
        </Box>

        <TabPanel value={activeTab} index={0}>
          <LoginForm onSwitchToRegister={switchToRegister} />
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <RegisterForm
            onSwitchToLogin={switchToLogin}
            onRegistrationSuccess={handleRegistrationSuccess}
          />
        </TabPanel>
      </Box>
    </Container>
  );
};

export default LoginPage;
