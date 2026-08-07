import { useState, useEffect, useCallback } from 'react';
import { getStoredToken, getStoredUser, isTokenExpired, removeStoredToken } from '../utils/jwt';
import { loginUser, signupUser, logoutUser } from '../services/auth';
import { User } from '../types';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const checkAuth = useCallback(() => {
    const storedToken = getStoredToken();
    const storedUser = getStoredUser();

    if (storedToken && !isTokenExpired(storedToken) && storedUser) {
      setToken(storedToken);
      setUser(storedUser);
    } else {
      removeStoredToken();
      setToken(null);
      setUser(null);
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await loginUser(email, password);
      setToken(response.access_token);
      setUser(response.user);
      return response;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await signupUser(email, password);
      setToken(response.access_token);
      setUser(response.user);
      return response;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    logoutUser();
    setToken(null);
    setUser(null);
  };

  return {
    user,
    token,
    isAuthenticated: !!token && !isTokenExpired(token),
    isLoading,
    login,
    signup,
    logout,
    checkAuth,
  };
}
