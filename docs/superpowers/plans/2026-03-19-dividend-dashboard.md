# Dividend Dashboard Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated dividends page showing income history, yield metrics, income by instrument, and recent payments.

**Architecture:** New backend APIView aggregates DIVIDEND transactions into summary metrics, monthly history, per-instrument breakdown, and recent payments. New frontend page renders summary cards, a Recharts bar chart, an income-by-instrument table, and a recent payments list. Sidebar gets a new "Dividends" nav item.

**Tech Stack:** Django REST Framework, Next.js 16 App Router, React 19, Recharts, TanStack Query v5, Tailwind v4, shadcn/ui

---

## File Structure

### Backend (modify)
- `backend/apps/portfolios/views.py` -- Add `PortfolioDividendView`
- `backend/apps/portfolios/urls.py` -- Add dividends URL pattern

### Backend (create)
- `backend/apps/portfolios/tests/test_dividends.py` -- Tests for the dividends endpoint

### Frontend (create)
- `frontend/src/app/(app)/dividends/page.tsx` -- Dividends page component
- `frontend/src/__tests__/dividends-page.test.tsx` -- Frontend tests for dividends page

### Frontend (modify)
- `frontend/src/types/api.ts` -- Add dividend response types
- `frontend/src/lib/api/portfolios.ts` -- Add `getDividends` API function
- `frontend/src/components/layout/sidebar.tsx` -- Add "Dividends" nav item

---

## Chunk 1: Backend

### Task 1: Dividends API Endpoint

**Files:**
- Create: `backend/apps/portfolios/tests/test_dividends.py`
- Modify: `backend/apps/portfolios/views.py`
- Modify: `backend/apps/portfolios/urls.py`

- [ ] **Step 1: Write failing tests for the dividends endpoint**

```python
# backend/apps/portfolios/tests/test_dividends.py
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.instruments.models import Instrument
from apps.market_data.providers.base import PriceResult
from apps.portfolios.models import Holding, Portfolio, Transaction, TransactionType
from apps.users.models import User


@pytest.mark.django_db
class TestPortfolioDividendView:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.portfolio = Portfolio.objects.create(user=self.user, name="Main")
        self.aapl = Instrument.objects.create(
            isin="US0378331005",
            ticker="AAPL",
            name="Apple Inc",
            currency="USD",
            asset_type="STOCK",
        )
        self.msft = Instrument.objects.create(
            isin="US5949181045",
            ticker="MSFT",
            name="Microsoft Corp",
            currency="USD",
            asset_type="STOCK",
        )
        self.etf = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="iShares MSCI World",
            currency="EUR",
            asset_type="ETF",
        )
        # Holdings: AAPL and MSFT have holdings, ETF has a holding but no dividends
        Holding.objects.create(
            portfolio=self.portfolio,
            instrument=self.aapl,
            quantity=Decimal("10"),
            avg_buy_price=Decimal("150.00"),
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            instrument=self.msft,
            quantity=Decimal("5"),
            avg_buy_price=Decimal("300.00"),
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            instrument=self.etf,
            quantity=Decimal("20"),
            avg_buy_price=Decimal("75.00"),
        )

    def _create_dividend(self, instrument, amount, tx_date, ref):
        """Helper: create a DIVIDEND transaction. quantity=1, price=amount."""
        Transaction.objects.create(
            portfolio=self.portfolio,
            instrument=instrument,
            type=TransactionType.DIVIDEND,
            quantity=Decimal("1"),
            price=Decimal(str(amount)),
            fee=Decimal("0"),
            date=tx_date,
            broker_source="manual",
            broker_reference=ref,
        )

    @patch("apps.portfolios.views.MarketDataService")
    def test_dividends_summary(self, MockService):
        """Summary metrics are computed correctly."""
        MockService.return_value.get_current_price.return_value = PriceResult(
            price=Decimal("160.00"), currency="USD"
        )
        today = date.today()
        # Recent dividends (within 12 months)
        self._create_dividend(self.aapl, "25.00", today - timedelta(days=30), "d1")
        self._create_dividend(self.aapl, "25.00", today - timedelta(days=120), "d2")
        self._create_dividend(self.msft, "15.00", today - timedelta(days=60), "d3")
        # Old dividend (outside 12 months)
        self._create_dividend(self.aapl, "20.00", today - timedelta(days=400), "d4")

        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_200_OK

        summary = resp.data["summary"]
        assert summary["total_dividends_12m"] == "65.00"
        assert summary["total_dividends_all_time"] == "85.00"
        assert summary["monthly_average_12m"] == "5.42"  # 65 / 12
        assert summary["dividend_holding_count"] == 2  # AAPL and MSFT
        assert summary["total_holding_count"] == 3

    @patch("apps.portfolios.views.MarketDataService")
    def test_dividends_trailing_yield(self, MockService):
        """Trailing yield = total_12m / portfolio_value * 100."""
        # Portfolio value: AAPL 10*160=1600 + MSFT 5*300=1500 + ETF 20*80=1600 = 4700
        MockService.return_value.get_current_price.side_effect = [
            PriceResult(price=Decimal("160.00"), currency="USD"),
            PriceResult(price=Decimal("300.00"), currency="USD"),
            PriceResult(price=Decimal("80.00"), currency="EUR"),
        ]
        today = date.today()
        self._create_dividend(self.aapl, "100.00", today - timedelta(days=30), "d1")

        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_200_OK
        # yield = 100 / 4700 * 100 = 2.13
        assert resp.data["summary"]["trailing_yield_pct"] == "2.13"

    @patch("apps.portfolios.views.MarketDataService")
    def test_dividends_monthly_history(self, MockService):
        """Monthly history returns 24 months, fills gaps with 0.00."""
        MockService.return_value.get_current_price.return_value = PriceResult(
            price=Decimal("160.00"), currency="USD"
        )
        today = date.today()
        self._create_dividend(self.aapl, "25.00", today.replace(day=15), "d1")

        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_200_OK

        history = resp.data["monthly_history"]
        assert len(history) == 24
        # Most recent month first
        current_month = today.strftime("%Y-%m")
        assert history[0]["month"] == current_month
        assert history[0]["amount"] == "25.00"
        # Other months should be 0.00
        assert history[1]["amount"] == "0.00"

    @patch("apps.portfolios.views.MarketDataService")
    def test_dividends_by_instrument(self, MockService):
        """By-instrument breakdown sorted by 12m total descending."""
        MockService.return_value.get_current_price.return_value = PriceResult(
            price=Decimal("160.00"), currency="USD"
        )
        today = date.today()
        self._create_dividend(self.aapl, "50.00", today - timedelta(days=30), "d1")
        self._create_dividend(self.aapl, "50.00", today - timedelta(days=120), "d2")
        self._create_dividend(self.msft, "30.00", today - timedelta(days=60), "d3")

        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_200_OK

        by_inst = resp.data["by_instrument"]
        assert len(by_inst) == 2
        # AAPL first (100 > 30)
        assert by_inst[0]["ticker"] == "AAPL"
        assert by_inst[0]["total_12m"] == "100.00"
        assert by_inst[0]["payment_count_12m"] == 2
        # MSFT second
        assert by_inst[1]["ticker"] == "MSFT"
        assert by_inst[1]["total_12m"] == "30.00"
        # Percentages
        assert by_inst[0]["pct_of_total"] == "76.9"  # 100/130*100
        assert by_inst[1]["pct_of_total"] == "23.1"  # 30/130*100

    @patch("apps.portfolios.views.MarketDataService")
    def test_dividends_recent_payments(self, MockService):
        """Recent payments returns last 10, newest first."""
        MockService.return_value.get_current_price.return_value = PriceResult(
            price=Decimal("160.00"), currency="USD"
        )
        today = date.today()
        for i in range(12):
            self._create_dividend(
                self.aapl, "10.00", today - timedelta(days=i * 30), f"d{i}"
            )

        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_200_OK

        recent = resp.data["recent_payments"]
        assert len(recent) == 10
        # Newest first
        assert recent[0]["date"] == str(today)
        assert recent[0]["instrument_name"] == "Apple Inc"
        assert recent[0]["ticker"] == "AAPL"
        assert recent[0]["amount"] == "10.00"

    def test_dividends_empty_portfolio(self):
        """No dividends returns zero summary and empty lists."""
        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["summary"]["total_dividends_12m"] == "0.00"
        assert resp.data["summary"]["total_dividends_all_time"] == "0.00"
        assert resp.data["summary"]["trailing_yield_pct"] == "0.00"
        assert resp.data["summary"]["monthly_average_12m"] == "0.00"
        assert resp.data["by_instrument"] == []
        assert resp.data["recent_payments"] == []

    def test_dividends_other_user_forbidden(self):
        """Cannot access another user's portfolio dividends."""
        other = User.objects.create_user(username="other", password="pass12345")
        other_portfolio = Portfolio.objects.create(user=other, name="Other")
        resp = self.client.get(f"/api/portfolios/{other_portfolio.id}/dividends/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest apps/portfolios/tests/test_dividends.py -v`
Expected: FAIL (PortfolioDividendView does not exist, URL not registered)

- [ ] **Step 3: Implement `PortfolioDividendView`**

Add to `backend/apps/portfolios/views.py`:

```python
# Add to imports at top (dateutil is not needed; use built-in)
from collections import defaultdict

# Add the view class after PortfolioAllocationView

class PortfolioDividendView(APIView):
    """Dividend income analytics: summary, monthly history, by instrument, recent payments."""

    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)

        today = date.today()
        twelve_months_ago = today - timedelta(days=365)

        # All dividend transactions for this portfolio
        all_dividends = (
            portfolio.transactions
            .filter(type=TransactionType.DIVIDEND)
            .select_related("instrument")
            .order_by("-date")
        )

        # Compute totals
        total_all_time = sum(
            (tx.quantity * tx.price for tx in all_dividends), Decimal("0")
        )
        dividends_12m = [tx for tx in all_dividends if tx.date >= twelve_months_ago]
        total_12m = sum(
            (tx.quantity * tx.price for tx in dividends_12m), Decimal("0")
        )
        monthly_avg = total_12m / 12 if total_12m else Decimal("0")

        # Trailing yield: total_12m / portfolio_value * 100
        holdings = portfolio.holdings.select_related("instrument").all()
        service = MarketDataService()
        portfolio_value = Decimal("0")
        for h in holdings:
            try:
                price_result = service.get_current_price(h.instrument)
                portfolio_value += h.quantity * price_result.price
            except Exception:
                portfolio_value += h.quantity * h.avg_buy_price

        trailing_yield = (
            (total_12m / portfolio_value * 100) if portfolio_value else Decimal("0")
        )

        # Dividend-paying holding count (instruments that paid dividends in 12m)
        dividend_instruments_12m = {tx.instrument_id for tx in dividends_12m}

        # --- Monthly history (last 24 months, newest first) ---
        monthly_totals = defaultdict(Decimal)
        for tx in all_dividends:
            month_key = tx.date.strftime("%Y-%m")
            monthly_totals[month_key] += tx.quantity * tx.price

        monthly_history = []
        cursor = today.replace(day=1)
        for _ in range(24):
            month_key = cursor.strftime("%Y-%m")
            monthly_history.append({
                "month": month_key,
                "amount": f"{monthly_totals.get(month_key, Decimal('0')):.2f}",
            })
            # Move to previous month
            cursor = (cursor - timedelta(days=1)).replace(day=1)

        # --- By instrument (12m, sorted by total desc) ---
        inst_totals = defaultdict(lambda: {"total": Decimal("0"), "count": 0, "instrument": None})
        for tx in dividends_12m:
            entry = inst_totals[tx.instrument_id]
            entry["total"] += tx.quantity * tx.price
            entry["count"] += 1
            entry["instrument"] = tx.instrument

        by_instrument = []
        for entry in sorted(inst_totals.values(), key=lambda e: -e["total"]):
            inst = entry["instrument"]
            pct = (entry["total"] / total_12m * 100) if total_12m else Decimal("0")
            by_instrument.append({
                "instrument_name": inst.name,
                "ticker": inst.ticker or "",
                "total_12m": f"{entry['total']:.2f}",
                "pct_of_total": f"{pct:.1f}",
                "payment_count_12m": entry["count"],
            })

        # --- Recent payments (last 10) ---
        recent_payments = []
        for tx in all_dividends[:10]:
            recent_payments.append({
                "date": str(tx.date),
                "instrument_name": tx.instrument.name,
                "ticker": tx.instrument.ticker or "",
                "amount": f"{tx.quantity * tx.price:.2f}",
            })

        return Response({
            "summary": {
                "total_dividends_12m": f"{total_12m:.2f}",
                "total_dividends_all_time": f"{total_all_time:.2f}",
                "trailing_yield_pct": f"{trailing_yield:.2f}",
                "monthly_average_12m": f"{monthly_avg:.2f}",
                "dividend_holding_count": len(dividend_instruments_12m),
                "total_holding_count": holdings.count(),
            },
            "monthly_history": monthly_history,
            "by_instrument": by_instrument,
            "recent_payments": recent_payments,
        })
```

- [ ] **Step 4: Register the URL**

In `backend/apps/portfolios/urls.py`, add the import and URL pattern:

```python
# Add PortfolioDividendView to the import from .views
from .views import (
    HoldingListView,
    PortfolioAdviceChatView,
    PortfolioAdviceView,
    PortfolioAllocationView,
    PortfolioDividendView,
    PortfolioFullAdviceView,
    PortfolioPerformanceView,
    PortfolioSummaryView,
    PortfolioViewSet,
    TransactionViewSet,
)

# Add to urlpatterns after the allocation entry:
    path("portfolios/<int:portfolio_id>/dividends/", PortfolioDividendView.as_view(), name="portfolio-dividends"),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest apps/portfolios/tests/test_dividends.py -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Run full backend test suite**

Run: `cd backend && python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 7: Lint**

Run: `cd backend && python -m ruff check .`
Expected: No errors

- [ ] **Step 8: Commit**

```bash
git add backend/apps/portfolios/views.py backend/apps/portfolios/urls.py backend/apps/portfolios/tests/test_dividends.py
git commit -m "feat: add portfolio dividends API endpoint with income analytics"
```

---

## Chunk 2: Frontend

### Task 2: Types and API Function

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/lib/api/portfolios.ts`

- [ ] **Step 1: Add dividend response types**

In `frontend/src/types/api.ts`, add at the end of the file:

```typescript
export interface DividendSummary {
  total_dividends_12m: string;
  total_dividends_all_time: string;
  trailing_yield_pct: string;
  monthly_average_12m: string;
  dividend_holding_count: number;
  total_holding_count: number;
}

export interface DividendMonthly {
  month: string;
  amount: string;
}

export interface DividendByInstrument {
  instrument_name: string;
  ticker: string;
  total_12m: string;
  pct_of_total: string;
  payment_count_12m: number;
}

export interface DividendPayment {
  date: string;
  instrument_name: string;
  ticker: string;
  amount: string;
}

export interface DividendResponse {
  summary: DividendSummary;
  monthly_history: DividendMonthly[];
  by_instrument: DividendByInstrument[];
  recent_payments: DividendPayment[];
}
```

- [ ] **Step 2: Add API function**

In `frontend/src/lib/api/portfolios.ts`, add the import and function:

```typescript
// Add DividendResponse to the import from "@/types/api"
import type {
  Portfolio, Holding, Transaction, PortfolioSummary,
  PerformanceSeries, AllocationItem, PaginatedResponse,
  AdviceResponse, FullAdviceResponse, DividendResponse,
} from "@/types/api";

// Add at the end of the file
export async function getDividends(portfolioId: number) {
  return apiClient<DividendResponse>(`/portfolios/${portfolioId}/dividends/`);
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/lib/api/portfolios.ts
git commit -m "feat: add dividend response types and API function"
```

---

### Task 3: Sidebar Navigation

**Files:**
- Modify: `frontend/src/components/layout/sidebar.tsx`

- [ ] **Step 1: Add Coins import and nav item**

In `frontend/src/components/layout/sidebar.tsx`:

1. Add `Coins` to the lucide-react import:

```typescript
import {
  LayoutDashboard,
  Briefcase,
  Coins,
  TrendingUp,
  PieChart,
  ArrowLeftRight,
  Upload,
  Sparkles,
  Settings,
  LogOut,
  Sun,
  Moon,
  Monitor,
  Plus,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
```

2. Add the "Dividends" entry to the `navItems` array, after "Holdings":

```typescript
const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/holdings", label: "Holdings", icon: Briefcase },
  { href: "/dividends", label: "Dividends", icon: Coins },
  { href: "/performance", label: "Performance", icon: TrendingUp },
  { href: "/allocation", label: "Allocation", icon: PieChart },
  { href: "/transactions", label: "Transactions", icon: ArrowLeftRight },
  { href: "/import", label: "Import", icon: Upload },
  { href: "/advice", label: "AI Advice", icon: Sparkles },
  { href: "/settings", label: "Settings", icon: Settings },
];
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/layout/sidebar.tsx
git commit -m "feat: add Dividends nav item to sidebar"
```

---

### Task 4: Dividends Page

**Files:**
- Create: `frontend/src/app/(app)/dividends/page.tsx`

- [ ] **Step 1: Create the dividends page**

```tsx
// frontend/src/app/(app)/dividends/page.tsx
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
                  formatter={(value: number) => [
                    `\u20AC${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                    "Income",
                  ]}
                  labelFormatter={(label: string) => {
                    const [y, m] = label.split("-");
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
```

- [ ] **Step 2: Verify frontend compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(app\)/dividends/page.tsx
git commit -m "feat: add dividends page with income chart, breakdown table, and recent payments"
```

---

### Task 5: Frontend Tests

**Files:**
- Create: `frontend/src/__tests__/dividends-page.test.tsx`

- [ ] **Step 1: Create page tests**

```tsx
// frontend/src/__tests__/dividends-page.test.tsx
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { usePortfolio } from "@/lib/portfolio-context";
import { getDividends } from "@/lib/api/portfolios";

jest.mock("@/lib/portfolio-context");
jest.mock("@/lib/api/portfolios");
// Mock recharts to avoid canvas issues in jsdom
jest.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}));

import DividendsPage from "@/app/(app)/dividends/page";

const mockPortfolio = { id: 1, name: "Main", created_at: "2025-01-01" };

const mockDividendData = {
  summary: {
    total_dividends_12m: "130.00",
    total_dividends_all_time: "200.00",
    trailing_yield_pct: "2.50",
    monthly_average_12m: "10.83",
    dividend_holding_count: 2,
    total_holding_count: 5,
  },
  monthly_history: Array.from({ length: 24 }, (_, i) => ({
    month: `2026-${String(3 - Math.floor(i / 1)).padStart(2, "0")}`,
    amount: i === 0 ? "50.00" : "0.00",
  })),
  by_instrument: [
    {
      instrument_name: "Apple Inc",
      ticker: "AAPL",
      total_12m: "100.00",
      pct_of_total: "76.9",
      payment_count_12m: 4,
    },
    {
      instrument_name: "Microsoft Corp",
      ticker: "MSFT",
      total_12m: "30.00",
      pct_of_total: "23.1",
      payment_count_12m: 2,
    },
  ],
  recent_payments: [
    { date: "2026-03-15", instrument_name: "Apple Inc", ticker: "AAPL", amount: "25.00" },
    { date: "2026-02-15", instrument_name: "Microsoft Corp", ticker: "MSFT", amount: "15.00" },
  ],
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe("DividendsPage", () => {
  beforeEach(() => jest.clearAllMocks());

  it("shows empty state when no portfolio is selected", () => {
    (usePortfolio as jest.Mock).mockReturnValue({ selected: null });
    renderWithProviders(<DividendsPage />);
    expect(screen.getByText("Select a portfolio to view dividend data.")).toBeInTheDocument();
  });

  it("renders summary cards with data", async () => {
    (usePortfolio as jest.Mock).mockReturnValue({ selected: mockPortfolio });
    (getDividends as jest.Mock).mockResolvedValue(mockDividendData);
    renderWithProviders(<DividendsPage />);

    expect(await screen.findByText("Income (12M)")).toBeInTheDocument();
    expect(screen.getByText("Trailing Yield")).toBeInTheDocument();
    expect(screen.getByText("Monthly Average")).toBeInTheDocument();
    expect(screen.getByText("Dividend Holdings")).toBeInTheDocument();
    expect(screen.getByText("2.50%")).toBeInTheDocument();
  });

  it("renders by-instrument table", async () => {
    (usePortfolio as jest.Mock).mockReturnValue({ selected: mockPortfolio });
    (getDividends as jest.Mock).mockResolvedValue(mockDividendData);
    renderWithProviders(<DividendsPage />);

    expect(await screen.findByText("Apple Inc")).toBeInTheDocument();
    expect(screen.getByText("Microsoft Corp")).toBeInTheDocument();
    expect(screen.getByText("76.9%")).toBeInTheDocument();
  });

  it("renders recent payments", async () => {
    (usePortfolio as jest.Mock).mockReturnValue({ selected: mockPortfolio });
    (getDividends as jest.Mock).mockResolvedValue(mockDividendData);
    renderWithProviders(<DividendsPage />);

    expect(await screen.findByText("2026-03-15")).toBeInTheDocument();
    expect(screen.getByText("2026-02-15")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests**

Run: `cd frontend && npm test -- --testPathPattern=dividends-page`
Expected: 4 tests PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/__tests__/dividends-page.test.tsx
git commit -m "test: add dividends page component tests"
```

---

### Task 6: Final Verification and Lint

**Files:** None (verification only)

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass

- [ ] **Step 2: Run backend lint**

Run: `cd backend && python -m ruff check .`
Expected: No lint errors

- [ ] **Step 3: Run frontend lint**

Run: `cd frontend && npx eslint src/`
Expected: No lint errors

- [ ] **Step 4: Run frontend tests**

Run: `cd frontend && npm test`
Expected: All tests pass

- [ ] **Step 5: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 6: Commit any lint fixes if needed**
