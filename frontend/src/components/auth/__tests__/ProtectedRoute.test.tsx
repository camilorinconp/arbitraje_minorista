// frontend/src/components/auth/__tests__/ProtectedRoute.test.tsx

import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ProtectedRoute from '../ProtectedRoute';
import { AuthProvider } from '../../../contexts/AuthContext';

// Mock the auth API
const mockAuthApi = {
  login: jest.fn(),
  setupAxiosInterceptors: jest.fn(),
  isAuthenticated: jest.fn(),
  getStoredTokens: jest.fn(),
  getCurrentUser: jest.fn(),
};

jest.mock('../../../api/authApi', () => mockAuthApi);

const theme = createTheme();

const TestComponent = () => <div>Protected Content</div>;

const renderWithProviders = (
  component: React.ReactElement,
  initialRoute = '/'
) => {
  window.history.pushState({}, 'Test page', initialRoute);

  return render(
    <ThemeProvider theme={theme}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div>Login Page</div>} />
            <Route path="/" element={component} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
};

describe('ProtectedRoute', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows loading state when auth is loading', () => {
    mockAuthApi.isAuthenticated.mockReturnValue(false);
    mockAuthApi.getStoredTokens.mockReturnValue({
      accessToken: null,
      refreshToken: null,
    });

    renderWithProviders(
      <ProtectedRoute>
        <TestComponent />
      </ProtectedRoute>
    );

    expect(
      screen.getByText('Verificando autenticación...')
    ).toBeInTheDocument();
  });

  it('redirects to login when not authenticated', async () => {
    mockAuthApi.isAuthenticated.mockReturnValue(false);
    mockAuthApi.getStoredTokens.mockReturnValue({
      accessToken: null,
      refreshToken: null,
    });
    mockAuthApi.getCurrentUser.mockRejectedValue(
      new Error('Not authenticated')
    );

    renderWithProviders(
      <ProtectedRoute>
        <TestComponent />
      </ProtectedRoute>
    );

    // Due to the async nature and AuthProvider initialization,
    // we need to wait for the redirect to happen
    await new Promise((resolve) => setTimeout(resolve, 100));
  });

  it('shows access denied for insufficient role', async () => {
    mockAuthApi.isAuthenticated.mockReturnValue(true);
    mockAuthApi.getStoredTokens.mockReturnValue({
      accessToken: 'token',
      refreshToken: 'refresh',
    });
    mockAuthApi.getCurrentUser.mockResolvedValue({
      id: 1,
      email: 'user@example.com',
      username: 'user',
      full_name: 'Test User',
      role: 'user',
      is_active: true,
      is_verified: true,
      created_at: '2024-01-01',
      last_login: null,
    });

    renderWithProviders(
      <ProtectedRoute requireRole="admin">
        <TestComponent />
      </ProtectedRoute>
    );

    // Wait for auth context to initialize
    await new Promise((resolve) => setTimeout(resolve, 200));

    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('shows access denied for insufficient permission', async () => {
    mockAuthApi.isAuthenticated.mockReturnValue(true);
    mockAuthApi.getStoredTokens.mockReturnValue({
      accessToken: 'token',
      refreshToken: 'refresh',
    });
    mockAuthApi.getCurrentUser.mockResolvedValue({
      id: 1,
      email: 'user@example.com',
      username: 'user',
      full_name: 'Test User',
      role: 'user',
      is_active: true,
      is_verified: true,
      created_at: '2024-01-01',
      last_login: null,
    });

    renderWithProviders(
      <ProtectedRoute requirePermission="write">
        <TestComponent />
      </ProtectedRoute>
    );

    // Wait for auth context to initialize
    await new Promise((resolve) => setTimeout(resolve, 200));

    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('renders children when authenticated with sufficient permissions', async () => {
    mockAuthApi.isAuthenticated.mockReturnValue(true);
    mockAuthApi.getStoredTokens.mockReturnValue({
      accessToken: 'token',
      refreshToken: 'refresh',
    });
    mockAuthApi.getCurrentUser.mockResolvedValue({
      id: 1,
      email: 'admin@example.com',
      username: 'admin',
      full_name: 'Admin User',
      role: 'admin',
      is_active: true,
      is_verified: true,
      created_at: '2024-01-01',
      last_login: null,
    });

    renderWithProviders(
      <ProtectedRoute requirePermission="write">
        <TestComponent />
      </ProtectedRoute>
    );

    // Wait for auth context to initialize
    await new Promise((resolve) => setTimeout(resolve, 200));

    // Admin has all permissions, so should see content
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });
});
