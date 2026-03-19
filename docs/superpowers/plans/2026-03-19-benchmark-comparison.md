# Benchmark Comparison — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compare portfolio performance against market benchmarks (MSCI World, S&P 500) on the performance page and dashboard, with both series normalized to base-100 for fair visual comparison.

**Architecture:** A new `get_benchmark_series()` function in `MarketDataService` fetches daily close prices for a benchmark ticker via yfinance, normalizes them to base-100, and caches the result for 24 hours using Django's cache framework. `PortfolioPerformanceView` accepts an optional `benchmark` query param, normalizes both portfolio and benchmark series to base-100, and returns them side-by-side. `PortfolioSummaryView` gains a `benchmark_return_pct` field. On the frontend, a selector dropdown on the performance page toggles the benchmark overlay (gray dashed line), and an alpha metric appears on both the performance page and dashboard.

**Tech Stack:** Django 5 + DRF, yfinance, Django cache framework (backend); Next.js 16, React 19, Recharts, TanStack Query v5, shadcn/ui Select, Tailwind v4 (frontend)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/apps/market_data/services.py` | Modify | Add `BENCHMARK_MAP`, `get_benchmark_series()` with 24h caching |
| `backend/apps/market_data/tests/test_services.py` | Modify | Tests for `get_benchmark_series()` |
| `backend/apps/portfolios/views.py` | Modify | Add `benchmark` param to `PortfolioPerformanceView`, normalize both series to base-100; add `benchmark_return_pct` to `PortfolioSummaryView` |
| `backend/apps/portfolios/tests/test_analytics.py` | Modify | Tests for benchmark in performance and summary endpoints |
| `frontend/src/types/api.ts` | Modify | Add `benchmark_series`, `benchmark_name` to `PerformanceSeries`; add `benchmark_return_pct` to `PortfolioSummary` |
| `frontend/src/lib/api/portfolios.ts` | Modify | Pass `benchmark` query param in `getPerformance` and `getSummary` |
| `frontend/src/app/(app)/performance/page.tsx` | Modify | Add benchmark selector, overlay benchmark line, show alpha |
| `frontend/src/app/(app)/dashboard/page.tsx` | Modify | Show alpha vs benchmark in Overall Gain/Loss card |

---

### Task 1: Add `get_benchmark_series()` to MarketDataService

**Files:**
- Modify: `backend/apps/market_data/services.py`
- Modify: `backend/apps/market_data/tests/test_services.py`

- [ ] **Step 1: Write tests for `get_benchmark_series`**

Add the following tests to `backend/apps/market_data/tests/test_services.py`:

```python
from apps.market_data.services import BENCHMARK_MAP


class TestGetBenchmarkSeries:
    @patch("apps.market_data.services.MarketDataService.get_historical_prices_by_ticker")
    def test_returns_base100_series(self, mock_hist):
        mock_hist.return_value = [
            PricePoint(date=date(2025, 1, 1), price=Decimal("100.00")),
            PricePoint(date=date(2025, 1, 2), price=Decimal("105.00")),
            PricePoint(date=date(2025, 1, 3), price=Decimal("110.00")),
        ]
        service = MarketDataService()
        result = service.get_benchmark_series("sp500", date(2025, 1, 1), date(2025, 1, 3))

        assert result is not None
        assert len(result) == 3
        assert result[0]["value"] == "100.00"
        assert result[1]["value"] == "105.00"
        assert result[2]["value"] == "110.00"

    @patch("apps.market_data.services.MarketDataService.get_historical_prices_by_ticker")
    def test_normalizes_to_base_100(self, mock_hist):
        mock_hist.return_value = [
            PricePoint(date=date(2025, 1, 1), price=Decimal("5000.00")),
            PricePoint(date=date(2025, 1, 2), price=Decimal("5100.00")),
        ]
        service = MarketDataService()
        result = service.get_benchmark_series("sp500", date(2025, 1, 1), date(2025, 1, 2))

        assert result[0]["value"] == "100.00"
        assert result[1]["value"] == "102.00"

    @patch("apps.market_data.services.MarketDataService.get_historical_prices_by_ticker")
    def test_unknown_benchmark_returns_none(self, mock_hist):
        service = MarketDataService()
        result = service.get_benchmark_series("nasdaq", date(2025, 1, 1), date(2025, 1, 3))

        assert result is None
        mock_hist.assert_not_called()

    @patch("apps.market_data.services.MarketDataService.get_historical_prices_by_ticker")
    def test_empty_prices_returns_none(self, mock_hist):
        mock_hist.return_value = []
        service = MarketDataService()
        result = service.get_benchmark_series("sp500", date(2025, 1, 1), date(2025, 1, 3))

        assert result is None

    def test_benchmark_map_has_expected_keys(self):
        assert "sp500" in BENCHMARK_MAP
        assert "msci_world" in BENCHMARK_MAP
        assert BENCHMARK_MAP["sp500"]["ticker"] == "^GSPC"
        assert BENCHMARK_MAP["msci_world"]["ticker"] == "IWDA.AS"
```

- [ ] **Step 2: Run tests (expect failures — TDD red phase)**

```bash
cd backend && python -m pytest apps/market_data/tests/test_services.py -v -k "benchmark"
```

Expected: Tests fail because `get_benchmark_series`, `get_historical_prices_by_ticker`, and `BENCHMARK_MAP` don't exist yet.

- [ ] **Step 3: Add `BENCHMARK_MAP` and `get_benchmark_series()` to services.py**

Add the following to `backend/apps/market_data/services.py`:

After the existing imports, add:

```python
from django.core.cache import cache
```

After `CACHE_TTL`, add the benchmark map:

```python
BENCHMARK_MAP = {
    "sp500": {"ticker": "^GSPC", "name": "S&P 500"},
    "msci_world": {"ticker": "IWDA.AS", "name": "MSCI World"},
}

BENCHMARK_CACHE_TTL = 60 * 60 * 24  # 24 hours in seconds
```

Add to `MarketDataService` class, after the `get_ohlcv` method:

```python
    def get_historical_prices_by_ticker(self, ticker: str, start: date, end: date) -> list[PricePoint]:
        """Fetch historical prices by raw ticker string (no Instrument needed)."""
        return self.provider.get_historical_prices(ticker, start, end)

    def get_benchmark_series(
        self, benchmark: str, start: date, end: date
    ) -> list[dict] | None:
        """Return base-100 normalized daily series for a benchmark, or None if invalid."""
        if benchmark not in BENCHMARK_MAP:
            return None

        ticker = BENCHMARK_MAP[benchmark]["ticker"]
        cache_key = f"benchmark:{benchmark}:{start}:{end}"

        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            prices = self.get_historical_prices_by_ticker(ticker, start, end)
        except Exception:
            return None

        if not prices:
            return None

        base_price = prices[0].price
        series = [
            {
                "date": str(pp.date),
                "value": f"{(pp.price / base_price * 100):.2f}",
            }
            for pp in prices
        ]

        cache.set(cache_key, series, BENCHMARK_CACHE_TTL)
        return series
```

- [ ] **Step 4: Run tests (expect pass — TDD green phase)**

```bash
cd backend && python -m pytest apps/market_data/tests/test_services.py -v -k "benchmark"
```

Expected: All benchmark tests pass.

- [ ] **Step 5: Run full backend test suite**

```bash
cd backend && python -m pytest
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/market_data/services.py backend/apps/market_data/tests/test_services.py
git commit -m "feat: add get_benchmark_series with base-100 normalization and 24h cache"
```

---

### Task 2: Add benchmark support to PortfolioPerformanceView

**Files:**
- Modify: `backend/apps/portfolios/views.py`
- Modify: `backend/apps/portfolios/tests/test_analytics.py`

- [ ] **Step 1: Write tests for benchmark in performance endpoint**

Add the following tests to `TestPortfolioAnalytics` in `backend/apps/portfolios/tests/test_analytics.py`:

```python
    @patch("apps.portfolios.views.MarketDataService")
    def test_performance_with_benchmark(self, MockService):
        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("75.50"),
            fee=Decimal("0"),
            date=date(2025, 1, 1),
            broker_source="degiro",
            broker_reference="ref2",
        )
        MockService.return_value.get_historical_prices.return_value = [
            PricePoint(date=date(2025, 1, 1), price=Decimal("75.50")),
            PricePoint(date=date(2025, 1, 2), price=Decimal("76.00")),
        ]
        MockService.return_value.get_benchmark_series.return_value = [
            {"date": "2025-01-01", "value": "100.00"},
            {"date": "2025-01-02", "value": "101.00"},
        ]
        resp = self.client.get(
            f"/api/portfolios/{self.portfolio.id}/performance/?period=1W&benchmark=sp500"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["benchmark_series"] is not None
        assert len(resp.data["benchmark_series"]) == 2
        assert resp.data["benchmark_name"] == "S&P 500"
        # Portfolio series should also be normalized to base-100
        assert resp.data["series"][0]["value"] == "100.00"

    @patch("apps.portfolios.views.MarketDataService")
    def test_performance_without_benchmark(self, MockService):
        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("75.50"),
            fee=Decimal("0"),
            date=date(2025, 1, 1),
            broker_source="degiro",
            broker_reference="ref3",
        )
        MockService.return_value.get_historical_prices.return_value = [
            PricePoint(date=date(2025, 1, 1), price=Decimal("75.50")),
            PricePoint(date=date(2025, 1, 2), price=Decimal("76.00")),
        ]
        resp = self.client.get(
            f"/api/portfolios/{self.portfolio.id}/performance/?period=1W"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["benchmark_series"] is None
        assert resp.data["benchmark_name"] is None
        # Without benchmark, series should still be raw values (not normalized)
        assert resp.data["series"][0]["value"] == "755.00"

    @patch("apps.portfolios.views.MarketDataService")
    def test_performance_invalid_benchmark_ignored(self, MockService):
        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("75.50"),
            fee=Decimal("0"),
            date=date(2025, 1, 1),
            broker_source="degiro",
            broker_reference="ref4",
        )
        MockService.return_value.get_historical_prices.return_value = [
            PricePoint(date=date(2025, 1, 1), price=Decimal("75.50")),
        ]
        MockService.return_value.get_benchmark_series.return_value = None
        resp = self.client.get(
            f"/api/portfolios/{self.portfolio.id}/performance/?period=1W&benchmark=invalid"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["benchmark_series"] is None
        assert resp.data["benchmark_name"] is None
```

- [ ] **Step 2: Run tests (expect failures — TDD red phase)**

```bash
cd backend && python -m pytest apps/portfolios/tests/test_analytics.py -v -k "benchmark"
```

Expected: Tests fail because the view doesn't return `benchmark_series` or `benchmark_name` yet.

- [ ] **Step 3: Modify `PortfolioPerformanceView` in views.py**

Add the following import at the top of `backend/apps/portfolios/views.py`:

```python
from apps.market_data.services import BENCHMARK_MAP
```

(Add `BENCHMARK_MAP` to the existing import from `apps.market_data.services`.)

Replace the return statement in `PortfolioPerformanceView.get()` (the last line, `return Response({"series": series})`) with:

```python
        # Handle benchmark
        benchmark_key = request.query_params.get("benchmark")
        benchmark_series = None
        benchmark_name = None

        if benchmark_key:
            benchmark_series = service.get_benchmark_series(benchmark_key, start, end)
            if benchmark_series:
                benchmark_name = BENCHMARK_MAP[benchmark_key]["name"]

        # When a benchmark is selected, normalize portfolio series to base-100 too
        if benchmark_series and series:
            base_value = Decimal(series[0]["value"])
            if base_value > 0:
                series = [
                    {
                        "date": point["date"],
                        "value": f"{(Decimal(point['value']) / base_value * 100):.2f}",
                    }
                    for point in series
                ]

        return Response({
            "series": series,
            "benchmark_series": benchmark_series,
            "benchmark_name": benchmark_name,
        })
```

- [ ] **Step 4: Run tests (expect pass — TDD green phase)**

```bash
cd backend && python -m pytest apps/portfolios/tests/test_analytics.py -v -k "benchmark"
```

Expected: All benchmark tests pass.

- [ ] **Step 5: Run full backend test suite**

```bash
cd backend && python -m pytest
```

Expected: All tests pass. Note: the existing `test_performance` test will need its assertion updated since the response now includes `benchmark_series` and `benchmark_name` keys. Update the existing test to also check:

```python
        assert resp.data["benchmark_series"] is None
        assert resp.data["benchmark_name"] is None
```

- [ ] **Step 6: Commit**

```bash
git add backend/apps/portfolios/views.py backend/apps/portfolios/tests/test_analytics.py
git commit -m "feat: add benchmark query param to performance endpoint with base-100 normalization"
```

---

### Task 3: Add `benchmark_return_pct` to PortfolioSummaryView

**Files:**
- Modify: `backend/apps/portfolios/views.py`
- Modify: `backend/apps/portfolios/tests/test_analytics.py`

- [ ] **Step 1: Write test for benchmark return in summary**

Add the following test to `TestPortfolioAnalytics` in `backend/apps/portfolios/tests/test_analytics.py`:

```python
    @patch("apps.portfolios.views.MarketDataService")
    def test_summary_with_benchmark(self, MockService):
        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=self.inst,
            type=TransactionType.BUY,
            quantity=Decimal("10"),
            price=Decimal("75.50"),
            fee=Decimal("0"),
            date=date(2025, 1, 1),
            broker_source="degiro",
            broker_reference="ref5",
        )
        MockService.return_value.get_current_price.return_value = PriceResult(
            price=Decimal("80.00"),
            currency="EUR",
        )
        MockService.return_value.get_benchmark_series.return_value = [
            {"date": "2025-01-01", "value": "100.00"},
            {"date": "2026-03-19", "value": "112.50"},
        ]
        resp = self.client.get(
            f"/api/portfolios/{self.portfolio.id}/summary/?benchmark=sp500"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["benchmark_return_pct"] == "12.50"

    @patch("apps.portfolios.views.MarketDataService")
    def test_summary_without_benchmark(self, MockService):
        MockService.return_value.get_current_price.return_value = PriceResult(
            price=Decimal("80.00"),
            currency="EUR",
        )
        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/summary/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["benchmark_return_pct"] is None
```

- [ ] **Step 2: Run tests (expect failures — TDD red phase)**

```bash
cd backend && python -m pytest apps/portfolios/tests/test_analytics.py -v -k "summary"
```

- [ ] **Step 3: Modify `PortfolioSummaryView` in views.py**

In the `PortfolioSummaryView.get()` method, add benchmark logic before the return statement. Replace the return block with:

```python
        # Benchmark return
        benchmark_key = request.query_params.get("benchmark")
        benchmark_return_pct = None

        if benchmark_key and first_tx:
            benchmark_series = service.get_benchmark_series(
                benchmark_key, first_tx, date.today()
            )
            if benchmark_series and len(benchmark_series) >= 2:
                start_val = Decimal(benchmark_series[0]["value"])
                end_val = Decimal(benchmark_series[-1]["value"])
                if start_val > 0:
                    benchmark_return_pct = f"{((end_val - start_val) / start_val * 100):.2f}"

        return Response(
            {
                "total_value": f"{total_value:.2f}",
                "total_cost": f"{total_cost:.2f}",
                "total_gain_loss": f"{total_value - total_cost:.2f}",
                "total_return_pct": f"{((total_value - total_cost) / total_cost * 100):.2f}" if total_cost else "0.00",
                "first_transaction_date": str(first_tx) if first_tx else None,
                "benchmark_return_pct": benchmark_return_pct,
            }
        )
```

- [ ] **Step 4: Run tests (expect pass — TDD green phase)**

```bash
cd backend && python -m pytest apps/portfolios/tests/test_analytics.py -v -k "summary"
```

Expected: All summary tests pass.

- [ ] **Step 5: Run full backend test suite and lint**

```bash
cd backend && python -m pytest && python -m ruff check .
```

Expected: All tests pass, no lint errors.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/portfolios/views.py backend/apps/portfolios/tests/test_analytics.py
git commit -m "feat: add benchmark_return_pct to portfolio summary endpoint"
```

---

### Task 4: Update frontend types and API client

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/lib/api/portfolios.ts`

- [ ] **Step 1: Update `PerformanceSeries` type**

In `frontend/src/types/api.ts`, replace the `PerformanceSeries` interface:

```typescript
export interface PerformanceSeries {
  series: { date: string; value: string }[];
  benchmark_series: { date: string; value: string }[] | null;
  benchmark_name: string | null;
}
```

- [ ] **Step 2: Update `PortfolioSummary` type**

In `frontend/src/types/api.ts`, add `benchmark_return_pct` to the `PortfolioSummary` interface:

```typescript
export interface PortfolioSummary {
  total_value: string;
  total_cost: string;
  total_gain_loss: string;
  total_return_pct: string;
  first_transaction_date: string | null;
  benchmark_return_pct: string | null;
}
```

- [ ] **Step 3: Update `getPerformance` to accept benchmark param**

In `frontend/src/lib/api/portfolios.ts`, replace the `getPerformance` function:

```typescript
export async function getPerformance(portfolioId: number, period: string, benchmark?: string) {
  const params = new URLSearchParams({ period });
  if (benchmark) params.set("benchmark", benchmark);
  return apiClient<PerformanceSeries>(`/portfolios/${portfolioId}/performance/?${params.toString()}`);
}
```

- [ ] **Step 4: Update `getSummary` to accept benchmark param**

In `frontend/src/lib/api/portfolios.ts`, replace the `getSummary` function:

```typescript
export async function getSummary(portfolioId: number, benchmark?: string) {
  const params = benchmark ? `?benchmark=${benchmark}` : "";
  return apiClient<PortfolioSummary>(`/portfolios/${portfolioId}/summary/${params}`);
}
```

- [ ] **Step 5: Verify frontend build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds. Type errors may appear in consuming components that don't yet pass the new params — those are fixed in Tasks 5 and 6.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/lib/api/portfolios.ts
git commit -m "feat: update frontend types and API client for benchmark support"
```

---

### Task 5: Add benchmark selector and overlay to performance page

**Files:**
- Modify: `frontend/src/app/(app)/performance/page.tsx`

- [ ] **Step 1: Add benchmark state and selector dropdown**

Add imports at the top of `frontend/src/app/(app)/performance/page.tsx`:

```typescript
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
```

Add the benchmark options constant after `PERIODS`:

```typescript
const BENCHMARKS = [
  { value: "none", label: "No benchmark" },
  { value: "msci_world", label: "MSCI World" },
  { value: "sp500", label: "S&P 500" },
] as const;
```

Inside `PerformancePage`, add state after the `period` state:

```typescript
const [benchmark, setBenchmark] = useState<string>("none");
```

Update the `useQuery` call to pass the benchmark:

```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ["performance", selected?.id, period, benchmark],
  queryFn: () =>
    getPerformance(
      selected!.id,
      period,
      benchmark !== "none" ? benchmark : undefined
    ),
  enabled: !!selected,
});
```

- [ ] **Step 2: Add the selector UI and alpha display**

Add the benchmark selector next to the period toggles. Replace the `<div className="flex gap-2">` block containing the period buttons with:

```tsx
      <div className="flex items-center gap-4">
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
        <Select value={benchmark} onValueChange={setBenchmark}>
          <SelectTrigger className="w-[180px] h-8 text-sm">
            <SelectValue placeholder="Benchmark" />
          </SelectTrigger>
          <SelectContent>
            {BENCHMARKS.map((b) => (
              <SelectItem key={b.value} value={b.value}>
                {b.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
```

- [ ] **Step 3: Build the merged chart data with benchmark overlay**

Replace the `series` data mapping (the `const series = ...` block) with:

```typescript
  const series =
    data?.series.map((p, i) => ({
      date: p.date,
      value: parseFloat(p.value),
      benchmark: data.benchmark_series?.[i]
        ? parseFloat(data.benchmark_series[i].value)
        : undefined,
    })) ?? [];

  const benchmarkName = data?.benchmark_name;

  // Calculate alpha when benchmark is active
  const alpha =
    series.length >= 2 && benchmarkName
      ? series[series.length - 1].value -
        series[0].value -
        ((series[series.length - 1].benchmark ?? series[0].value) -
          (series[0].benchmark ?? series[0].value))
      : null;
```

- [ ] **Step 4: Add the benchmark line to the chart**

Inside the `<LineChart>` component, after the existing `<Line>` element for portfolio value, add:

```tsx
                {benchmarkName && (
                  <Line
                    type="monotone"
                    dataKey="benchmark"
                    stroke="#9ca3af"
                    strokeWidth={1.5}
                    strokeDasharray="6 3"
                    dot={false}
                    name={benchmarkName}
                  />
                )}
```

Update the `<Tooltip>` formatter to handle both lines:

```tsx
                <Tooltip
                  formatter={(value: number, name: string) => [
                    Number(value).toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    }),
                    name === "benchmark" ? benchmarkName : "Portfolio",
                  ]}
                  labelFormatter={(label) =>
                    new Date(String(label)).toLocaleDateString()
                  }
                />
```

- [ ] **Step 5: Show alpha below the chart card when benchmark is active**

After the chart `</Card>`, add:

```tsx
      {benchmarkName && alpha !== null && (
        <Card>
          <CardHeader>
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Alpha vs {benchmarkName}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p
              className={`text-2xl font-bold ${
                alpha >= 0
                  ? "text-green-600 dark:text-green-400"
                  : "text-red-600 dark:text-red-400"
              }`}
            >
              {alpha >= 0 ? "+" : ""}
              {alpha.toFixed(2)} pts
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Portfolio return minus benchmark return (base-100 normalized)
            </p>
          </CardContent>
        </Card>
      )}
```

- [ ] **Step 6: Update the YAxis label when benchmark is active**

When a benchmark is selected the chart shows base-100 normalized values, not currency. Update the YAxis `tickFormatter`:

```tsx
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v: number) =>
                    benchmarkName ? v.toFixed(0) : v.toLocaleString()
                  }
                />
```

- [ ] **Step 7: Verify frontend build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/app/(app)/performance/page.tsx
git commit -m "feat: add benchmark selector and overlay line to performance chart"
```

---

### Task 6: Show alpha on dashboard

**Files:**
- Modify: `frontend/src/app/(app)/dashboard/page.tsx`

- [ ] **Step 1: Add benchmark state and pass to API calls**

In `frontend/src/app/(app)/dashboard/page.tsx`, add state for the benchmark after the `period` state:

```typescript
const [benchmark, setBenchmark] = useState<string>("sp500");
```

Update the `getSummary` query to pass the benchmark:

```typescript
  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError,
  } = useQuery({
    queryKey: ["summary", selected?.id, benchmark],
    queryFn: () => getSummary(selected!.id, benchmark !== "none" ? benchmark : undefined),
    enabled: !!selected,
  });
```

- [ ] **Step 2: Derive alpha value from summary data**

In the derived values section, add:

```typescript
  const benchmarkReturnPct = summary?.benchmark_return_pct
    ? parseFloat(summary.benchmark_return_pct)
    : null;
  const alphaPct =
    benchmarkReturnPct !== null ? returnPct - benchmarkReturnPct : null;
```

- [ ] **Step 3: Display alpha in the Overall Gain/Loss card**

In the "Overall Gain/Loss" card, after the `{sinceLabel && ...}` block and before the closing `</CardContent>`, add:

```tsx
            {alphaPct !== null && (
              <div className="mt-2 pt-2 border-t">
                <p className={labelClasses}>Alpha vs S&P 500</p>
                <p
                  className={`text-sm font-semibold mt-0.5 ${colorClasses(alphaPct >= 0)}`}
                >
                  {alphaPct >= 0 ? "+" : ""}
                  {alphaPct.toFixed(2)}%
                </p>
              </div>
            )}
```

- [ ] **Step 4: Verify frontend build and lint**

```bash
cd frontend && npm run build && npx eslint src/
```

Expected: Build succeeds, no lint errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/(app)/dashboard/page.tsx
git commit -m "feat: show alpha vs benchmark on dashboard"
```

---

### Task 7: Final verification

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && python -m pytest
```

Expected: All tests pass.

- [ ] **Step 2: Run backend linter**

```bash
cd backend && python -m ruff check .
```

Expected: No errors.

- [ ] **Step 3: Run frontend tests**

```bash
cd frontend && npm test
```

Expected: All tests pass.

- [ ] **Step 4: Run frontend linter**

```bash
cd frontend && npx eslint src/
```

Expected: No errors.

- [ ] **Step 5: Run frontend production build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.
