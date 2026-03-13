"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import type { User } from "@/types/api";
import { getMe, logout as apiLogout } from "./api/auth";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  refreshUser: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const u = await getMe();
      setUser(u);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    apiLogout();
    setUser(null);
  };

  useEffect(() => { refreshUser(); }, []);

  return (
    <AuthContext.Provider value={{ user, loading, refreshUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
