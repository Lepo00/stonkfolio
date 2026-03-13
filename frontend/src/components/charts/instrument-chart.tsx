"use client";

import { useRef, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  createChart,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type SeriesType,
  type CandlestickData,
  type LineData,
  type HistogramData,
  type Time,
} from "lightweight-charts";
import { useTheme } from "@/lib/theme-context";
import { getInstrumentChart } from "@/lib/api/instruments";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ChartToolbar,
  type ViewType,
  type IndicatorState,
} from "./chart-toolbar";

interface InstrumentChartProps {
  instrumentId: number;
}

const LIGHT_THEME = {
  background: "#ffffff",
  textColor: "#333333",
  gridColor: "#f0f0f0",
  borderColor: "#e0e0e0",
};

const DARK_THEME = {
  background: "#1a1a2e",
  textColor: "#d1d5db",
  gridColor: "#2d2d44",
  borderColor: "#2d2d44",
};

export function InstrumentChart({ instrumentId }: InstrumentChartProps) {
  const mainChartRef = useRef<HTMLDivElement>(null);
  const rsiChartRef = useRef<HTMLDivElement>(null);
  const mainChartApi = useRef<IChartApi | null>(null);
  const rsiChartApi = useRef<IChartApi | null>(null);
  const rsiSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  const [period, setPeriod] = useState("6M");
  const [viewType, setViewType] = useState<ViewType>("Candlestick");
  const [indicators, setIndicators] = useState<IndicatorState>({
    sma20: true,
    sma50: true,
    rsi: false,
  });
  const { resolvedTheme } = useTheme();
  const colors = resolvedTheme === "dark" ? DARK_THEME : LIGHT_THEME;

  const { data, isLoading, error } = useQuery({
    queryKey: ["instrument-chart", instrumentId, period],
    queryFn: () => getInstrumentChart(instrumentId, period),
    staleTime: 5 * 60 * 1000,
  });

  // Create and manage main chart
  useEffect(() => {
    if (!mainChartRef.current) return;

    const chart = createChart(mainChartRef.current, {
      width: mainChartRef.current.clientWidth,
      height: 400,
      layout: {
        background: { type: ColorType.Solid, color: colors.background },
        textColor: colors.textColor,
      },
      grid: {
        vertLines: { color: colors.gridColor },
        horzLines: { color: colors.gridColor },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: colors.borderColor },
      timeScale: { borderColor: colors.borderColor },
    });

    mainChartApi.current = chart;

    const handleResize = () => {
      if (mainChartRef.current) {
        chart.applyOptions({ width: mainChartRef.current.clientWidth });
      }
    };
    const observer = new ResizeObserver(handleResize);
    observer.observe(mainChartRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      mainChartApi.current = null;
    };
  }, [colors]);

  // Create RSI chart, populate data, and sync crosshair — all in one effect
  useEffect(() => {
    if (!rsiChartRef.current || !indicators.rsi || !data) return;

    const chart = createChart(rsiChartRef.current, {
      width: rsiChartRef.current.clientWidth,
      height: 120,
      layout: {
        background: { type: ColorType.Solid, color: colors.background },
        textColor: colors.textColor,
      },
      grid: {
        vertLines: { color: colors.gridColor },
        horzLines: { color: colors.gridColor },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: colors.borderColor },
      timeScale: { borderColor: colors.borderColor, visible: false },
    });

    rsiChartApi.current = chart;

    const rsiSeries = chart.addLineSeries({
      color: "#a855f7",
      lineWidth: 1,
      priceLineVisible: false,
    });
    rsiSeriesRef.current = rsiSeries;

    rsiSeries.setData(
      data.indicators.rsi_14.map((d) => ({
        time: d.time as Time,
        value: d.value,
      }))
    );
    rsiSeries.createPriceLine({
      price: 70,
      color: "#ef4444",
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: "",
    });
    rsiSeries.createPriceLine({
      price: 30,
      color: "#22c55e",
      lineWidth: 1,
      lineStyle: 2,
      axisLabelVisible: true,
      title: "",
    });
    chart.priceScale("right").applyOptions({
      scaleMargins: { top: 0.05, bottom: 0.05 },
    });
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (rsiChartRef.current) {
        chart.applyOptions({ width: rsiChartRef.current.clientWidth });
      }
    };
    const observer = new ResizeObserver(handleResize);
    observer.observe(rsiChartRef.current);

    const mainChart = mainChartApi.current;
    const crosshairHandler = mainChart
      ? (param: { time?: unknown }) => {
          if (param.time && rsiChartApi.current && rsiSeriesRef.current) {
            rsiChartApi.current.setCrosshairPosition(
              NaN,
              param.time as Time,
              rsiSeriesRef.current
            );
          }
        }
      : null;

    if (mainChart && crosshairHandler) {
      mainChart.subscribeCrosshairMove(crosshairHandler);
    }

    return () => {
      if (mainChart && crosshairHandler) {
        mainChart.unsubscribeCrosshairMove(crosshairHandler);
      }
      observer.disconnect();
      chart.remove();
      rsiChartApi.current = null;
      rsiSeriesRef.current = null;
    };
  }, [colors, indicators.rsi, data]);

  // Update main chart data
  useEffect(() => {
    const chart = mainChartApi.current;
    if (!chart || !data) return;

    const seriesToRemove: ISeriesApi<SeriesType>[] = [];

    if (viewType === "Candlestick") {
      const candleSeries = chart.addCandlestickSeries({
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderDownColor: "#ef4444",
        borderUpColor: "#22c55e",
        wickDownColor: "#ef4444",
        wickUpColor: "#22c55e",
      });
      const candleData: CandlestickData[] = data.ohlc.map((d) => ({
        time: d.time as Time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }));
      candleSeries.setData(candleData);
      seriesToRemove.push(candleSeries);
    } else {
      const lineSeries = chart.addLineSeries({
        color: "#2563eb",
        lineWidth: 2,
      });
      const lineData: LineData[] = data.ohlc.map((d) => ({
        time: d.time as Time,
        value: d.close,
      }));
      lineSeries.setData(lineData);
      seriesToRemove.push(lineSeries);
    }

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });
    const volumeData: HistogramData[] = data.ohlc.map((d) => ({
      time: d.time as Time,
      value: d.volume,
      color:
        d.close >= d.open ? "rgba(34,197,94,0.4)" : "rgba(239,68,68,0.4)",
    }));
    volumeSeries.setData(volumeData);
    seriesToRemove.push(volumeSeries);

    if (indicators.sma20 && data.indicators.sma_20.length > 0) {
      const sma20Series = chart.addLineSeries({
        color: "#3b82f6",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      sma20Series.setData(
        data.indicators.sma_20.map((d) => ({
          time: d.time as Time,
          value: d.value,
        }))
      );
      seriesToRemove.push(sma20Series);
    }

    if (indicators.sma50 && data.indicators.sma_50.length > 0) {
      const sma50Series = chart.addLineSeries({
        color: "#f97316",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      sma50Series.setData(
        data.indicators.sma_50.map((d) => ({
          time: d.time as Time,
          value: d.value,
        }))
      );
      seriesToRemove.push(sma50Series);
    }

    chart.timeScale().fitContent();

    return () => {
      if (mainChartApi.current) {
        seriesToRemove.forEach((s) => {
          try {
            mainChartApi.current?.removeSeries(s);
          } catch {
            // Series may already be removed if chart was destroyed
          }
        });
      }
    };
  }, [data, viewType, indicators.sma20, indicators.sma50, resolvedTheme]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Chart</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <ChartToolbar
          period={period}
          onPeriodChange={setPeriod}
          viewType={viewType}
          onViewTypeChange={setViewType}
          indicators={indicators}
          onIndicatorsChange={setIndicators}
        />

        {isLoading ? (
          <div className="h-[400px] flex items-center justify-center">
            <p className="text-muted-foreground">Loading chart data...</p>
          </div>
        ) : error ? (
          <div className="h-[400px] flex items-center justify-center">
            <p className="text-destructive">Chart data unavailable</p>
          </div>
        ) : (
          <>
            <div ref={mainChartRef} aria-label="Price chart" role="img" />
            {indicators.rsi && <div ref={rsiChartRef} aria-label="RSI indicator chart" role="img" />}
          </>
        )}
      </CardContent>
    </Card>
  );
}
