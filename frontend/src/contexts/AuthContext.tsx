// frontend/src/contexts/AuthContext.tsx

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from 'react';
import {
  User,
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  getCurrentUser,
  isAuthenticated,
  getStoredTokens,
  clearTokens,
} from '../api/authApi';
import type { LoginRequest, RegisterRequest } from '../api/authApi';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (userData: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasRole: (role: string) => boolean;
  hasPermission: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticatedState, setIsAuthenticatedState] = useState(false);

  // Role permissions mapping (matches backend)
  const rolePermissions = {
    admin: ['read', 'write', 'delete', 'scrape', 'manage_users'],
    scraper: ['read', 'write', 'scrape'],
    user: ['read'],
  };

  // Initialize auth state on mount
  useEffect(() => {
    const initializeAuth = async () => {
      setIsLoading(true);

      try {
        if (isAuthenticated()) {
          // Try to get current user
          const currentUser = await getCurrentUser();
          setUser(currentUser);
          setIsAuthenticatedState(true);
        } else {
          // Clear any stale tokens
          clearTokens();
          setUser(null);
          setIsAuthenticatedState(false);
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
        // Clear tokens on error
        clearTokens();
        setUser(null);
        setIsAuthenticatedState(false);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (credentials: LoginRequest): Promise<void> => {
    setIsLoading(true);
    try {
      // Login and get tokens
      await apiLogin(credentials);

      // Get user data
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      setIsAuthenticatedState(true);
    } catch (error) {
      setUser(null);
      setIsAuthenticatedState(false);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (userData: RegisterRequest): Promise<void> => {
    setIsLoading(true);
    try {
      await apiRegister(userData);
      // Note: After registration, user might need to verify email
      // We don't automatically log them in
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setIsLoading(true);
    try {
      await apiLogout();
    } catch (error) {
      console.error('Error during logout:', error);
      // Continue with local logout even if server request fails
    } finally {
      setUser(null);
      setIsAuthenticatedState(false);
      setIsLoading(false);
    }
  };

  const refreshUser = async (): Promise<void> => {
    if (!isAuthenticated()) {
      setUser(null);
      setIsAuthenticatedState(false);
      return;
    }

    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      setIsAuthenticatedState(true);
    } catch (error) {
      console.error('Error refreshing user:', error);
      setUser(null);
      setIsAuthenticatedState(false);
      clearTokens();
      throw error;
    }
  };

  const hasRole = (role: string): boolean => {
    if (!user) return false;
    return user.role === role;
  };

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;

    // Superuser (admin) has all permissions
    if (user.role === 'admin') return true;

    // Check role-based permissions
    const userPermissions =
      rolePermissions[user.role as keyof typeof rolePermissions] || [];
    return userPermissions.includes(permission);
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: isAuthenticatedState,
    login,
    register,
    logout,
    refreshUser,
    hasRole,
    hasPermission,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Hook for checking specific roles
export const useRequireRole = (requiredRole: string) => {
  const { user, hasRole, isLoading } = useAuth();

  return {
    hasAccess: hasRole(requiredRole),
    isLoading,
    user,
  };
};

// Hook for checking specific permissions
export const useRequirePermission = (requiredPermission: string) => {
  const { user, hasPermission, isLoading } = useAuth();

  return {
    hasAccess: hasPermission(requiredPermission),
    isLoading,
    user,
  };
};
