"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";
import { updateMe } from "@/lib/api/auth";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sun, Moon, Monitor, AlertTriangle, Check, Coffee, Heart } from "lucide-react";
import { cn } from "@/lib/utils";

const CURRENCIES = ["EUR", "USD", "GBP", "CHF", "JPY", "CAD", "AUD", "SEK", "NOK", "DKK"];

const PERIODS = [
  { value: "1W", label: "1 Week" },
  { value: "1M", label: "1 Month" },
  { value: "3M", label: "3 Months" },
  { value: "6M", label: "6 Months" },
  { value: "1Y", label: "1 Year" },
  { value: "ALL", label: "All Time" },
];

const ALLOCATION_GROUPS = [
  { value: "sector", label: "Sector" },
  { value: "country", label: "Country" },
  { value: "asset_type", label: "Asset Type" },
];

const BROKERS = [
  { value: "degiro", label: "DeGiro" },
  { value: "trade_republic", label: "Trade Republic" },
  { value: "interactive_brokers", label: "Interactive Brokers" },
  { value: "bitpanda", label: "Bitpanda" },
];

function useLocalStorage(key: string, defaultValue: string) {
  const [value, setValue] = useState(defaultValue);

  useEffect(() => {
    const stored = localStorage.getItem(key);
    if (stored !== null) setValue(stored);
  }, [key]);

  const set = useCallback(
    (newValue: string) => {
      setValue(newValue);
      localStorage.setItem(key, newValue);
    },
    [key]
  );

  return [value, set] as const;
}

function useLocalStorageBool(key: string, defaultValue: boolean) {
  const [value, setValue] = useState(defaultValue);

  useEffect(() => {
    const stored = localStorage.getItem(key);
    if (stored !== null) setValue(stored === "true");
  }, [key]);

  const set = useCallback(
    (newValue: boolean) => {
      setValue(newValue);
      localStorage.setItem(key, String(newValue));
    },
    [key]
  );

  return [value, set] as const;
}

function ToggleButton({
  pressed,
  onToggle,
  id,
  label,
}: {
  pressed: boolean;
  onToggle: (v: boolean) => void;
  id: string;
  label: string;
}) {
  return (
    <button
      id={id}
      role="switch"
      aria-checked={pressed}
      aria-label={label}
      onClick={() => onToggle(!pressed)}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        pressed ? "bg-primary" : "bg-input"
      )}
    >
      <span
        className={cn(
          "pointer-events-none block size-5 rounded-full bg-background shadow-lg ring-0 transition-transform",
          pressed ? "translate-x-5" : "translate-x-0"
        )}
      />
    </button>
  );
}

function SuccessMessage({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700 dark:bg-green-950 dark:text-green-300">
      <Check className="size-4" />
      {message}
    </div>
  );
}

export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const { theme, setTheme } = useTheme();

  // Server-side preferences
  const [currency, setCurrency] = useState(user?.base_currency ?? "EUR");
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Local display settings
  const [defaultPeriod, setDefaultPeriod] = useLocalStorage("default_period", "1Y");
  const [allocationGroup, setAllocationGroup] = useLocalStorage("default_allocation_group", "sector");
  const [showFees, setShowFees] = useLocalStorageBool("show_fees", true);
  const [compactTables, setCompactTables] = useLocalStorageBool("compact_tables", false);
  const [defaultBroker, setDefaultBroker] = useLocalStorage("default_broker", "degiro");

  // Delete confirmation
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Sync currency if user changes
  const prevBaseCurrency = useRef(user?.base_currency);
  useEffect(() => {
    if (user?.base_currency && user.base_currency !== prevBaseCurrency.current) {
      prevBaseCurrency.current = user.base_currency;
      setCurrency(user.base_currency);
    }
  }, [user?.base_currency]);

  const handleSavePreferences = async () => {
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      await updateMe({ base_currency: currency });
      await refreshUser();
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch {
      setSaveError("Failed to save preferences. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const themeOptions = [
    { value: "light" as const, label: "Light", icon: Sun },
    { value: "dark" as const, label: "Dark", icon: Moon },
    { value: "system" as const, label: "System", icon: Monitor },
  ];

  return (
    <div className="mx-auto max-w-2xl p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your account preferences and display settings.
        </p>
      </div>

      {/* Profile Section */}
      <section aria-labelledby="profile-heading">
        <Card>
          <CardHeader>
            <CardTitle id="profile-heading">Profile</CardTitle>
            <CardDescription>Your account information.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                value={user?.username ?? ""}
                readOnly
                disabled
                className="max-w-sm"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                value={user?.email ?? ""}
                readOnly
                disabled
                className="max-w-sm"
              />
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Preferences Section */}
      <section aria-labelledby="preferences-heading">
        <Card>
          <CardHeader>
            <CardTitle id="preferences-heading">Preferences</CardTitle>
            <CardDescription>
              Configure your base currency and appearance.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="currency">Base Currency</Label>
              <Select value={currency} onValueChange={(v) => v && setCurrency(v)}>
                <SelectTrigger id="currency" className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CURRENCIES.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                All portfolio values will be converted to this currency.
              </p>
            </div>

            <Separator />

            <div className="space-y-3">
              <Label>Theme</Label>
              <div className="flex gap-2">
                {themeOptions.map((opt) => {
                  const Icon = opt.icon;
                  const isActive = theme === opt.value;
                  return (
                    <Button
                      key={opt.value}
                      variant={isActive ? "default" : "outline"}
                      size="sm"
                      onClick={() => setTheme(opt.value)}
                      className="gap-2"
                      aria-pressed={isActive}
                    >
                      <Icon className="size-4" />
                      {opt.label}
                    </Button>
                  );
                })}
              </div>
            </div>

            <Separator />

            {saveSuccess && <SuccessMessage message="Preferences saved successfully." />}
            {saveError && (
              <p className="text-sm text-destructive">{saveError}</p>
            )}

            <Button onClick={handleSavePreferences} disabled={saving}>
              {saving ? "Saving..." : "Save Preferences"}
            </Button>
          </CardContent>
        </Card>
      </section>

      {/* Display Settings Section */}
      <section aria-labelledby="display-heading">
        <Card>
          <CardHeader>
            <CardTitle id="display-heading">Display Settings</CardTitle>
            <CardDescription>
              Customize how data is displayed. These settings are stored locally.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="default-period">Default Performance Period</Label>
              <Select value={defaultPeriod} onValueChange={(v) => v && setDefaultPeriod(v)}>
                <SelectTrigger id="default-period" className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PERIODS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="allocation-group">Default Allocation Grouping</Label>
              <Select value={allocationGroup} onValueChange={(v) => v && setAllocationGroup(v)}>
                <SelectTrigger id="allocation-group" className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ALLOCATION_GROUPS.map((g) => (
                    <SelectItem key={g.value} value={g.value}>
                      {g.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Separator />

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="show-fees">Show Fees in Transactions</Label>
                <p className="text-xs text-muted-foreground">
                  Display the fee column in the transaction table.
                </p>
              </div>
              <ToggleButton
                id="show-fees"
                pressed={showFees}
                onToggle={setShowFees}
                label="Show fees in transaction table"
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="compact-tables">Compact Tables</Label>
                <p className="text-xs text-muted-foreground">
                  Use smaller row heights for denser data display.
                </p>
              </div>
              <ToggleButton
                id="compact-tables"
                pressed={compactTables}
                onToggle={setCompactTables}
                label="Enable compact table mode"
              />
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Import Settings Section */}
      <section aria-labelledby="import-heading">
        <Card>
          <CardHeader>
            <CardTitle id="import-heading">Import Settings</CardTitle>
            <CardDescription>
              Default settings for CSV transaction imports.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="default-broker">Default Broker</Label>
              <Select value={defaultBroker} onValueChange={(v) => v && setDefaultBroker(v)}>
                <SelectTrigger id="default-broker" className="w-[240px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {BROKERS.map((b) => (
                    <SelectItem key={b.value} value={b.value}>
                      {b.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                This broker will be pre-selected when importing transactions.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Support Section */}
      <section aria-labelledby="support-heading">
        <Card className="border-amber-200 dark:border-amber-800 bg-gradient-to-br from-amber-50/50 to-orange-50/50 dark:from-amber-950/30 dark:to-orange-950/30">
          <CardHeader>
            <CardTitle id="support-heading" className="flex items-center gap-2">
              <Coffee className="size-5 text-amber-600 dark:text-amber-400" />
              Buy Me a Coffee
            </CardTitle>
            <CardDescription>
              If Stonkfolio helps you track your investments, consider supporting
              its development.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Stonkfolio is built and maintained with{" "}
              <Heart className="inline size-3.5 text-red-500 fill-red-500" />{" "}
              as an open-source project. Your support helps cover hosting costs
              and keeps development going.
            </p>
            <div className="flex flex-wrap gap-3">
              <a
                href="https://buymeacoffee.com/stonkfolio"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button variant="outline" className="gap-2 border-amber-300 hover:bg-amber-100 dark:border-amber-700 dark:hover:bg-amber-900">
                  <Coffee className="size-4 text-amber-600 dark:text-amber-400" />
                  Buy me a coffee
                </Button>
              </a>
              <a
                href="https://github.com/sponsors/stonkfolio"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button variant="outline" className="gap-2">
                  <Heart className="size-4 text-pink-500" />
                  Sponsor on GitHub
                </Button>
              </a>
            </div>
            <p className="text-xs text-muted-foreground">
              Thank you for your generosity! Every contribution makes a difference.
            </p>
          </CardContent>
        </Card>
      </section>

      {/* Danger Zone Section */}
      <section aria-labelledby="danger-heading">
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle id="danger-heading" className="text-destructive">
              Danger Zone
            </CardTitle>
            <CardDescription>
              Irreversible actions that affect your account.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {showDeleteConfirm ? (
              <div className="rounded-md border border-destructive/50 bg-destructive/5 p-4 space-y-3">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="size-5 text-destructive mt-0.5" />
                  <div className="space-y-1">
                    <p className="text-sm font-medium">
                      Are you sure you want to delete your account?
                    </p>
                    <p className="text-xs text-muted-foreground">
                      This action is permanent and cannot be undone. All your portfolios,
                      transactions, and settings will be permanently deleted.
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => {
                      alert("Account deletion is not yet available. Please contact support.");
                      setShowDeleteConfirm(false);
                    }}
                  >
                    Yes, Delete My Account
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowDeleteConfirm(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-sm font-medium">Delete Account</p>
                  <p className="text-xs text-muted-foreground">
                    Permanently delete your account and all associated data.
                  </p>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setShowDeleteConfirm(true)}
                >
                  Delete Account
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
