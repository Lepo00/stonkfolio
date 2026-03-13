"use client";

import { createContext, useContext, useState, useMemo, useCallback, ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { listPortfolios } from "./api/portfolios";
import type { Portfolio } from "@/types/api";

interface PortfolioContextType {
  portfolios: Portfolio[];
  selected: Portfolio | null;
  setSelected: (p: Portfolio) => void;
}

const PortfolioContext = createContext<PortfolioContextType | null>(null);

export function PortfolioProvider({ children }: { children: ReactNode }) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { data } = useQuery({
    queryKey: ["portfolios"],
    queryFn: listPortfolios,
  });

  const portfolios = useMemo(() => data?.results ?? [], [data?.results]);

  const selected = useMemo(() => {
    if (selectedId !== null) {
      const found = portfolios.find((p) => p.id === selectedId);
      if (found) return found;
    }
    return portfolios.length > 0 ? portfolios[0] : null;
  }, [portfolios, selectedId]);

  const setSelected = useCallback((p: Portfolio) => {
    setSelectedId(p.id);
  }, []);

  return (
    <PortfolioContext.Provider value={{ portfolios, selected, setSelected }}>
      {children}
    </PortfolioContext.Provider>
  );
}

export function usePortfolio() {
  const ctx = useContext(PortfolioContext);
  if (!ctx) throw new Error("usePortfolio must be used within PortfolioProvider");
  return ctx;
}
