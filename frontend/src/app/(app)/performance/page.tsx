"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { usePortfolio } from "@/lib/portfolio-context";
import { getPerformance } from "@/lib/api/portfolios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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

export default function PerformancePage() {
  const { selected } = usePortfolio();
  const [period, setPeriod] = useState<string>("1Y");

  const { data, isLoading, error } = useQuery({
    queryKey: ["performance", selected?.id, period],
    queryFn: () => getPerformance(selected!.id, period),
    enabled: !!selected,
  });

  if (!selected) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Performance</h1>
        <p className="text-muted-foreground mt-4">
          Create a portfolio to get started
        </p>
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
    data?.series.map((p) => ({
      date: p.date,
      value: parseFloat(p.value),
    })) ?? [];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Performance</h1>

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

      <Card>
        <CardHeader>
          <CardTitle>Portfolio Value Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : series.length === 0 ? (
            <p className="text-muted-foreground">
              No performance data available
            </p>
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
                  tickFormatter={(v: number) => v.toLocaleString()}
                />
                <Tooltip
                  formatter={(value) => [
                    Number(value).toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    }),
                    "Value",
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
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
