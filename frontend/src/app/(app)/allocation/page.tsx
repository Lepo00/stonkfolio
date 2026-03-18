"use client";

import { useQuery } from "@tanstack/react-query";
import { usePortfolio } from "@/lib/portfolio-context";
import { getAllocation } from "@/lib/api/portfolios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PieChart as PieChartIcon } from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  Legend,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const COLORS = [
  "#2563eb",
  "#16a34a",
  "#dc2626",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
  "#84cc16",
  "#f97316",
  "#6366f1",
];

const TABS = [
  { value: "sector", label: "Sector", groupBy: "sector" },
  { value: "country", label: "Country", groupBy: "country" },
  { value: "asset_type", label: "Asset Type", groupBy: "asset_type" },
] as const;

function AllocationChart({ portfolioId, groupBy }: { portfolioId: number; groupBy: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["allocation", portfolioId, groupBy],
    queryFn: () => getAllocation(portfolioId, groupBy),
  });

  if (error) {
    return <p className="text-destructive">Failed to load portfolio data. Please try again.</p>;
  }

  if (isLoading) {
    return <div className="h-[400px] w-full animate-pulse rounded bg-muted" />;
  }

  const items = data ?? [];

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground">
        <PieChartIcon className="size-12 mb-3 opacity-30" />
        <p>No allocation data yet</p>
      </div>
    );
  }

  const chartData = items.map((item) => ({
    name: item.group || "Unknown",
    value: parseFloat(item.value),
    percentage: parseFloat(item.percentage),
  }));

  return (
    <ResponsiveContainer width="100%" height={400}>
      <PieChart>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={140}
          label={({ name, percentage }: { name?: string; percentage?: number }) =>
            `${name ?? ""} (${(percentage ?? 0).toFixed(1)}%)`
          }
        >
          {chartData.map((_, index) => (
            <Cell key={index} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => [
            Number(value).toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            }),
            "Value",
          ]}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

export default function AllocationPage() {
  const { selected } = usePortfolio();

  if (!selected) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Allocation</h1>
        <p className="text-muted-foreground mt-1">See how your investments are distributed.</p>
        <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground mt-6">
          <PieChartIcon className="size-12 mb-3 opacity-30" />
          <p>No allocation data yet</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Allocation</h1>
      <p className="text-muted-foreground mt-1">See how your investments are distributed.</p>

      <Card>
        <CardHeader>
          <CardTitle>Portfolio Allocation</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="sector">
            <TabsList>
              {TABS.map((tab) => (
                <TabsTrigger key={tab.value} value={tab.value}>
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>
            {TABS.map((tab) => (
              <TabsContent key={tab.value} value={tab.value}>
                <AllocationChart
                  portfolioId={selected.id}
                  groupBy={tab.groupBy}
                />
              </TabsContent>
            ))}
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
