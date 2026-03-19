"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { usePortfolio } from "@/lib/portfolio-context";
import { getPerformance } from "@/lib/api/portfolios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LineChart as LineChartIcon } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const PERIODS = ["1W", "1M", "3M", "6M", "1Y", "ALL"] as const;

const BENCHMARKS = [
  { value: "none", label: "No benchmark" },
  { value: "msci_world", label: "MSCI World" },
  { value: "sp500", label: "S&P 500" },
] as const;

export default function PerformancePage() {
  const { selected } = usePortfolio();
  const [period, setPeriod] = useState<string>("1Y");
  const [benchmark, setBenchmark] = useState<string>("none");

  const { data, isLoading, error } = useQuery({
    queryKey: ["performance", selected?.id, period, benchmark],
    queryFn: () =>
      getPerformance(
        selected!.id,
        period,
        benchmark !== "none" ? benchmark : undefined
      ),
    enabled: !!selected,
  });

  if (!selected) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Performance</h1>
        <p className="text-muted-foreground mt-1">Track your portfolio value over time.</p>
        <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground mt-6">
          <LineChartIcon className="size-12 mb-3 opacity-30" />
          <p>No performance data yet</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-destructive">Failed to load portfolio data. Please try again.</p>
      </div>
    );
  }

  const series =
    data?.series.map((p, i) => ({
      date: p.date,
      value: parseFloat(p.value),
      benchmark: data.benchmark_series?.[i]
        ? parseFloat(data.benchmark_series[i].value)
        : undefined,
    })) ?? [];

  const benchmarkName = data?.benchmark_name;

  // Calculate alpha when benchmark is active
  const alpha =
    series.length >= 2 && benchmarkName
      ? series[series.length - 1].value -
        series[0].value -
        ((series[series.length - 1].benchmark ?? series[0].value) -
          (series[0].benchmark ?? series[0].value))
      : null;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Performance</h1>
      <p className="text-muted-foreground mt-1">Track your portfolio value over time.</p>

      <div className="flex items-center gap-4">
        <div className="flex gap-2">
          {PERIODS.map((p) => (
            <Button
              key={p}
              variant={period === p ? "default" : "outline"}
              size="sm"
              onClick={() => setPeriod(p)}
            >
              {p}
            </Button>
          ))}
        </div>
        <Select value={benchmark} onValueChange={(v) => setBenchmark(v ?? "none")}>
          <SelectTrigger className="w-[180px] h-8 text-sm">
            <SelectValue placeholder="Benchmark" />
          </SelectTrigger>
          <SelectContent>
            {BENCHMARKS.map((b) => (
              <SelectItem key={b.value} value={b.value}>
                {b.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Portfolio Value Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="h-[400px] w-full animate-pulse rounded bg-muted" />
          ) : series.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground">
              <LineChartIcon className="size-12 mb-3 opacity-30" />
              <p>No performance data yet</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={series}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v: string) =>
                    new Date(v).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })
                  }
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v: number) =>
                    benchmarkName ? v.toFixed(0) : v.toLocaleString()
                  }
                />
                <Tooltip
                  formatter={(value, name) => [
                    Number(value).toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    }),
                    name === "benchmark" ? benchmarkName : "Portfolio",
                  ]}
                  labelFormatter={(label) =>
                    new Date(String(label)).toLocaleDateString()
                  }
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#2563eb"
                  strokeWidth={2}
                  dot={false}
                />
                {benchmarkName && (
                  <Line
                    type="monotone"
                    dataKey="benchmark"
                    stroke="#9ca3af"
                    strokeWidth={1.5}
                    strokeDasharray="6 3"
                    dot={false}
                    name={benchmarkName}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {benchmarkName && alpha !== null && (
        <Card>
          <CardHeader>
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Alpha vs {benchmarkName}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p
              className={`text-2xl font-bold ${
                alpha >= 0
                  ? "text-green-600 dark:text-green-400"
                  : "text-red-600 dark:text-red-400"
              }`}
            >
              {alpha >= 0 ? "+" : ""}
              {alpha.toFixed(2)} pts
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Portfolio return minus benchmark return (base-100 normalized)
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
