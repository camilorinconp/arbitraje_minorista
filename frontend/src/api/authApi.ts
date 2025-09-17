// frontend/src/api/authApi.ts

import axios from 'axios';

const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// --- Interfaces ---

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  password_confirm: string;
  full_name: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login: string | null;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
}

export interface MessageResponse {
  message: string;
}

// --- Token Management ---

export const getStoredTokens = () => {
  const accessToken = localStorage.getItem('access_token');
  const refreshToken = localStorage.getItem('refresh_token');
  return { accessToken, refreshToken };
};

export const storeTokens = (tokens: TokenResponse) => {
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
  localStorage.setItem('token_type', tokens.token_type);
  localStorage.setItem('expires_in', tokens.expires_in.toString());
  localStorage.setItem('token_timestamp', Date.now().toString());
};

export const clearTokens = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('token_type');
  localStorage.removeItem('expires_in');
  localStorage.removeItem('token_timestamp');
};

export const isTokenExpired = (): boolean => {
  const timestamp = localStorage.getItem('token_timestamp');
  const expiresIn = localStorage.getItem('expires_in');

  if (!timestamp || !expiresIn) return true;

  const tokenAge = Date.now() - parseInt(timestamp);
  const expirationTime = parseInt(expiresIn) * 1000; // Convert to milliseconds

  return tokenAge >= expirationTime;
};

// --- API Functions ---

export const login = async (
  credentials: LoginRequest
): Promise<TokenResponse> => {
  try {
    const response = await axios.post<TokenResponse>(
      `${API_BASE_URL}/auth/login`,
      credentials
    );

    // Store tokens automatically
    storeTokens(response.data);

    return response.data;
  } catch (error) {
    console.error('Error during login:', error);
    throw error;
  }
};

export const register = async (userData: RegisterRequest): Promise<User> => {
  try {
    const response = await axios.post<User>(
      `${API_BASE_URL}/auth/register`,
      userData
    );
    return response.data;
  } catch (error) {
    console.error('Error during registration:', error);
    throw error;
  }
};

export const getCurrentUser = async (): Promise<User> => {
  try {
    const { accessToken } = getStoredTokens();

    if (!accessToken) {
      throw new Error('No access token found');
    }

    const response = await axios.get<User>(`${API_BASE_URL}/auth/me`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error getting current user:', error);
    throw error;
  }
};

export const refreshToken = async (): Promise<TokenResponse> => {
  try {
    const { refreshToken } = getStoredTokens();

    if (!refreshToken) {
      throw new Error('No refresh token found');
    }

    const response = await axios.post<TokenResponse>(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: refreshToken }
    );

    // Store new tokens
    storeTokens(response.data);

    return response.data;
  } catch (error) {
    console.error('Error refreshing token:', error);
    // Clear tokens if refresh fails
    clearTokens();
    throw error;
  }
};

export const logout = async (): Promise<void> => {
  try {
    const { accessToken } = getStoredTokens();

    if (accessToken) {
      await axios.post(
        `${API_BASE_URL}/auth/logout`,
        {},
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );
    }
  } catch (error) {
    console.error('Error during logout:', error);
    // Continue with local logout even if server request fails
  } finally {
    // Always clear local tokens
    clearTokens();
  }
};

export const changePassword = async (
  passwordData: PasswordChangeRequest
): Promise<MessageResponse> => {
  try {
    const { accessToken } = getStoredTokens();

    if (!accessToken) {
      throw new Error('No access token found');
    }

    const response = await axios.post<MessageResponse>(
      `${API_BASE_URL}/auth/change-password`,
      passwordData,
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error changing password:', error);
    throw error;
  }
};

// --- Axios Interceptor Setup ---

export const setupAxiosInterceptors = () => {
  // Request interceptor to add auth header
  axios.interceptors.request.use(
    (config) => {
      const { accessToken } = getStoredTokens();

      if (accessToken && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${accessToken}`;
      }

      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor to handle token refresh
  axios.interceptors.response.use(
    (response) => {
      return response;
    },
    async (error) => {
      const originalRequest = error.config;

      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true;

        try {
          // Try to refresh token
          await refreshToken();

          // Retry original request with new token
          const { accessToken } = getStoredTokens();
          originalRequest.headers.Authorization = `Bearer ${accessToken}`;

          return axios(originalRequest);
        } catch (refreshError) {
          // Refresh failed, redirect to login
          clearTokens();

          // Only redirect if we're not already on the login page
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }

          return Promise.reject(refreshError);
        }
      }

      return Promise.reject(error);
    }
  );
};

// --- Utility Functions ---

export const isAuthenticated = (): boolean => {
  const { accessToken } = getStoredTokens();
  return !!accessToken && !isTokenExpired();
};

export const hasRole = (requiredRole: string): boolean => {
  // This would need to decode JWT or fetch user data
  // For now, we'll implement this in the user context
  return false;
};

export const hasPermission = (permission: string): boolean => {
  // This would need to decode JWT or fetch user data
  // For now, we'll implement this in the user context
  return false;
};
