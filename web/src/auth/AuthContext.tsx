import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, clearSession, refreshSession, setLogoutHandler, setSession } from "../api/client";

export type User = { id: string; email: string; full_name: string; about: string; created_at: string };

type AuthState = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (u: User) => void;
};

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const qc = useQueryClient();

  const loadMe = useCallback(async () => setUser(await api<User>("/users/me")), []);

  useEffect(() => {
    setLogoutHandler(() => {
      setUser(null);
      qc.clear();
    });
    (async () => {
      if (await refreshSession()) await loadMe().catch(() => setUser(null));
      setLoading(false);
    })();
  }, [loadMe, qc]);

  const login = async (email: string, password: string) => {
    await setSession(await api("/auth/login", { method: "POST", json: { email, password } }));
    await loadMe();
  };
  const register = async (email: string, password: string, full_name: string) => {
    await setSession(await api("/auth/register", { method: "POST", json: { email, password, full_name } }));
    await loadMe();
  };
  const logout = async () => {
    await clearSession();
    qc.clear();
    setUser(null);
  };

  return <Ctx.Provider value={{ user, loading, login, register, logout, setUser }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth outside provider");
  return c;
}
