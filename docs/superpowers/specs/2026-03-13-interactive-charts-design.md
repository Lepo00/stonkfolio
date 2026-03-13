# Interactive Instrument Charts — Design Spec

## Goal

Add interactive financial charts (candlestick, line, volume, indicators) to the instrument detail page using TradingView Lightweight Charts, with OHLC data served on-the-fly from yfinance.

## Decisions

- **Location:** Instrument detail page (`/instrument/[id]`), between the price card and AI analysis card
- **Library:** TradingView Lightweight Charts (MIT, ~40KB)
- **Data strategy:** Fetch OHLC from yfinance on-the-fly per request (no DB caching)
- **Indicators:** SMA 20, SMA 50 (overlays), RSI 14 (separate pane), calculated server-side
- **Two chart libraries:** Recharts stays for portfolio-level charts (allocation pies, performance line); Lightweight Charts is used for financial instrument charts (OHLC, volume, indicators). Different tools for different jobs.
- **Out of scope:** Drawing tools, comparison mode, fullscreen mode, DB-cached history

---

## Backend

### New Endpoint

`GET /api/instruments/<id>/chart/?period=6M`

**Period mapping (API → yfinance):**

| API period | yfinance `period` | yfinance `interval` | Notes |
|------------|-------------------|---------------------|-------|
| `1D`       | `"1d"`            | `"5m"`              | Intraday 5-min bars |
| `1W`       | `"5d"`            | `"15m"`             | Hourly-ish bars for 5 trading days |
| `1M`       | `"1mo"`           | `"1d"`              | Daily bars |
| `3M`       | `"3mo"`           | `"1d"`              | Daily bars |
| `6M`       | `"6mo"`           | `"1d"`              | Daily bars (default) |
| `1Y`       | `"1y"`            | `"1d"`              | Daily bars |
| `ALL`      | `"max"`           | `"1wk"`             | Weekly bars to keep data manageable |

**Default period:** `6M` (when `period` query param is omitted)

**Time format in response:**
- Daily/weekly intervals: date string `"2025-01-15"` (YYYY-MM-DD)
- Intraday intervals (1D, 1W): Unix timestamp in seconds (e.g., `1736942400`) — required by Lightweight Charts for intraday data

**Response schema:**

```json
{
  "ticker": "AAPL",
  "currency": "USD",
  "ohlc": [
    {
      "time": "2025-01-15",
      "open": 148.5,
      "high": 152.3,
      "low": 147.8,
      "close": 151.2,
      "volume": 52340000
    }
  ],
  "indicators": {
    "sma_20": [{ "time": "2025-01-15", "value": 149.1 }],
    "sma_50": [{ "time": "2025-01-15", "value": 146.3 }],
    "rsi_14": [{ "time": "2025-01-15", "value": 62.4 }]
  }
}
```

### Implementation Details

**Provider architecture (follows existing pattern):**
1. Add abstract method `get_ohlcv(ticker: str, period: str, interval: str) -> pd.DataFrame` to `PriceProvider` base class (`market_data/providers/base.py`)
2. Implement in `YFinancePriceProvider` — calls `yf.Ticker(ticker).history(period=period, interval=interval)`, returns DataFrame with OHLC+Volume columns
3. Add pass-through `get_ohlcv()` on `MarketDataService` (`market_data/services.py`) that delegates to the provider (consistent with existing `get_current_price` pattern)
4. Returns floats (not Decimal) since chart data is display-only, not financial calculations

**Indicator calculation — new utility `backend/apps/market_data/indicators.py`:**
- `calculate_sma(closes: pd.Series, window: int) -> list[dict]` — rolling mean, returns list of `{time, value}` dicts
- `calculate_rsi(closes: pd.Series, window: int = 14) -> list[dict]` — standard RSI formula (avg gain / avg loss), returns list of `{time, value}` dicts
- **Insufficient data handling:** If fewer data points than the window size, the indicator array is returned partially filled — starting from the first calculable point. Example: SMA 20 with 15 data points → `sma_20: []` (empty). SMA 20 with 25 data points → `sma_20` has 6 entries (points 20-25). This matches how pandas `rolling().mean()` naturally works (NaN for initial window, which we drop).
- This also deduplicates the SMA logic currently inline in `InstrumentAnalysisView`

**New view:** `InstrumentChartView` in `backend/apps/instruments/views.py`
- Uses DRF default authentication (same as existing `InstrumentDetailView` and `InstrumentAnalysisView`)
- Validates period parameter against allowed values, returns 400 for invalid period
- Returns 400 if instrument has no ticker (same pattern as `InstrumentAnalysisView`)
- Looks up instrument by PK (404 if not found), gets ticker
- Calls `MarketDataService.get_ohlcv()` with mapped yfinance period/interval
- Computes indicators via `market_data/indicators.py`
- yfinance call timeout: 10 seconds (pass `timeout=10` to yfinance). Returns 504 on timeout.
- Returns computed OHLC + indicators

**New serializer:** Not needed — response is a simple dict, not model-backed.

**URL:** Added to `backend/apps/instruments/urls.py` as `instruments/<int:pk>/chart/`

---

## Frontend

### New Dependencies

- `lightweight-charts` — TradingView Lightweight Charts library

### New Files

**`frontend/src/components/charts/instrument-chart.tsx`**
- Main chart wrapper component
- Props: `instrumentId: number`
- Manages chart instance lifecycle (create on mount, destroy on unmount via `useRef` + `useEffect`)
- Handles dark/light theme from `theme-context` — passes matching Lightweight Charts theme options
- Two chart instances: main price chart (400px) and RSI chart (120px, collapsible)
- Volume is rendered as a `HistogramSeries` overlay on the main price chart using a secondary price scale (`priceScaleId: 'volume'`) — this is the standard Lightweight Charts pattern, simpler than a separate pane
- Crosshair sync between main chart and RSI chart via Lightweight Charts `subscribeCrosshairMove` API
- Responsive: uses `ResizeObserver` to resize charts when container changes width

**`frontend/src/components/charts/chart-toolbar.tsx`**
- Props: `period`, `onPeriodChange`, `viewType`, `onViewTypeChange`, `indicators`, `onIndicatorsChange`
- Period buttons: 1D, 1W, 1M, 3M, 6M, 1Y, ALL
- View toggle: Candlestick / Line (two buttons or a toggle)
- Indicator checkboxes: SMA 20 (on by default), SMA 50 (on by default), RSI (off by default)

### New API Function

**`frontend/src/lib/api/instruments.ts`** — add:

```typescript
export interface OHLCPoint {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorPoint {
  time: string;
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

export async function getInstrumentChart(id: number, period: string): Promise<ChartData> { ... }
```

### Integration into Instrument Detail Page

**`frontend/src/app/(app)/instrument/[id]/page.tsx`** — modified:
- Import and render `<InstrumentChart instrumentId={id} />` between the price/details cards and the AI analysis card
- Chart component handles its own data fetching, period state, and view state internally

### Chart Behavior

**Series types:**
- **Candlestick view:** `CandlestickSeries` for OHLC data
- **Line view:** `LineSeries` using close prices
- **Volume:** `HistogramSeries` overlaid on price chart with secondary price scale (`priceScaleId: 'volume'`, scaled to ~20% of chart height), bars colored green (close > open) or red (close <= open)
- **SMA 20:** `LineSeries` overlay, blue color, togglable
- **SMA 50:** `LineSeries` overlay, orange color, togglable
- **RSI 14:** `LineSeries` in separate chart instance below the main chart, with horizontal lines at 30 and 70

**Interactions:**
- Crosshair: built-in on each chart, synced between main and RSI via `subscribeCrosshairMove`
- Zoom: mouse scroll
- Pan: click-drag
- Mobile: pinch-to-zoom

**Theming:**
- Read from `theme-context`
- Light: white background, dark grid lines, green/red candles
- Dark: dark background (#1a1a2e or similar), subtle grid, green/red candles

**Data fetching:**
- TanStack Query key: `["instrument-chart", instrumentId, period]` — period changes trigger fresh fetches
- Stale time: 5 minutes
- Loading state: Show skeleton/spinner inside the chart card while data loads
- Error state: Show "Chart data unavailable" message inside the chart area if the API call fails

---

## Page Layout (Top to Bottom)

1. Instrument name + ticker/ISIN
2. Details card + Price card (side by side)
3. **Chart card (NEW):** toolbar + price chart + volume + RSI (collapsible)
4. AI Analysis card
5. News card

---

## Testing

**Backend:**
- Test `get_ohlcv()` method with mocked yfinance response
- Test `InstrumentChartView` — valid period, invalid period (400), nonexistent instrument (404)
- Test SMA and RSI calculation with known data

**Frontend:**
- Test toolbar renders period buttons and toggles
- Test that chart component mounts and calls the API
- Test loading/error states
