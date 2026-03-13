"use client";

import { Button } from "@/components/ui/button";

const PERIODS = ["1D", "1W", "1M", "3M", "6M", "1Y", "ALL"] as const;
const VIEW_TYPES = ["Candlestick", "Line"] as const;

export type ViewType = (typeof VIEW_TYPES)[number];

export interface IndicatorState {
  sma20: boolean;
  sma50: boolean;
  rsi: boolean;
}

interface ChartToolbarProps {
  period: string;
  onPeriodChange: (period: string) => void;
  viewType: ViewType;
  onViewTypeChange: (view: ViewType) => void;
  indicators: IndicatorState;
  onIndicatorsChange: (indicators: IndicatorState) => void;
}

export function ChartToolbar({
  period,
  onPeriodChange,
  viewType,
  onViewTypeChange,
  indicators,
  onIndicatorsChange,
}: ChartToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Period selector */}
      <div className="flex gap-1">
        {PERIODS.map((p) => (
          <Button
            key={p}
            variant={period === p ? "default" : "outline"}
            size="sm"
            onClick={() => onPeriodChange(p)}
          >
            {p}
          </Button>
        ))}
      </div>

      {/* View toggle */}
      <div className="flex gap-1 border-l pl-3">
        {VIEW_TYPES.map((v) => (
          <Button
            key={v}
            variant={viewType === v ? "default" : "outline"}
            size="sm"
            onClick={() => onViewTypeChange(v)}
          >
            {v}
          </Button>
        ))}
      </div>

      {/* Indicator checkboxes */}
      <div className="flex items-center gap-3 border-l pl-3 text-sm">
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="checkbox"
            checked={indicators.sma20}
            onChange={(e) =>
              onIndicatorsChange({ ...indicators, sma20: e.target.checked })
            }
            className="rounded"
          />
          <span className="text-blue-500 font-medium">SMA 20</span>
        </label>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="checkbox"
            checked={indicators.sma50}
            onChange={(e) =>
              onIndicatorsChange({ ...indicators, sma50: e.target.checked })
            }
            className="rounded"
          />
          <span className="text-orange-500 font-medium">SMA 50</span>
        </label>
        <label className="flex items-center gap-1.5 cursor-pointer">
          <input
            type="checkbox"
            checked={indicators.rsi}
            onChange={(e) =>
              onIndicatorsChange({ ...indicators, rsi: e.target.checked })
            }
            className="rounded"
          />
          <span className="text-purple-500 font-medium">RSI</span>
        </label>
      </div>
    </div>
  );
}
