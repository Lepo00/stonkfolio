"use client";

import { useQuery } from "@tanstack/react-query";
import { Coins } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { usePortfolio } from "@/lib/portfolio-context";
import { getDividends } from "@/lib/api/portfolios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function DividendsPage() {
  const { selected } = usePortfolio();

  const { data, isLoading, error } = useQuery({
    queryKey: ["dividends", selected?.id],
    queryFn: () => getDividends(selected!.id),
    enabled: !!selected,
  });

  if (!selected) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Dividends</h1>
        <p className="text-muted-foreground mt-1">Dividend income analytics.</p>
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <Coins className="size-12 mb-3 opacity-30" />
          <p>Select a portfolio to view dividend data.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-destructive">Failed to load dividend data. Please try again.</p>
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="p-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Dividends</h1>
          <p className="text-muted-foreground mt-1">Dividend income analytics.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="shadow-sm rounded-xl">
              <CardContent className="pt-6">
                <div className="animate-pulse bg-muted rounded h-16 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Card className="shadow-sm rounded-xl">
          <CardContent className="pt-6">
            <div className="animate-pulse bg-muted rounded h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  const { summary, monthly_history, by_instrument, recent_payments } = data;

  // Reverse monthly history for chart (oldest first, left-to-right)
  const chartData = [...monthly_history].reverse().map((m) => ({
    month: m.month,
    amount: parseFloat(m.amount),
  }));

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dividends</h1>
        <p className="text-muted-foreground mt-1">Dividend income analytics.</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="shadow-sm rounded-xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Income (12M)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              &euro;{parseFloat(summary.total_dividends_12m).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm rounded-xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Trailing Yield
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {summary.trailing_yield_pct}%
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm rounded-xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Monthly Average
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              &euro;{parseFloat(summary.monthly_average_12m).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm rounded-xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Dividend Holdings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {summary.dividend_holding_count}
              <span className="text-sm font-normal text-muted-foreground ml-1">
                / {summary.total_holding_count}
              </span>
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Monthly Income Bar Chart */}
      <Card className="shadow-sm rounded-xl">
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            Monthly Income (24 Months)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {chartData.every((d) => d.amount === 0) ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3">
              <Coins className="size-10 opacity-40" />
              <p className="text-sm">No dividend income recorded yet</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="month"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: string) => {
                    const [y, m] = v.split("-");
                    return `${m}/${y.slice(2)}`;
                  }}
                  interval="preserveStartEnd"
                />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(value) => [
                    `\u20AC${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                    "Income",
                  ]}
                  labelFormatter={(label) => {
                    const [y, m] = String(label).split("-");
                    return `${m}/${y}`;
                  }}
                />
                <Bar dataKey="amount" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Income by Instrument */}
      <Card className="shadow-sm rounded-xl">
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            Income by Instrument (12M)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {by_instrument.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3">
              <Coins className="size-10 opacity-40" />
              <p className="text-sm">No dividend-paying instruments</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Instrument</TableHead>
                  <TableHead>Ticker</TableHead>
                  <TableHead className="text-right">Total (12M)</TableHead>
                  <TableHead className="text-right">% of Total</TableHead>
                  <TableHead className="text-right">Payments</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {by_instrument.map((row) => (
                  <TableRow key={row.ticker}>
                    <TableCell className="font-medium">{row.instrument_name}</TableCell>
                    <TableCell>{row.ticker || "-"}</TableCell>
                    <TableCell className="text-right">
                      &euro;{parseFloat(row.total_12m).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </TableCell>
                    <TableCell className="text-right">{row.pct_of_total}%</TableCell>
                    <TableCell className="text-right">{row.payment_count_12m}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Recent Payments */}
      <Card className="shadow-sm rounded-xl">
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            Recent Payments
          </CardTitle>
        </CardHeader>
        <CardContent>
          {recent_payments.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3">
              <Coins className="size-10 opacity-40" />
              <p className="text-sm">No dividend payments yet</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Instrument</TableHead>
                  <TableHead>Ticker</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recent_payments.map((payment, idx) => (
                  <TableRow key={`${payment.date}-${payment.ticker}-${idx}`}>
                    <TableCell>{payment.date}</TableCell>
                    <TableCell className="font-medium">{payment.instrument_name}</TableCell>
                    <TableCell>{payment.ticker || "-"}</TableCell>
                    <TableCell className="text-right">
                      &euro;{parseFloat(payment.amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
