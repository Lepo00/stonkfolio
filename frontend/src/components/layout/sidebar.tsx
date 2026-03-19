"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Briefcase,
  Coins,
  TrendingUp,
  PieChart,
  Grid3X3,
  Scale,
  ArrowLeftRight,
  Upload,
  Sparkles,
  Settings,
  LogOut,
  Sun,
  Moon,
  Monitor,
  Plus,
  PanelLeftClose,
  PanelLeftOpen,
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
  { href: "/holdings", label: "Holdings", icon: Briefcase },
  { href: "/dividends", label: "Dividends", icon: Coins },
  { href: "/performance", label: "Performance", icon: TrendingUp },
  { href: "/allocation", label: "Allocation", icon: PieChart },
  { href: "/correlation", label: "Correlation", icon: Grid3X3 },
  { href: "/rebalance", label: "Rebalance", icon: Scale },
  { href: "/transactions", label: "Transactions", icon: ArrowLeftRight },
  { href: "/import", label: "Import", icon: Upload },
  { href: "/advice", label: "AI Advice", icon: Sparkles },
  { href: "/settings", label: "Settings", icon: Settings },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
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
    <aside
      className={cn(
        "flex h-screen flex-col border-r border-border/50 bg-sidebar transition-all duration-200",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* App name + collapse toggle */}
      <div className="flex h-14 items-center justify-between px-3">
        {!collapsed && (
          <h1 className="text-xl font-bold tracking-tight pl-1">Stonkfolio</h1>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className={cn(
            "size-8 text-muted-foreground hover:text-foreground",
            collapsed && "mx-auto"
          )}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeftOpen className="size-4" />
          ) : (
            <PanelLeftClose className="size-4" />
          )}
        </Button>
      </div>

      <Separator />

      {/* Portfolio selector */}
      {!collapsed ? (
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
      ) : (
        <div className="flex flex-col items-center gap-1 py-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCreateOpen(true)}
            className="size-8 text-muted-foreground hover:text-foreground"
            aria-label="Create portfolio"
          >
            <Plus className="size-4" />
          </Button>
        </div>
      )}

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
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center rounded-lg py-2 text-sm font-medium transition-colors",
                collapsed ? "justify-center px-2" : "gap-3 px-3",
                isActive
                  ? "rounded-lg bg-primary/10 text-primary font-semibold"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )}
            >
              <Icon className="size-5 shrink-0" />
              {!collapsed && item.label}
            </Link>
          );
        })}
      </nav>

      <Separator />

      {/* Bottom controls */}
      <div className={cn(
        "flex items-center gap-3 px-3 py-3",
        collapsed ? "flex-col" : "px-4"
      )}>
        {!collapsed ? (
          <>
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
              onClick={cycleTheme}
              className="size-8 text-muted-foreground hover:text-foreground"
              aria-label={themeLabel}
            >
              <ThemeIcon className="size-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={logout}
              className="size-8 text-muted-foreground hover:text-foreground"
            >
              <LogOut className="size-4" />
              <span className="sr-only">Logout</span>
            </Button>
          </>
        ) : (
          <>
            <Avatar size="sm">
              <AvatarFallback>
                {user?.username?.charAt(0).toUpperCase() ?? "?"}
              </AvatarFallback>
            </Avatar>
            <Button
              variant="ghost"
              size="icon"
              onClick={cycleTheme}
              className="size-8 text-muted-foreground hover:text-foreground"
              aria-label={themeLabel}
            >
              <ThemeIcon className="size-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={logout}
              className="size-8 text-muted-foreground hover:text-foreground"
              aria-label="Logout"
            >
              <LogOut className="size-4" />
            </Button>
          </>
        )}
      </div>

      <CreatePortfolioDialog open={createOpen} onOpenChange={setCreateOpen} />
    </aside>
  );
}
