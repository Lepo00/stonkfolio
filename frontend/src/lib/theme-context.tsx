"use client";

import { createContext, useContext, useEffect, useMemo, useSyncExternalStore, ReactNode } from "react";

type Theme = "light" | "dark" | "system";

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  resolvedTheme: "light" | "dark";
}

const ThemeContext = createContext<ThemeContextType | null>(null);

function getStoredTheme(): Theme {
  if (typeof window === "undefined") return "system";
  return (localStorage.getItem("theme") as Theme) ?? "system";
}

function subscribeToStorage(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

function getPrefersDark(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function subscribeToColorScheme(callback: () => void) {
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  mq.addEventListener("change", callback);
  return () => mq.removeEventListener("change", callback);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const storedTheme = useSyncExternalStore(subscribeToStorage, getStoredTheme, () => "system" as Theme);
  const prefersDark = useSyncExternalStore(subscribeToColorScheme, getPrefersDark, () => false);

  const resolvedTheme = useMemo<"light" | "dark">(() => {
    if (storedTheme === "system") {
      return prefersDark ? "dark" : "light";
    }
    return storedTheme;
  }, [storedTheme, prefersDark]);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(resolvedTheme);
  }, [resolvedTheme]);

  const setTheme = (t: Theme) => {
    localStorage.setItem("theme", t);
    window.dispatchEvent(new Event("storage"));
  };

  return (
    <ThemeContext.Provider value={{ theme: storedTheme, setTheme, resolvedTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
