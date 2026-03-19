"use client";

import { useQuery } from "@tanstack/react-query";
import { usePortfolio } from "@/lib/portfolio-context";
import { getCorrelation } from "@/lib/api/portfolios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Grid3X3 } from "lucide-react";

function correlationColor(value: number): string {
  if (value >= 0.99) return "bg-muted";
  if (value >= 0.7) return "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300";
  if (value >= 0.3) return "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300";
  if (value >= -0.3) return "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300";
  return "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300";
}

function computeAverageCorrelation(matrix: number[][]): number | null {
  if (matrix.length < 2) return null;
  let sum = 0;
  let count = 0;
  for (let i = 0; i < matrix.length; i++) {
    for (let j = i + 1; j < matrix.length; j++) {
      sum += matrix[i][j];
      count++;
    }
  }
  return count > 0 ? sum / count : null;
}

function CorrelationHeatmap({ portfolioId }: { portfolioId: number }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["correlation", portfolioId],
    queryFn: () => getCorrelation(portfolioId),
    staleTime: 24 * 60 * 60 * 1000,
  });

  if (error) {
    return <p className="text-destructive">Failed to load correlation data. Please try again.</p>;
  }

  if (isLoading) {
    return <div className="h-[400px] w-full animate-pulse rounded bg-muted" />;
  }

  if (!data || data.tickers.length < 2) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground">
        <Grid3X3 className="size-12 mb-3 opacity-30" />
        <p>Need at least 2 holdings with price data for a correlation matrix</p>
      </div>
    );
  }

  const avgCorrelation = computeAverageCorrelation(data.matrix);

  return (
    <div className="space-y-6">
      {/* Summary metric */}
      {avgCorrelation !== null && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">Average pairwise correlation:</span>
          <span className={`text-lg font-semibold ${
            avgCorrelation >= 0.7 ? "text-red-600 dark:text-red-400" :
            avgCorrelation >= 0.3 ? "text-amber-600 dark:text-amber-400" :
            avgCorrelation >= -0.3 ? "text-green-600 dark:text-green-400" :
            "text-blue-600 dark:text-blue-400"
          }`}>
            {avgCorrelation.toFixed(2)}
          </span>
          <span className="text-xs text-muted-foreground">
            {avgCorrelation >= 0.7 ? "(high — low diversification)" :
             avgCorrelation >= 0.3 ? "(moderate)" :
             avgCorrelation >= -0.3 ? "(low — good diversification)" :
             "(negative — excellent diversification)"}
          </span>
        </div>
      )}

      {/* Heatmap table */}
      <div className="overflow-x-auto">
        <table className="border-collapse">
          <thead>
            <tr>
              <th className="p-2" />
              {data.tickers.map((ticker) => (
                <th
                  key={ticker}
                  className="p-2 text-xs font-medium text-muted-foreground whitespace-nowrap"
                  title={data.names[data.tickers.indexOf(ticker)]}
                >
                  {ticker}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.tickers.map((rowTicker, i) => (
              <tr key={rowTicker}>
                <td
                  className="p-2 text-xs font-medium text-muted-foreground whitespace-nowrap text-right"
                  title={data.names[i]}
                >
                  {rowTicker}
                </td>
                {data.matrix[i].map((value, j) => (
                  <td
                    key={`${i}-${j}`}
                    className={`p-2 text-center text-sm font-mono min-w-[60px] rounded-sm ${correlationColor(value)}`}
                    title={`${rowTicker} / ${data.tickers[j]}: ${value.toFixed(4)}`}
                  >
                    {value.toFixed(2)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
        <span className="font-medium">Legend:</span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block size-3 rounded-sm bg-red-100 dark:bg-red-900/30 border border-red-200 dark:border-red-800" />
          High (&ge; 0.7)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block size-3 rounded-sm bg-amber-100 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800" />
          Moderate (0.3 to 0.7)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block size-3 rounded-sm bg-green-100 dark:bg-green-900/30 border border-green-200 dark:border-green-800" />
          Low (&minus;0.3 to 0.3)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block size-3 rounded-sm bg-blue-100 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800" />
          Negative (&lt; &minus;0.3)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block size-3 rounded-sm bg-muted border border-border" />
          Diagonal (1.00)
        </span>
      </div>
    </div>
  );
}

export default function CorrelationPage() {
  const { selected } = usePortfolio();

  if (!selected) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Correlation</h1>
        <p className="text-muted-foreground mt-1">See how your holdings move in relation to each other.</p>
        <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground mt-6">
          <Grid3X3 className="size-12 mb-3 opacity-30" />
          <p>No correlation data yet</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Correlation</h1>
      <p className="text-muted-foreground mt-1">See how your holdings move in relation to each other.</p>

      <Card>
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Correlation Heatmap</CardTitle>
        </CardHeader>
        <CardContent>
          <CorrelationHeatmap portfolioId={selected.id} />
        </CardContent>
      </Card>
    </div>
  );
}
