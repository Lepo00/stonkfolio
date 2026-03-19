"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Plus, TrendingUp, TrendingDown, BarChart3, Sparkles,
  ShieldAlert, Layers, CircleDollarSign, Banknote, Brain, HeartPulse,
} from "lucide-react";
import type { AdviceItem } from "@/types/api";
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

const CATEGORY_ICONS: Record<AdviceItem["category"], React.ComponentType<{ className?: string }>> = {
  risk: ShieldAlert,
  performance: TrendingUp,
  diversification: Layers,
  cost: CircleDollarSign,
  income: Banknote,
  technical: BarChart3,
  behavioral: Brain,
  health: HeartPulse,
};

const PRIORITY_BORDER: Record<AdviceItem["priority"], string> = {
  critical: "border-l-red-500",
  warning: "border-l-amber-500",
  info: "border-l-blue-500",
  positive: "border-l-green-500",
};

const PRIORITY_ICON_COLOR: Record<AdviceItem["priority"], string> = {
  critical: "text-red-600 dark:text-red-400",
  warning: "text-amber-600 dark:text-amber-400",
  info: "text-blue-600 dark:text-blue-400",
  positive: "text-green-600 dark:text-green-400",
};

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
    staleTime: 5 * 60 * 1000,
    refetchInterval: (query) =>
      query.state.data?.has_pending_analysis ? 10_000 : false,
  });
  const [adviceExpanded, setAdviceExpanded] = useState(false);

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
  const twrPct = summary?.twr_return_pct ? parseFloat(summary.twr_return_pct) : null;
  const xirrPct = summary?.xirr_return_pct ? parseFloat(summary.xirr_return_pct) : null;

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
    <div className="p-4 h-full flex flex-col overflow-hidden gap-3">
      {/* Top row: Hero + Today */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-3 shrink-0">
        <Card className="shadow-sm">
          <CardContent className="py-3">
            <p className={labelClasses}>Total Value</p>
            <p className="text-3xl font-bold mt-0.5">
              &euro;{formatCurrency(totalValue)}
            </p>
            <div className={`flex items-center gap-1 mt-1 ${colorClasses(isPositive)}`}>
              {isPositive ? (
                <TrendingUp className="size-3.5 shrink-0" />
              ) : (
                <TrendingDown className="size-3.5 shrink-0" />
              )}
              <span className="text-xs font-medium">
                {isPositive ? "+" : ""}
                {returnPct.toFixed(2)}% all time
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardContent className="py-3">
            <p className={labelClasses}>Today</p>
            {todayGL !== null ? (
              <>
                <div className={`flex items-center gap-1.5 mt-0.5 ${colorClasses(todayPositive)}`}>
                  {todayPositive ? (
                    <TrendingUp className="size-4 shrink-0" />
                  ) : (
                    <TrendingDown className="size-4 shrink-0" />
                  )}
                  <p className="text-xl font-bold">
                    {todayPositive ? "+" : ""}&euro;{formatCurrency(Math.abs(todayGL))}
                  </p>
                </div>
                <p className={`text-xs font-medium mt-0.5 ${colorClasses(todayPositive)}`}>
                  {todayPositive ? "+" : ""}
                  {todayPct!.toFixed(2)}%
                </p>
              </>
            ) : (
              <p className="text-xl font-bold mt-0.5 text-muted-foreground">--</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Middle row: Chart + Overall G/L — fills remaining space */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-3 flex-1 min-h-0">
        <Card className="shadow-sm flex flex-col min-h-0">
          <CardContent className="pt-3 pb-2 flex-1 flex flex-col min-h-0">
            {perfError ? (
              <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground gap-2">
                <BarChart3 className="size-10 opacity-40" />
                <p className="text-sm">Chart unavailable</p>
              </div>
            ) : perfLoading ? (
              <div className="animate-pulse bg-muted rounded-xl flex-1" />
            ) : (
              <div className="flex-1 min-h-0">
                <ResponsiveContainer width="100%" height="100%">
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
                    <YAxis hide domain={["auto", "auto"]} />
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
              </div>
            )}
            <div className="flex gap-1 mt-1 justify-center shrink-0">
              {PERIODS.map((p) => (
                <Button
                  key={p}
                  variant={period === p ? "default" : "ghost"}
                  size="sm"
                  className="h-6 px-2 text-xs rounded-full"
                  onClick={() => setPeriod(p)}
                >
                  {p}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardContent className="py-3 flex flex-col justify-between h-full">
            <div>
              <p className={labelClasses}>Overall Gain/Loss</p>
              <div className={`flex items-center gap-1.5 mt-0.5 ${colorClasses(isPositive)}`}>
                {isPositive ? (
                  <TrendingUp className="size-4 shrink-0" />
                ) : (
                  <TrendingDown className="size-4 shrink-0" />
                )}
                <p className="text-xl font-bold">
                  {isPositive ? "+" : ""}&euro;{formatCurrency(Math.abs(gainLoss))}
                </p>
              </div>
              <p className={`text-xs font-medium mt-0.5 ${colorClasses(isPositive)}`}>
                {isPositive ? "+" : ""}
                {returnPct.toFixed(2)}%
              </p>
            </div>
            {sinceLabel && (
              <p className="text-xs text-muted-foreground mt-2">{sinceLabel}</p>
            )}
            {(twrPct !== null || xirrPct !== null) && (
              <div className="border-t pt-2 mt-2 space-y-1">
                {twrPct !== null && (
                  <div className="flex items-center justify-between">
                    <span className={labelClasses}>TWR (ann.)</span>
                    <span className={`text-xs font-medium ${colorClasses(twrPct >= 0)}`}>
                      {twrPct >= 0 ? "+" : ""}{twrPct.toFixed(2)}%
                    </span>
                  </div>
                )}
                {xirrPct !== null && (
                  <div className="flex items-center justify-between">
                    <span className={labelClasses}>XIRR (ann.)</span>
                    <span className={`text-xs font-medium ${colorClasses(xirrPct >= 0)}`}>
                      {xirrPct >= 0 ? "+" : ""}{xirrPct.toFixed(2)}%
                    </span>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Bottom: AI Portfolio Advice — compact, never grows */}
      <Card className="shadow-sm shrink-0">
        <CardContent className="py-3">
          <div className="flex items-center gap-2 mb-1.5">
            <Sparkles className="size-3.5 text-primary" />
            <p className={labelClasses}>Portfolio Insights</p>
            {adviceData?.has_pending_analysis && (
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary/75" />
                <span className="relative inline-flex size-2 rounded-full bg-primary" />
              </span>
            )}
          </div>
          {adviceLoading || (adviceData?.has_pending_analysis && !adviceData.items.length) ? (
            <div className="space-y-1.5">
              <div className="animate-pulse bg-muted rounded h-3 w-full" />
              <div className="animate-pulse bg-muted rounded h-3 w-3/4" />
            </div>
          ) : adviceData?.items.length ? (
            <>
              <div className="max-h-[120px] overflow-y-auto space-y-1">
                {(adviceExpanded ? adviceData.items : adviceData.items.slice(0, 3)).map((item) => {
                  const Icon = CATEGORY_ICONS[item.category];
                  return (
                    <div
                      key={item.rule_id}
                      className={`border-l-[3px] ${PRIORITY_BORDER[item.priority]} pl-2.5 py-0.5`}
                    >
                      <div className="flex items-center gap-1.5">
                        <Icon className={`size-3 shrink-0 ${PRIORITY_ICON_COLOR[item.priority]}`} />
                        <span className="text-xs font-medium leading-tight">{item.title}</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground leading-snug">
                        {item.message.split(/\*\*(.*?)\*\*/g).map((part, j) =>
                          j % 2 === 1 ? (
                            <strong key={j} className="text-foreground">{part}</strong>
                          ) : (
                            part
                          )
                        )}
                      </p>
                    </div>
                  );
                })}
              </div>
              {adviceData.items.length > 3 && (
                <button
                  onClick={() => setAdviceExpanded((v) => !v)}
                  className="text-[11px] text-primary hover:underline mt-1"
                >
                  {adviceExpanded ? "Show less" : `Show ${adviceData.items.length - 3} more`}
                </button>
              )}
              {adviceData.disclaimer && (
                <p className="text-[10px] text-muted-foreground/60 mt-2">{adviceData.disclaimer}</p>
              )}
            </>
          ) : (
            <p className="text-xs text-muted-foreground">No advice available.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
