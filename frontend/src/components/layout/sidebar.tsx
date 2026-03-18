"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  TrendingUp,
  PieChart,
  ArrowLeftRight,
  Upload,
  Settings,
  LogOut,
  Sun,
  Moon,
  Monitor,
  Plus,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";
import { usePortfolio } from "@/lib/portfolio-context";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { CreatePortfolioDialog } from "@/components/portfolios/create-portfolio-dialog";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/performance", label: "Performance", icon: TrendingUp },
  { href: "/allocation", label: "Allocation", icon: PieChart },
  { href: "/transactions", label: "Transactions", icon: ArrowLeftRight },
  { href: "/import", label: "Import", icon: Upload },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { portfolios, selected, setSelected } = usePortfolio();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [createOpen, setCreateOpen] = useState(false);

  const cycleTheme = () => {
    const next = theme === "light" ? "dark" : theme === "dark" ? "system" : "light";
    setTheme(next);
  };

  const ThemeIcon = theme === "system" ? Monitor : resolvedTheme === "dark" ? Moon : Sun;
  const themeLabel = theme === "system" ? "System theme" : theme === "dark" ? "Dark theme" : "Light theme";

  return (
    <aside className="flex h-screen w-64 flex-col border-r bg-background">
      {/* App name */}
      <div className="flex h-14 items-center justify-between px-4">
        <h1 className="text-lg font-semibold tracking-tight">Stonkfolio</h1>
        <Button
          variant="ghost"
          size="icon"
          onClick={cycleTheme}
          className="size-8 text-muted-foreground hover:text-foreground"
          aria-label={themeLabel}
        >
          <ThemeIcon className="size-4" />
        </Button>
      </div>

      <Separator />

      {/* Portfolio selector */}
      <div className="px-4 py-3">
        <div className="mb-1.5 flex items-center justify-between">
          <label className="text-xs font-medium text-muted-foreground">
            Portfolio
          </label>
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => setCreateOpen(true)}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Create portfolio"
          >
            <Plus className="size-3.5" />
          </Button>
        </div>
        <Select
          value={selected?.id?.toString() ?? ""}
          onValueChange={(val) => {
            const p = portfolios.find((p) => p.id.toString() === val);
            if (p) setSelected(p);
          }}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select portfolio" />
          </SelectTrigger>
          <SelectContent>
            {portfolios.map((p) => (
              <SelectItem key={p.id} value={p.id.toString()}>
                {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Separator />

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-3">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )}
            >
              <Icon className="size-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <Separator />

      {/* User menu */}
      <div className="flex items-center gap-3 px-4 py-3">
        <Avatar size="sm">
          <AvatarFallback>
            {user?.username?.charAt(0).toUpperCase() ?? "?"}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 truncate text-sm font-medium">
          {user?.username}
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={logout}
          className="size-8 text-muted-foreground hover:text-foreground"
        >
          <LogOut className="size-4" />
          <span className="sr-only">Logout</span>
        </Button>
      </div>

      <CreatePortfolioDialog open={createOpen} onOpenChange={setCreateOpen} />
    </aside>
  );
}
