import { useState, useEffect, createContext, useContext, ReactNode } from 'react';
import { authAPI } from '@/integrations/api/client';

interface User {
  id: number;
  email: string;
  username: string;
  user_code: string | null;
  theme: string;
  credits: number;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>;
  signUp: (email: string, password: string, username: string) => Promise<{ error: Error | null }>;
  signOut: () => void;
  refreshProfile: () => Promise<void>;
  updateProfile: (data: { username?: string; theme?: string }) => Promise<{ error: Error | null }>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = async () => {
    try {
      const response = await authAPI.me();
      setUser(response.data);
    } catch {
      console.error('Error fetching profile');
      setUser(null);
    }
  };

  const refreshProfile = async () => {
    await fetchProfile();
  };

  useEffect(() => {
    // Check for existing token
    const token = localStorage.getItem('token');
    if (token) {
      fetchProfile().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const signIn = async (email: string, password: string) => {
    try {
      const response = await authAPI.login(email, password);
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      await fetchProfile();
      return { error: null };
    } catch (error) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      return { error: new Error(axiosError.response?.data?.detail || 'Login failed') };
    }
  };

  const signUp = async (email: string, password: string, username: string) => {
    try {
      const response = await authAPI.register(email, password, username);
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      await fetchProfile();
      return { error: null };
    } catch (error) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      return { error: new Error(axiosError.response?.data?.detail || 'Registration failed') };
    }
  };

  const updateProfile = async (data: { username?: string; theme?: string }) => {
    try {
      const response = await authAPI.updateProfile(data);
      setUser(response.data);
      return { error: null };
    } catch (error) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      return { error: new Error(axiosError.response?.data?.detail || 'Update failed') };
    }
  };

  const signOut = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        signIn,
        signUp,
        signOut,
        refreshProfile,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
