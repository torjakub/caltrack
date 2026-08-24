import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import * as authApi from "../api/auth";
import { getToken, setRefreshToken, setToken } from "../api/client";
import type { UserOut } from "../api/types";

interface AuthContextValue {
  user: UserOut | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  setup: (username: string, password: string, email?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await authApi.me());
    } catch {
      // apiFetch already tried a refresh-and-retry; if we still failed the
      // session is unrecoverable (refresh token expired/revoked).
      setToken(null);
      setRefreshToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = useCallback(
    async (username: string, password: string) => {
      const tokens = await authApi.login(username, password);
      setToken(tokens.access_token);
      setRefreshToken(tokens.refresh_token);
      await loadUser();
    },
    [loadUser]
  );

  const setup = useCallback(
    async (username: string, password: string, email?: string) => {
      const tokens = await authApi.setup(username, password, email);
      setToken(tokens.access_token);
      setRefreshToken(tokens.refresh_token);
      await loadUser();
    },
    [loadUser]
  );

  const logout = useCallback(() => {
    setToken(null);
    setRefreshToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, setup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
