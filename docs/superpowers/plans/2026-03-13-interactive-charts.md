# Interactive Instrument Charts Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add interactive candlestick/line charts with volume and technical indicators (SMA, RSI) to the instrument detail page using TradingView Lightweight Charts.

**Architecture:** New backend endpoint fetches OHLC data from yfinance on-the-fly, calculates indicators server-side with pandas, returns JSON. Frontend renders with TradingView Lightweight Charts in a React wrapper component with toolbar for period/view/indicator controls.

**Tech Stack:** Django REST Framework, yfinance, pandas, TradingView Lightweight Charts (`lightweight-charts` npm package), TanStack Query, TypeScript, Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-03-13-interactive-charts-design.md`

---

## File Structure

### Backend (create)
- `backend/apps/market_data/indicators.py` — SMA and RSI calculation utilities using pandas
- `backend/apps/market_data/tests/test_indicators.py` — Tests for indicator calculations
- `backend/apps/instruments/tests/test_chart_api.py` — Tests for the chart endpoint

### Backend (modify)
- `backend/apps/market_data/providers/base.py` — Add abstract `get_ohlcv` method to `PriceProvider`
- `backend/apps/market_data/providers/yfinance_provider.py` — Implement `get_ohlcv` on `YFinancePriceProvider`
- `backend/apps/market_data/services.py` — Add `get_ohlcv` pass-through on `MarketDataService`
- `backend/apps/instruments/views.py` — Add `InstrumentChartView`
- `backend/apps/instruments/urls.py` — Add chart URL pattern

### Frontend (create)
- `frontend/src/components/charts/instrument-chart.tsx` — Main chart wrapper (Lightweight Charts lifecycle, theming, data binding)
- `frontend/src/components/charts/chart-toolbar.tsx` — Period selector, view toggle, indicator checkboxes
- `frontend/src/__tests__/chart-toolbar.test.tsx` — Toolbar component tests

### Frontend (modify)
- `frontend/package.json` — Add `lightweight-charts` dependency
- `frontend/src/types/api.ts` — Add chart data types
- `frontend/src/lib/api/instruments.ts` — Add `getInstrumentChart` function
- `frontend/src/app/(app)/instrument/[id]/page.tsx` — Integrate chart component

---

## Chunk 1: Backend

### Task 1: Indicator Calculation Utilities

**Files:**
- Create: `backend/apps/market_data/indicators.py`
- Create: `backend/apps/market_data/tests/test_indicators.py`

- [ ] **Step 1: Write failing tests for SMA calculation**

```python
# backend/apps/market_data/tests/test_indicators.py
import pandas as pd
import pytest

from apps.market_data.indicators import calculate_sma, calculate_rsi


class TestCalculateSMA:
    def test_sma_basic(self):
        """SMA of [1,2,3,4,5] with window=3 should give [2,3,4] for last 3 points."""
        dates = pd.date_range("2025-01-01", periods=5, freq="D")
        closes = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=dates)
        result = calculate_sma(closes, window=3)
        assert len(result) == 3
        assert result[0]["value"] == pytest.approx(2.0)
        assert result[1]["value"] == pytest.approx(3.0)
        assert result[2]["value"] == pytest.approx(4.0)
        assert result[0]["time"] == "2025-01-03"

    def test_sma_insufficient_data(self):
        """Fewer data points than window returns empty list."""
        dates = pd.date_range("2025-01-01", periods=2, freq="D")
        closes = pd.Series([1.0, 2.0], index=dates)
        result = calculate_sma(closes, window=5)
        assert result == []

    def test_sma_exact_window(self):
        """Exactly window-sized data returns one point."""
        dates = pd.date_range("2025-01-01", periods=3, freq="D")
        closes = pd.Series([10.0, 20.0, 30.0], index=dates)
        result = calculate_sma(closes, window=3)
        assert len(result) == 1
        assert result[0]["value"] == pytest.approx(20.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest apps/market_data/tests/test_indicators.py -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Implement `calculate_sma`**

```python
# backend/apps/market_data/indicators.py
from __future__ import annotations

import pandas as pd


def calculate_sma(closes: pd.Series, window: int, *, intraday: bool = False) -> list[dict]:
    """Calculate Simple Moving Average. Returns list of {time, value} dicts."""
    sma = closes.rolling(window=window).mean().dropna()
    return [
        {"time": _format_time(idx, intraday), "value": round(float(val), 4)}
        for idx, val in sma.items()
    ]


def _format_time(idx, intraday: bool = False) -> str | int:
    """Format pandas index to date string (daily) or unix timestamp (intraday)."""
    if intraday:
        return int(idx.timestamp())
    if hasattr(idx, "date"):
        return str(idx.date())
    return str(idx)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest apps/market_data/tests/test_indicators.py::TestCalculateSMA -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Write failing tests for RSI calculation**

Add to `test_indicators.py`:

```python
class TestCalculateRSI:
    def test_rsi_known_values(self):
        """RSI with known up/down sequence."""
        # 14 gains of 1.0, then 1 loss of 1.0 → RSI should be high then drop
        prices = [100.0 + i for i in range(15)] + [113.0]  # up 14, then down 1
        dates = pd.date_range("2025-01-01", periods=16, freq="D")
        closes = pd.Series(prices, index=dates)
        result = calculate_rsi(closes, window=14)
        assert len(result) >= 1
        # After 14 consecutive gains, RSI should be very high (close to 100)
        assert result[0]["value"] > 90
        # After the drop, RSI should decrease
        assert result[-1]["value"] < result[0]["value"]

    def test_rsi_insufficient_data(self):
        """Fewer than window+1 points returns empty."""
        dates = pd.date_range("2025-01-01", periods=5, freq="D")
        closes = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=dates)
        result = calculate_rsi(closes, window=14)
        assert result == []

    def test_rsi_bounds(self):
        """RSI values should be between 0 and 100."""
        dates = pd.date_range("2025-01-01", periods=50, freq="D")
        import numpy as np
        np.random.seed(42)
        closes = pd.Series(np.random.uniform(90, 110, 50), index=dates)
        result = calculate_rsi(closes, window=14)
        for point in result:
            assert 0 <= point["value"] <= 100
```

- [ ] **Step 6: Run to verify RSI tests fail**

Run: `cd backend && python -m pytest apps/market_data/tests/test_indicators.py::TestCalculateRSI -v`
Expected: FAIL with `ImportError` (calculate_rsi not defined)

- [ ] **Step 7: Implement `calculate_rsi`**

Add to `backend/apps/market_data/indicators.py`:

```python
def calculate_rsi(closes: pd.Series, window: int = 14, *, intraday: bool = False) -> list[dict]:
    """Calculate Relative Strength Index. Returns list of {time, value} dicts."""
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.dropna()

    return [
        {"time": _format_time(idx, intraday), "value": round(float(val), 2)}
        for idx, val in rsi.items()
    ]
```

- [ ] **Step 8: Run all indicator tests**

Run: `cd backend && python -m pytest apps/market_data/tests/test_indicators.py -v`
Expected: PASS (6 tests)

- [ ] **Step 9: Commit**

```bash
git add backend/apps/market_data/indicators.py backend/apps/market_data/tests/test_indicators.py
git commit -m "feat: add SMA and RSI indicator calculation utilities"
```

---

### Task 2: Provider and Service Layer — `get_ohlcv`

**Files:**
- Modify: `backend/apps/market_data/providers/base.py`
- Modify: `backend/apps/market_data/providers/yfinance_provider.py`
- Modify: `backend/apps/market_data/services.py`

- [ ] **Step 1: Add abstract method to PriceProvider**

In `backend/apps/market_data/providers/base.py`, add the import and abstract method:

```python
# Add to imports at top
from typing import Any

# Add to PriceProvider class, after get_historical_prices
    @abstractmethod
    def get_ohlcv(self, ticker: str, period: str, interval: str) -> Any:
        """Return OHLC+Volume data as a pandas DataFrame."""
        ...
```

Note: We use `Any` return type instead of `pd.DataFrame` to avoid importing pandas in the base module. The concrete implementation returns a DataFrame.

- [ ] **Step 2: Implement `get_ohlcv` on YFinancePriceProvider**

In `backend/apps/market_data/providers/yfinance_provider.py`, add:

```python
    def get_ohlcv(self, ticker: str, period: str, interval: str):
        """Fetch OHLC+Volume data from yfinance. Returns a pandas DataFrame."""
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval, timeout=10)
        if df.empty:
            raise ValueError(f"No OHLCV data for {ticker} (period={period})")
        return df
```

- [ ] **Step 3: Add pass-through on MarketDataService**

In `backend/apps/market_data/services.py`, add method to `MarketDataService`:

```python
    def get_ohlcv(self, instrument, period: str, interval: str):
        """Fetch OHLCV data for an instrument. Returns a pandas DataFrame."""
        if not instrument.ticker:
            raise ValueError(f"No ticker for instrument {instrument.isin}")
        return self.provider.get_ohlcv(instrument.ticker, period, interval)
```

- [ ] **Step 4: Run existing tests to verify nothing broke**

Run: `cd backend && python -m pytest apps/market_data/tests/ -v`
Expected: All existing tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/market_data/providers/base.py backend/apps/market_data/providers/yfinance_provider.py backend/apps/market_data/services.py
git commit -m "feat: add get_ohlcv to provider and service layer"
```

---

### Task 3: Chart API Endpoint

**Files:**
- Modify: `backend/apps/instruments/views.py`
- Modify: `backend/apps/instruments/urls.py`
- Create: `backend/apps/instruments/tests/test_chart_api.py`

The period mapping from the spec:

| API period | yfinance `period` | yfinance `interval` |
|------------|-------------------|---------------------|
| `1D`       | `"1d"`            | `"5m"`              |
| `1W`       | `"5d"`            | `"15m"`             |
| `1M`       | `"1mo"`           | `"1d"`              |
| `3M`       | `"3mo"`           | `"1d"`              |
| `6M`       | `"6mo"`           | `"1d"`              |
| `1Y`       | `"1y"`            | `"1d"`              |
| `ALL`      | `"max"`           | `"1wk"`             |

- [ ] **Step 1: Write failing tests for the chart endpoint**

```python
# backend/apps/instruments/tests/test_chart_api.py
from unittest.mock import patch

import pandas as pd
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.instruments.models import Instrument
from apps.users.models import User


@pytest.mark.django_db
class TestInstrumentChartAPI:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.inst = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="iShares MSCI World",
            currency="EUR",
            asset_type="ETF",
        )

    def _mock_ohlcv_df(self, periods=30, freq="D"):
        """Create a mock OHLCV DataFrame."""
        dates = pd.date_range("2025-01-01", periods=periods, freq=freq)
        return pd.DataFrame(
            {
                "Open": [100.0 + i * 0.5 for i in range(periods)],
                "High": [101.0 + i * 0.5 for i in range(periods)],
                "Low": [99.0 + i * 0.5 for i in range(periods)],
                "Close": [100.5 + i * 0.5 for i in range(periods)],
                "Volume": [1000000 + i * 10000 for i in range(periods)],
            },
            index=dates,
        )

    @patch("apps.instruments.views.MarketDataService")
    def test_chart_default_period(self, MockService):
        MockService.return_value.get_ohlcv.return_value = self._mock_ohlcv_df()
        resp = self.client.get(f"/api/instruments/{self.inst.id}/chart/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["ticker"] == "IWDA.AS"
        assert resp.data["currency"] == "EUR"
        assert len(resp.data["ohlc"]) == 30
        assert "open" in resp.data["ohlc"][0]
        assert "high" in resp.data["ohlc"][0]
        assert "low" in resp.data["ohlc"][0]
        assert "close" in resp.data["ohlc"][0]
        assert "volume" in resp.data["ohlc"][0]
        assert "time" in resp.data["ohlc"][0]

    @patch("apps.instruments.views.MarketDataService")
    def test_chart_with_indicators(self, MockService):
        MockService.return_value.get_ohlcv.return_value = self._mock_ohlcv_df(periods=60)
        resp = self.client.get(f"/api/instruments/{self.inst.id}/chart/?period=3M")
        assert resp.status_code == status.HTTP_200_OK
        assert "sma_20" in resp.data["indicators"]
        assert "sma_50" in resp.data["indicators"]
        assert "rsi_14" in resp.data["indicators"]
        # With 60 data points, SMA 20 should have 41 points, SMA 50 should have 11
        assert len(resp.data["indicators"]["sma_20"]) == 41
        assert len(resp.data["indicators"]["sma_50"]) == 11

    @patch("apps.instruments.views.MarketDataService")
    def test_chart_sparse_data_indicators_empty(self, MockService):
        MockService.return_value.get_ohlcv.return_value = self._mock_ohlcv_df(periods=10)
        resp = self.client.get(f"/api/instruments/{self.inst.id}/chart/?period=1M")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["ohlc"]) == 10
        # SMA 20 requires 20 points, so empty with only 10
        assert resp.data["indicators"]["sma_20"] == []
        assert resp.data["indicators"]["sma_50"] == []

    def test_chart_invalid_period(self):
        resp = self.client.get(f"/api/instruments/{self.inst.id}/chart/?period=INVALID")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_chart_instrument_not_found(self):
        resp = self.client.get("/api/instruments/99999/chart/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_chart_no_ticker(self):
        inst = Instrument.objects.create(
            isin="XX0000000000",
            name="No Ticker",
            currency="EUR",
            asset_type="OTHER",
        )
        resp = self.client.get(f"/api/instruments/{inst.id}/chart/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.instruments.views.MarketDataService")
    def test_chart_intraday_returns_unix_timestamps(self, MockService):
        """1D period uses 5-min intervals, time should be unix timestamps."""
        dates = pd.date_range("2025-01-15 09:30", periods=10, freq="5min")
        df = pd.DataFrame(
            {
                "Open": [100.0] * 10,
                "High": [101.0] * 10,
                "Low": [99.0] * 10,
                "Close": [100.5] * 10,
                "Volume": [50000] * 10,
            },
            index=dates,
        )
        MockService.return_value.get_ohlcv.return_value = df
        resp = self.client.get(f"/api/instruments/{self.inst.id}/chart/?period=1D")
        assert resp.status_code == status.HTTP_200_OK
        # Intraday time should be unix timestamp (integer)
        assert isinstance(resp.data["ohlc"][0]["time"], int)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest apps/instruments/tests/test_chart_api.py -v`
Expected: FAIL (InstrumentChartView doesn't exist yet)

- [ ] **Step 3: Implement InstrumentChartView**

Add to `backend/apps/instruments/views.py`:

```python
# Add to imports at top
from apps.market_data.indicators import calculate_rsi, calculate_sma

# Add the period mapping as a module-level constant
CHART_PERIOD_MAP = {
    "1D": ("1d", "5m"),
    "1W": ("5d", "15m"),
    "1M": ("1mo", "1d"),
    "3M": ("3mo", "1d"),
    "6M": ("6mo", "1d"),
    "1Y": ("1y", "1d"),
    "ALL": ("max", "1wk"),
}


class InstrumentChartView(APIView):
    """OHLCV chart data with technical indicators."""

    def get(self, request, pk):
        try:
            instrument = Instrument.objects.get(pk=pk)
        except Instrument.DoesNotExist:
            return Response({"error": "Instrument not found"}, status=status.HTTP_404_NOT_FOUND)

        if not instrument.ticker:
            return Response({"error": "No ticker available for chart data"}, status=status.HTTP_400_BAD_REQUEST)

        period = request.query_params.get("period", "6M")
        if period not in CHART_PERIOD_MAP:
            return Response(
                {"error": f"Invalid period. Allowed: {', '.join(CHART_PERIOD_MAP.keys())}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        yf_period, yf_interval = CHART_PERIOD_MAP[period]

        try:
            service = MarketDataService()
            df = service.get_ohlcv(instrument, yf_period, yf_interval)
        except Exception:
            logger.exception("Failed to fetch chart data for instrument %s", pk)
            return Response({"error": "Chart data temporarily unavailable"}, status=status.HTTP_502_BAD_GATEWAY)

        # Build OHLC response
        is_intraday = yf_interval in ("5m", "15m")
        ohlc = []
        for idx, row in df.iterrows():
            time_val = int(idx.timestamp()) if is_intraday else str(idx.date())
            ohlc.append({
                "time": time_val,
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            })

        # Calculate indicators
        closes = df["Close"].astype(float)
        indicators = {
            "sma_20": calculate_sma(closes, window=20, intraday=is_intraday),
            "sma_50": calculate_sma(closes, window=50, intraday=is_intraday),
            "rsi_14": calculate_rsi(closes, window=14, intraday=is_intraday),
        }

        return Response({
            "ticker": instrument.ticker,
            "currency": instrument.currency,
            "ohlc": ohlc,
            "indicators": indicators,
        })
```

- [ ] **Step 4: Add URL pattern**

In `backend/apps/instruments/urls.py`, add the import and URL:

```python
from .views import InstrumentAnalysisView, InstrumentChartView, InstrumentDetailView

urlpatterns = [
    path("instruments/<int:pk>/", InstrumentDetailView.as_view(), name="instrument-detail"),
    path("instruments/<int:pk>/analysis/", InstrumentAnalysisView.as_view(), name="instrument-analysis"),
    path("instruments/<int:pk>/chart/", InstrumentChartView.as_view(), name="instrument-chart"),
]
```

- [ ] **Step 5: Run chart API tests**

Run: `cd backend && python -m pytest apps/instruments/tests/test_chart_api.py -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Run full backend test suite**

Run: `cd backend && python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/apps/instruments/views.py backend/apps/instruments/urls.py backend/apps/instruments/tests/test_chart_api.py
git commit -m "feat: add instrument chart API endpoint with OHLCV and indicators"
```

---

## Chunk 2: Frontend

### Task 4: Install Lightweight Charts and Add Types

**Files:**
- Modify: `frontend/package.json` (via npm)
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/lib/api/instruments.ts`

- [ ] **Step 1: Install lightweight-charts**

```bash
cd frontend && npm install lightweight-charts@4
```

Note: We pin to v4 because v5 changed the API significantly (`addCandlestickSeries` → `addSeries(CandlestickSeries)`, crosshair sync changes). All chart code in this plan uses the v4 API.

- [ ] **Step 2: Add chart data types**

In `frontend/src/types/api.ts`, add at the end of the file:

```typescript
export interface OHLCPoint {
  time: string | number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorPoint {
  time: string | number;
  value: number;
}

export interface ChartData {
  ticker: string;
  currency: string;
  ohlc: OHLCPoint[];
  indicators: {
    sma_20: IndicatorPoint[];
    sma_50: IndicatorPoint[];
    rsi_14: IndicatorPoint[];
  };
}
```

- [ ] **Step 3: Add API function**

In `frontend/src/lib/api/instruments.ts`, add:

```typescript
import type { InstrumentDetail, StockAnalysis, ChartData } from "@/types/api";

export async function getInstrumentChart(id: number, period: string = "6M") {
  return apiClient<ChartData>(`/instruments/${id}/chart/?period=${period}`);
}
```

Update the existing import at the top to include `ChartData`.

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/types/api.ts frontend/src/lib/api/instruments.ts
git commit -m "feat: add lightweight-charts dependency and chart API types"
```

---

### Task 5: Chart Toolbar Component

**Files:**
- Create: `frontend/src/components/charts/chart-toolbar.tsx`

- [ ] **Step 1: Create the toolbar component**

```tsx
// frontend/src/components/charts/chart-toolbar.tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/charts/chart-toolbar.tsx
git commit -m "feat: add chart toolbar component with period, view, and indicator controls"
```

---

### Task 6: Instrument Chart Component

This is the core component. It manages TradingView Lightweight Charts lifecycle, data binding, theming, and indicator overlays.

**Files:**
- Create: `frontend/src/components/charts/instrument-chart.tsx`

- [ ] **Step 1: Create the chart component**

```tsx
// frontend/src/components/charts/instrument-chart.tsx
"use client";

import { useRef, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  createChart,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
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

  const [period, setPeriod] = useState("6M");
  const [viewType, setViewType] = useState<ViewType>("Candlestick");
  const [indicators, setIndicators] = useState<IndicatorState>({
    sma20: true,
    sma50: true,
    rsi: false,
  });
  // Counter to trigger data re-render after chart recreation (e.g., theme change)
  const [chartVersion, setChartVersion] = useState(0);

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

    // Bump version so data effect re-runs after chart recreation
    setChartVersion((v) => v + 1);

    return () => {
      observer.disconnect();
      chart.remove();
      mainChartApi.current = null;
    };
  }, [colors]);

  // Create RSI chart, populate data, and sync crosshair — all in one effect
  // to avoid race conditions between chart creation and data binding.
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

    // Add RSI data
    const rsiSeries = chart.addLineSeries({
      color: "#a855f7",
      lineWidth: 1.5,
      priceLineVisible: false,
    });
    rsiSeries.setData(
      data.indicators.rsi_14.map((d) => ({
        time: d.time as Time,
        value: d.value,
      }))
    );
    rsiSeries.createPriceLine({ price: 70, color: "#ef4444", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "" });
    rsiSeries.createPriceLine({ price: 30, color: "#22c55e", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: "" });
    chart.priceScale("right").applyOptions({ scaleMargins: { top: 0.05, bottom: 0.05 } });
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (rsiChartRef.current) {
        chart.applyOptions({ width: rsiChartRef.current.clientWidth });
      }
    };
    const observer = new ResizeObserver(handleResize);
    observer.observe(rsiChartRef.current);

    // Sync crosshair from main to RSI
    if (mainChartApi.current) {
      mainChartApi.current.subscribeCrosshairMove((param) => {
        if (param.time && rsiChartApi.current) {
          rsiChartApi.current.setCrosshairPosition(NaN, param.time, rsiChartApi.current.timeScale());
        }
      });
    }

    return () => {
      observer.disconnect();
      chart.remove();
      rsiChartApi.current = null;
    };
  }, [colors, indicators.rsi, data]);

  // Update chart data when data/viewType/indicators change
  useEffect(() => {
    const chart = mainChartApi.current;
    if (!chart || !data) return;

    // Track series to remove on cleanup (when data/view/indicators change)
    const seriesToRemove: ISeriesApi<any>[] = [];

    // Price series
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

    // Volume as overlay with secondary price scale
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
        d.close >= d.open
          ? "rgba(34,197,94,0.4)"
          : "rgba(239,68,68,0.4)",
    }));
    volumeSeries.setData(volumeData);
    seriesToRemove.push(volumeSeries);

    // SMA 20 overlay
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

    // SMA 50 overlay
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

    // Cleanup: remove all series we added
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
  }, [data, viewType, indicators.sma20, indicators.sma50, chartVersion]);

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
            <div ref={mainChartRef} />
            {indicators.rsi && <div ref={rsiChartRef} />}
          </>
        )}
      </CardContent>
    </Card>
  );
}
```

**Implementation notes:**
- We pin `lightweight-charts@4` — all code uses the v4 API. Do NOT upgrade to v5 (breaking API changes).
- The main chart creation and data update effects are separated intentionally — chart instance lives longer than data updates. A `chartVersion` counter ensures data re-renders after chart recreation (e.g., theme change).
- The RSI chart creation and data population are combined into a single effect to avoid race conditions.

- [ ] **Step 2: Verify frontend compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No type errors. If there are Lightweight Charts API issues, fix them based on the installed version's types.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/charts/instrument-chart.tsx
git commit -m "feat: add interactive instrument chart component with Lightweight Charts"
```

---

### Task 7: Integrate Chart into Instrument Detail Page

**Files:**
- Modify: `frontend/src/app/(app)/instrument/[id]/page.tsx`

- [ ] **Step 1: Add chart import and render**

In `frontend/src/app/(app)/instrument/[id]/page.tsx`:

1. Add import at the top:
```tsx
import { InstrumentChart } from "@/components/charts/instrument-chart";
```

2. Add the chart component between the price/details grid and the AI Analysis card. Find the closing `</div>` of the grid (`grid grid-cols-1 md:grid-cols-2 gap-4`) and add after it:

```tsx
      {/* Interactive Chart */}
      {instrument.ticker && <InstrumentChart instrumentId={id} />}
```

This goes right before the `{/* AI Analysis */}` comment. The `instrument.ticker &&` guard ensures we only show the chart for instruments with tickers (matching the backend's 400 response for no-ticker instruments).

- [ ] **Step 2: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/(app)/instrument/[id]/page.tsx
git commit -m "feat: integrate interactive chart into instrument detail page"
```

---

### Task 8: Frontend Chart Tests

**Files:**
- Create: `frontend/src/__tests__/chart-toolbar.test.tsx`

- [ ] **Step 1: Create toolbar tests**

```tsx
// frontend/src/__tests__/chart-toolbar.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChartToolbar, type ViewType, type IndicatorState } from "@/components/charts/chart-toolbar";

const defaultProps = {
  period: "6M",
  onPeriodChange: jest.fn(),
  viewType: "Candlestick" as ViewType,
  onViewTypeChange: jest.fn(),
  indicators: { sma20: true, sma50: true, rsi: false } as IndicatorState,
  onIndicatorsChange: jest.fn(),
};

describe("ChartToolbar", () => {
  beforeEach(() => jest.clearAllMocks());

  it("renders all period buttons", () => {
    render(<ChartToolbar {...defaultProps} />);
    for (const p of ["1D", "1W", "1M", "3M", "6M", "1Y", "ALL"]) {
      expect(screen.getByRole("button", { name: p })).toBeInTheDocument();
    }
  });

  it("renders view toggle buttons", () => {
    render(<ChartToolbar {...defaultProps} />);
    expect(screen.getByRole("button", { name: "Candlestick" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Line" })).toBeInTheDocument();
  });

  it("renders indicator checkboxes with correct state", () => {
    render(<ChartToolbar {...defaultProps} />);
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes).toHaveLength(3);
    expect(checkboxes[0]).toBeChecked(); // SMA 20
    expect(checkboxes[1]).toBeChecked(); // SMA 50
    expect(checkboxes[2]).not.toBeChecked(); // RSI
  });

  it("calls onPeriodChange when period button clicked", async () => {
    render(<ChartToolbar {...defaultProps} />);
    await userEvent.click(screen.getByRole("button", { name: "1M" }));
    expect(defaultProps.onPeriodChange).toHaveBeenCalledWith("1M");
  });

  it("calls onViewTypeChange when view button clicked", async () => {
    render(<ChartToolbar {...defaultProps} />);
    await userEvent.click(screen.getByRole("button", { name: "Line" }));
    expect(defaultProps.onViewTypeChange).toHaveBeenCalledWith("Line");
  });

  it("calls onIndicatorsChange when checkbox toggled", async () => {
    render(<ChartToolbar {...defaultProps} />);
    const rsiCheckbox = screen.getAllByRole("checkbox")[2];
    await userEvent.click(rsiCheckbox);
    expect(defaultProps.onIndicatorsChange).toHaveBeenCalledWith({
      sma20: true,
      sma50: true,
      rsi: true,
    });
  });
});
```

Note: We only test the toolbar (pure presentational component). The chart component itself uses canvas/WebGL via Lightweight Charts which doesn't render in jsdom. Integration testing of the chart would require a browser environment (e.g., Playwright), which is out of scope.

- [ ] **Step 2: Run tests**

```bash
cd frontend && npm test -- --testPathPattern=chart-toolbar
```

Expected: 6 tests PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/__tests__/chart-toolbar.test.tsx
git commit -m "test: add chart toolbar component tests"
```

---

### Task 9: Final Verification and Lint

**Files:** None (verification only)

- [ ] **Step 1: Run backend tests**

```bash
cd backend && python -m pytest -v
```

Expected: All tests pass (including new chart tests)

- [ ] **Step 2: Run backend lint**

```bash
cd backend && ruff check .
```

Expected: No lint errors

- [ ] **Step 3: Run frontend lint**

```bash
cd frontend && npm run lint
```

Expected: No lint errors

- [ ] **Step 4: Run frontend tests**

```bash
cd frontend && npm test
```

Expected: All tests pass

- [ ] **Step 5: Run frontend build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds

- [ ] **Step 6: Commit any lint fixes if needed, then push**

```bash
git push origin main
```
