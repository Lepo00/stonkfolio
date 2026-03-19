"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { usePortfolio } from "@/lib/portfolio-context";
import { getRebalance } from "@/lib/api/portfolios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Scale } from "lucide-react";
import type { RebalanceHolding } from "@/types/api";

const STRATEGIES = [
  { value: "equal_weight", label: "Equal Weight" },
] as const;

function DriftBar({ current, target }: { current: number; target: number }) {
  const max = Math.max(current, target, 1);
  const currentPct = (current / max) * 100;
  const targetPct = (target / max) * 100;

  return (
    <div className="flex flex-col gap-1 w-full min-w-[120px]">
      <div className="relative h-2 rounded-full bg-muted overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-primary/60"
          style={{ width: `${currentPct}%` }}
        />
      </div>
      <div className="relative h-2 rounded-full bg-muted overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-emerald-500/60"
          style={{ width: `${targetPct}%` }}
        />
      </div>
    </div>
  );
}

function ActionBadge({ action }: { action: RebalanceHolding["action"] }) {
  if (action === "SELL") {
    return (
      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
        SELL
      </span>
    );
  }
  if (action === "BUY") {
    return (
      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
        BUY
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-muted text-muted-foreground">
      HOLD
    </span>
  );
}

function DriftValue({ drift }: { drift: number }) {
  const color =
    drift > 2
      ? "text-red-600 dark:text-red-400"
      : drift < -2
        ? "text-emerald-600 dark:text-emerald-400"
        : "text-muted-foreground";

  return (
    <span className={`font-mono text-sm ${color}`}>
      {drift > 0 ? "+" : ""}
      {drift.toFixed(2)}%
    </span>
  );
}

function RebalanceContent({ portfolioId, strategy }: { portfolioId: number; strategy: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["rebalance", portfolioId, strategy],
    queryFn: () => getRebalance(portfolioId, strategy),
  });

  if (error) {
    return <p className="text-destructive">Failed to load rebalancing data. Please try again.</p>;
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-24 w-full animate-pulse rounded bg-muted" />
        <div className="h-64 w-full animate-pulse rounded bg-muted" />
      </div>
    );
  }

  if (!data || data.holdings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[300px] text-muted-foreground">
        <Scale className="size-12 mb-3 opacity-30" />
        <p>No holdings to rebalance</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            Rebalance Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Total Portfolio Value</p>
              <p className="text-xl font-semibold tabular-nums">
                {parseFloat(data.total_value).toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}{" "}
                EUR
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Max Drift</p>
              <p className="text-xl font-semibold tabular-nums">{data.max_drift.toFixed(2)}%</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Status</p>
              <div className="mt-1">
                {data.rebalance_needed ? (
                  <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border-0">
                    Rebalance Recommended
                  </Badge>
                ) : (
                  <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-0">
                    Balanced
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Holdings table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            Holdings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-muted-foreground">
                  <th className="pb-2 pr-4 font-medium">Name / Ticker</th>
                  <th className="pb-2 pr-4 font-medium text-right">Current %</th>
                  <th className="pb-2 pr-4 font-medium text-right">Target %</th>
                  <th className="pb-2 pr-4 font-medium min-w-[140px]">Current vs Target</th>
                  <th className="pb-2 pr-4 font-medium text-right">Drift</th>
                  <th className="pb-2 pr-4 font-medium text-center">Action</th>
                  <th className="pb-2 font-medium text-right">Amount (EUR)</th>
                </tr>
              </thead>
              <tbody>
                {data.holdings.map((h) => (
                  <tr key={h.ticker} className="border-b border-border/50 last:border-0">
                    <td className="py-3 pr-4">
                      <div className="font-medium">{h.name}</div>
                      <div className="text-xs text-muted-foreground">{h.ticker}</div>
                    </td>
                    <td className="py-3 pr-4 text-right tabular-nums">{h.current_weight.toFixed(2)}%</td>
                    <td className="py-3 pr-4 text-right tabular-nums">{h.target_weight.toFixed(2)}%</td>
                    <td className="py-3 pr-4">
                      <DriftBar current={h.current_weight} target={h.target_weight} />
                      <div className="flex justify-between text-[10px] text-muted-foreground mt-0.5">
                        <span>Current</span>
                        <span>Target</span>
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-right">
                      <DriftValue drift={h.drift} />
                    </td>
                    <td className="py-3 pr-4 text-center">
                      <ActionBadge action={h.action} />
                    </td>
                    <td className="py-3 text-right tabular-nums font-mono text-sm">
                      {h.action !== "HOLD"
                        ? parseFloat(h.amount_eur).toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })
                        : "\u2014"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function RebalancePage() {
  const { selected } = usePortfolio();
  const [strategy, setStrategy] = useState("equal_weight");

  if (!selected) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Rebalance</h1>
        <p className="text-muted-foreground mt-1">Analyze portfolio drift and plan rebalancing trades.</p>
        <div className="flex flex-col items-center justify-center h-[300px] text-muted-foreground mt-6">
          <Scale className="size-12 mb-3 opacity-30" />
          <p>Select a portfolio to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Rebalance</h1>
        <p className="text-muted-foreground mt-1">Analyze portfolio drift and plan rebalancing trades.</p>
      </div>

      {/* Strategy selector */}
      <div className="flex gap-2">
        {STRATEGIES.map((s) => (
          <Button
            key={s.value}
            variant={strategy === s.value ? "default" : "outline"}
            size="sm"
            onClick={() => setStrategy(s.value)}
          >
            {s.label}
          </Button>
        ))}
      </div>

      <RebalanceContent portfolioId={selected.id} strategy={strategy} />
    </div>
  );
}
