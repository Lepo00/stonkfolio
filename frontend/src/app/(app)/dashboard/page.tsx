"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, TrendingUp, TrendingDown, BarChart3, Sparkles } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { usePortfolio } from "@/lib/portfolio-context";
import { getSummary, getPerformance, getPortfolioAdvice } from "@/lib/api/portfolios";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CreatePortfolioDialog } from "@/components/portfolios/create-portfolio-dialog";

const PERIODS = ["1W", "1M", "3M", "6M", "1Y", "ALL"] as const;
type Period = (typeof PERIODS)[number];

function formatCurrency(value: number) {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatSinceDate(dateStr: string | null): string | null {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return null;
  return `Since ${d.toLocaleDateString(undefined, { month: "long", year: "numeric" })}`;
}

const labelClasses = "text-xs uppercase tracking-wider text-muted-foreground";

function colorClasses(positive: boolean) {
  return positive
    ? "text-green-600 dark:text-green-400"
    : "text-red-600 dark:text-red-400";
}

export default function DashboardPage() {
  const { selected } = usePortfolio();
  const [createOpen, setCreateOpen] = useState(false);
  const [period, setPeriod] = useState<Period>("1Y");

  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError,
  } = useQuery({
    queryKey: ["summary", selected?.id],
    queryFn: () => getSummary(selected!.id),
    enabled: !!selected,
  });

  const {
    data: perfData,
    isLoading: perfLoading,
    error: perfError,
  } = useQuery({
    queryKey: ["performance", selected?.id, period],
    queryFn: () => getPerformance(selected!.id, period),
    enabled: !!selected,
  });

  const { data: adviceData, isLoading: adviceLoading } = useQuery({
    queryKey: ["portfolio-advice", selected?.id],
    queryFn: () => getPortfolioAdvice(selected!.id),
    enabled: !!selected,
    staleTime: 5 * 60 * 1000, // cache for 5 minutes
  });

  // --- No portfolio state ---
  if (!selected) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Plus className="size-12 text-muted-foreground opacity-40" />
        <p className="text-muted-foreground">No portfolio yet.</p>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="size-4 mr-1" />
          Create portfolio
        </Button>
        <CreatePortfolioDialog open={createOpen} onOpenChange={setCreateOpen} />
      </div>
    );
  }

  // --- Loading state ---
  if (summaryLoading) {
    return (
      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="animate-pulse bg-muted rounded-xl h-40" />
          ))}
        </div>
      </div>
    );
  }

  // --- Summary error state ---
  if (summaryError) {
    return (
      <div className="p-6">
        <p className="text-destructive">
          Failed to load portfolio data. Please try again.
        </p>
      </div>
    );
  }

  // --- Derived values ---
  const totalValue = parseFloat(summary?.total_value ?? "0");
  const gainLoss = parseFloat(summary?.total_gain_loss ?? "0");
  const returnPct = parseFloat(summary?.total_return_pct ?? "0");
  const isPositive = gainLoss >= 0;

  const series = perfData?.series ?? [];
  const chartData = series.map((s) => ({
    date: s.date,
    value: parseFloat(s.value),
  }));

  const todayGL =
    series.length >= 2
      ? parseFloat(series[series.length - 1].value) -
        parseFloat(series[series.length - 2].value)
      : null;
  const todayPct =
    todayGL !== null && series.length >= 2
      ? (todayGL / parseFloat(series[series.length - 2].value)) * 100
      : null;
  const todayPositive = todayGL !== null ? todayGL >= 0 : true;

  const sinceLabel = formatSinceDate(summary?.first_transaction_date ?? null);

  return (
    <div className="p-6 h-full flex flex-col justify-center overflow-hidden">
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-4">
        {/* --- Hero: Total Value (top-left) --- */}
        <Card className="shadow-sm">
          <CardContent className="pt-6">
            <p className={labelClasses}>Total Value</p>
            <p className="text-4xl font-bold mt-1">
              &euro;{formatCurrency(totalValue)}
            </p>
            <div className={`flex items-center gap-1 mt-2 ${colorClasses(isPositive)}`}>
              {isPositive ? (
                <TrendingUp className="size-4 shrink-0" />
              ) : (
                <TrendingDown className="size-4 shrink-0" />
              )}
              <span className="text-sm font-medium">
                {isPositive ? "+" : ""}
                {returnPct.toFixed(2)}% all time
              </span>
            </div>
          </CardContent>
        </Card>

        {/* --- Today (top-right) --- */}
        <Card className="shadow-sm">
          <CardContent className="pt-6">
            <p className={labelClasses}>Today</p>
            {todayGL !== null ? (
              <>
                <div className={`flex items-center gap-1.5 mt-1 ${colorClasses(todayPositive)}`}>
                  {todayPositive ? (
                    <TrendingUp className="size-5 shrink-0" />
                  ) : (
                    <TrendingDown className="size-5 shrink-0" />
                  )}
                  <p className="text-2xl font-bold">
                    {todayPositive ? "+" : ""}&euro;{formatCurrency(Math.abs(todayGL))}
                  </p>
                </div>
                <p className={`text-sm font-medium mt-1 ${colorClasses(todayPositive)}`}>
                  {todayPositive ? "+" : ""}
                  {todayPct!.toFixed(2)}%
                </p>
              </>
            ) : (
              <p className="text-2xl font-bold mt-1 text-muted-foreground">
                --
              </p>
            )}
          </CardContent>
        </Card>

        {/* --- Performance chart (bottom-left) --- */}
        <Card className="shadow-sm">
          <CardContent className="pt-4 pb-3">
            {perfError ? (
              <div className="flex flex-col items-center justify-center h-[280px] text-muted-foreground gap-2">
                <BarChart3 className="size-10 opacity-40" />
                <p className="text-sm">Chart unavailable</p>
              </div>
            ) : perfLoading ? (
              <div className="animate-pulse bg-muted rounded-xl h-[280px]" />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="valueGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563eb" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="date"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 11 }}
                    minTickGap={40}
                  />
                  <YAxis
                    hide
                    domain={["auto", "auto"]}
                  />
                  <Tooltip
                    formatter={(v) => [`\u20AC${formatCurrency(Number(v))}`, "Value"]}
                    labelStyle={{ fontSize: 12 }}
                    contentStyle={{ borderRadius: 8, fontSize: 13, fontFamily: "inherit" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#2563eb"
                    strokeWidth={2}
                    fill="url(#valueGradient)"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
            {/* Period toggles */}
            <div className="flex gap-1 mt-2 justify-center">
              {PERIODS.map((p) => (
                <Button
                  key={p}
                  variant={period === p ? "default" : "ghost"}
                  size="sm"
                  className="h-7 px-2.5 text-xs rounded-full"
                  onClick={() => setPeriod(p)}
                >
                  {p}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* --- Overall Gain/Loss (bottom-right) --- */}
        <Card className="shadow-sm">
          <CardContent className="pt-6 flex flex-col justify-between h-full">
            <div>
              <p className={labelClasses}>Overall Gain/Loss</p>
              <div className={`flex items-center gap-1.5 mt-1 ${colorClasses(isPositive)}`}>
                {isPositive ? (
                  <TrendingUp className="size-5 shrink-0" />
                ) : (
                  <TrendingDown className="size-5 shrink-0" />
                )}
                <p className="text-2xl font-bold">
                  {isPositive ? "+" : ""}&euro;{formatCurrency(Math.abs(gainLoss))}
                </p>
              </div>
              <p className={`text-sm font-medium mt-1 ${colorClasses(isPositive)}`}>
                {isPositive ? "+" : ""}
                {returnPct.toFixed(2)}%
              </p>
            </div>
            {sinceLabel && (
              <p className="text-xs text-muted-foreground mt-4">
                {sinceLabel}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* AI Portfolio Advice */}
      <Card className="shadow-sm mt-4">
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="size-4 text-primary" />
            <p className={labelClasses}>Portfolio Insights</p>
          </div>
          {adviceLoading ? (
            <div className="space-y-2">
              <div className="animate-pulse bg-muted rounded h-4 w-full" />
              <div className="animate-pulse bg-muted rounded h-4 w-3/4" />
            </div>
          ) : adviceData?.advice ? (
            <ul className="space-y-2">
              {(Array.isArray(adviceData.advice)
                ? adviceData.advice
                : [adviceData.advice]
              ).map((tip, i) => (
                <li
                  key={i}
                  className="text-sm text-muted-foreground leading-relaxed"
                >
                  {tip.split(/\*\*(.*?)\*\*/g).map((part, j) =>
                    j % 2 === 1 ? (
                      <strong key={j} className="text-foreground">{part}</strong>
                    ) : (
                      part
                    )
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No advice available.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
