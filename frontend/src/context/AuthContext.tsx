import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { decodeJwtPayload, isCognitoConfigured, getCognitoLogoutUrl } from '../api/cognito';

interface AuthContextValue {
  isAuthenticated: boolean;
  userEmail: string | null;
  /** Mock login — only used when Cognito is not configured */
  loginMock: (email: string) => void;
  /** Set real tokens from Cognito code exchange */
  setTokens: (idToken: string, accessToken: string, refreshToken: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  // Restore session on mount
  useEffect(() => {
    const saved = localStorage.getItem('token');
    const email = localStorage.getItem('userEmail');
    if (saved) {
      setToken(saved);
      setUserEmail(email);
    }
  }, []);

  const loginMock = (email: string) => {
    const fakeToken = 'mock-jwt-' + Date.now();
    localStorage.setItem('token', fakeToken);
    localStorage.setItem('userEmail', email);
    setToken(fakeToken);
    setUserEmail(email);
  };

  const setTokens = (idToken: string, accessToken: string, refreshToken: string) => {
    // Store the access token for API calls (Authorization header)
    localStorage.setItem('token', accessToken);
    localStorage.setItem('id_token', idToken);
    localStorage.setItem('refresh_token', refreshToken);

    // Extract email from ID token
    try {
      const payload = decodeJwtPayload(idToken);
      const email = (payload.email as string) || (payload['cognito:username'] as string) || 'user';
      localStorage.setItem('userEmail', email);
      setUserEmail(email);
    } catch {
      localStorage.setItem('userEmail', 'user');
      setUserEmail('user');
    }

    setToken(accessToken);
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('id_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('userEmail');
    setToken(null);
    setUserEmail(null);

    // If Cognito is configured, redirect to Cognito logout to clear their session too
    if (isCognitoConfigured()) {
      window.location.href = getCognitoLogoutUrl();
    }
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated: !!token, userEmail, loginMock, setTokens, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
