"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { PortfolioProvider } from "@/lib/portfolio-context";
import { Sidebar } from "./sidebar";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="size-8 animate-spin rounded-full border-4 border-muted border-t-foreground" />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <PortfolioProvider>
      <div className="flex h-screen bg-background text-foreground">
        <Sidebar />
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </PortfolioProvider>
  );
}
