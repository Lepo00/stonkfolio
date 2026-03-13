"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getInstrumentDetail, getInstrumentAnalysis } from "@/lib/api/instruments";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { InstrumentChart } from "@/components/charts/instrument-chart";

const recommendationColor: Record<string, string> = {
  BUY: "bg-green-600 hover:bg-green-600",
  HOLD: "bg-yellow-500 hover:bg-yellow-500",
  SELL: "bg-red-600 hover:bg-red-600",
};

const confidenceLabel: Record<string, string> = {
  low: "Low Confidence",
  medium: "Medium Confidence",
  high: "High Confidence",
};

export default function InstrumentDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const validId = !isNaN(id);

  const {
    data: instrument,
    isLoading: instrumentLoading,
    error: instrumentError,
  } = useQuery({
    queryKey: ["instrument", id],
    queryFn: () => getInstrumentDetail(id),
    enabled: validId,
  });

  const {
    data: analysis,
    isLoading: analysisLoading,
    error: analysisError,
  } = useQuery({
    queryKey: ["instrument-analysis", id],
    queryFn: () => getInstrumentAnalysis(id),
    enabled: validId,
  });

  if (!validId) {
    return (
      <div className="p-6">
        <p className="text-destructive">Invalid instrument ID.</p>
      </div>
    );
  }

  if (instrumentLoading) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Loading instrument details...</p>
      </div>
    );
  }

  if (instrumentError || !instrument) {
    return (
      <div className="p-6">
        <p className="text-red-600">Failed to load instrument details.</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{instrument.name}</h1>
        <p className="text-muted-foreground">
          {instrument.ticker ?? "N/A"} &middot; {instrument.isin}
        </p>
      </div>

      {/* Instrument Info & Price */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Ticker</span>
              <span className="font-medium">{instrument.ticker ?? "-"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">ISIN</span>
              <span className="font-medium">{instrument.isin}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Sector</span>
              <span className="font-medium">{instrument.sector ?? "-"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Country</span>
              <span className="font-medium">{instrument.country ?? "-"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Asset Type</span>
              <span className="font-medium">{instrument.asset_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Currency</span>
              <span className="font-medium">{instrument.currency}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Current Price</CardTitle>
          </CardHeader>
          <CardContent>
            {instrument.current_price != null ? (
              <p className="text-4xl font-bold">
                {parseFloat(instrument.current_price).toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}{" "}
                <span className="text-lg text-muted-foreground">
                  {instrument.price_currency ?? instrument.currency}
                </span>
              </p>
            ) : (
              <p className="text-muted-foreground">Price unavailable</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Interactive Chart */}
      {instrument.ticker && <InstrumentChart instrumentId={id} />}

      {/* AI Analysis */}
      <Card>
        <CardHeader>
          <CardTitle>AI Analysis</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {analysisLoading ? (
            <p className="text-muted-foreground">Loading analysis...</p>
          ) : analysisError || !analysis ? (
            <p className="text-muted-foreground">Analysis unavailable.</p>
          ) : (
            <>
              <div className="flex items-center gap-3">
                <Badge
                  className={`text-white text-lg px-4 py-1 ${recommendationColor[analysis.recommendation]}`}
                >
                  {analysis.recommendation}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {confidenceLabel[analysis.confidence] ?? analysis.confidence}
                </span>
              </div>

              <p className="text-sm leading-relaxed">{analysis.reasoning}</p>

              <Separator />

              <div>
                <h3 className="text-sm font-semibold mb-2">Signals</h3>
                <div className="flex flex-wrap gap-2">
                  {analysis.signals.map((s, i) => (
                    <Badge
                      key={i}
                      variant="outline"
                      className={
                        s.sentiment === "bullish"
                          ? "border-green-500 text-green-700 dark:text-green-400"
                          : "border-red-500 text-red-700 dark:text-red-400"
                      }
                    >
                      {s.signal}
                    </Badge>
                  ))}
                </div>
              </div>

              <Separator />

              <div>
                <h3 className="text-sm font-semibold mb-2">Metrics</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
                  <div>
                    <p className="text-muted-foreground">Current Price</p>
                    <p className="font-medium">{analysis.metrics.current_price}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">SMA 20</p>
                    <p className="font-medium">{analysis.metrics.sma_20}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">SMA 50</p>
                    <p className="font-medium">{analysis.metrics.sma_50}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Weekly Change</p>
                    <p className="font-medium">{analysis.metrics.weekly_change_pct}%</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Monthly Change</p>
                    <p className="font-medium">{analysis.metrics.monthly_change_pct}%</p>
                  </div>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* News */}
      {instrument.news && instrument.news.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>News</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {instrument.news.map((item, i) => (
              <div key={i}>
                <a
                  href={item.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium hover:underline text-blue-600"
                >
                  {item.title}
                </a>
                <p className="text-xs text-muted-foreground">
                  {item.publisher} &middot;{" "}
                  {new Date(item.published).toLocaleDateString()}
                </p>
                {i < instrument.news.length - 1 && <Separator className="mt-3" />}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
