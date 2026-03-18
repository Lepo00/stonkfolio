"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Plus, TrendingUp, TrendingDown, Package } from "lucide-react";
import { usePortfolio } from "@/lib/portfolio-context";
import { getHoldings, getSummary } from "@/lib/api/portfolios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CreatePortfolioDialog } from "@/components/portfolios/create-portfolio-dialog";

function SkeletonCard() {
  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-2">
        <div className="animate-pulse bg-muted rounded h-4 w-24" />
      </CardHeader>
      <CardContent>
        <div className="animate-pulse bg-muted rounded h-8 w-32" />
      </CardContent>
    </Card>
  );
}

function SkeletonTable() {
  return (
    <Card className="shadow-sm">
      <CardHeader>
        <div className="animate-pulse bg-muted rounded h-5 w-20" />
      </CardHeader>
      <CardContent className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="animate-pulse bg-muted rounded h-10 w-full" />
        ))}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const { selected } = usePortfolio();
  const [createOpen, setCreateOpen] = useState(false);

  const { data: summary, isLoading: summaryLoading, error: summaryError } = useQuery({
    queryKey: ["summary", selected?.id],
    queryFn: () => getSummary(selected!.id),
    enabled: !!selected,
  });

  const { data: holdingsData, isLoading: holdingsLoading, error: holdingsError } = useQuery({
    queryKey: ["holdings", selected?.id],
    queryFn: () => getHoldings(selected!.id),
    enabled: !!selected,
  });

  if (!selected) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground mt-1">Overview of your portfolio performance.</p>
        <p className="text-muted-foreground mt-4">
          Create a portfolio to get started.
        </p>
        <Button className="mt-4" onClick={() => setCreateOpen(true)}>
          <Plus className="size-4" data-icon="inline-start" />
          Create portfolio
        </Button>
        <CreatePortfolioDialog open={createOpen} onOpenChange={setCreateOpen} />
      </div>
    );
  }

  if (summaryError || holdingsError) {
    return (
      <div className="p-6">
        <p className="text-destructive">Failed to load portfolio data. Please try again.</p>
      </div>
    );
  }

  if (summaryLoading || holdingsLoading) {
    return (
      <div className="p-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground mt-1">Overview of your portfolio performance.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <SkeletonTable />
      </div>
    );
  }

  const holdings = holdingsData?.results ?? [];
  const gainLoss = parseFloat(summary?.total_gain_loss ?? "0");
  const returnPct = parseFloat(summary?.total_return_pct ?? "0");
  const isGainPositive = gainLoss >= 0;
  const isReturnPositive = returnPct >= 0;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground mt-1">Overview of your portfolio performance.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Value
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              €{parseFloat(summary?.total_value ?? "0").toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Cost
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              €{parseFloat(summary?.total_cost ?? "0").toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Gain / Loss
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-1.5">
              {isGainPositive ? (
                <TrendingUp className="size-5 text-green-600 dark:text-green-400 shrink-0" />
              ) : (
                <TrendingDown className="size-5 text-red-600 dark:text-red-400 shrink-0" />
              )}
              <p
                className={`text-2xl font-bold ${
                  isGainPositive ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                }`}
              >
                {isGainPositive ? "+" : ""}€{gainLoss.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Return %
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-1.5">
              {isReturnPositive ? (
                <TrendingUp className="size-5 text-green-600 dark:text-green-400 shrink-0" />
              ) : (
                <TrendingDown className="size-5 text-red-600 dark:text-red-400 shrink-0" />
              )}
              <p
                className={`text-2xl font-bold ${
                  isReturnPositive ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                }`}
              >
                {isReturnPositive ? "+" : ""}
                {returnPct.toFixed(2)}%
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Holdings</CardTitle>
        </CardHeader>
        <CardContent>
          {holdings.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3">
              <Package className="size-10 opacity-40" />
              <p className="text-sm">No holdings yet</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Ticker</TableHead>
                  <TableHead className="text-right">Quantity</TableHead>
                  <TableHead className="text-right">Avg Buy Price</TableHead>
                  <TableHead className="text-right">Cost Basis</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {holdings.map((h) => {
                  const qty = parseFloat(h.quantity);
                  const avgPrice = parseFloat(h.avg_buy_price);
                  const costBasis = qty * avgPrice;
                  return (
                    <TableRow
                      key={h.id}
                      className="cursor-pointer hover:bg-muted/50"
                      role="link"
                      tabIndex={0}
                      onClick={() => router.push(`/instrument/${h.instrument.id}`)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          router.push(`/instrument/${h.instrument.id}`);
                        }
                      }}
                    >
                      <TableCell className="font-medium">
                        {h.instrument.name}
                      </TableCell>
                      <TableCell>{h.instrument.ticker ?? "-"}</TableCell>
                      <TableCell className="text-right">
                        {qty.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 4,
                        })}
                      </TableCell>
                      <TableCell className="text-right">
                        {avgPrice.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </TableCell>
                      <TableCell className="text-right">
                        {costBasis.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
