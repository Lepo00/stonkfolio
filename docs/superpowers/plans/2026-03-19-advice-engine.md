# Portfolio Advice Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the naive `PortfolioAdviceView` with a comprehensive 37-rule advice engine, structured as a two-tier system (fast rules served immediately, slow rules cached 24h and computed in the background).

**Architecture:** A standalone `AdviceEngine` class evaluates rules against a precomputed `AdviceContext` dataclass. Rules are plain methods grouped into fast (DB + cached prices) and slow (technicals, correlation, post-sale tracking). The API returns structured `AdviceItem` objects with a `has_pending_analysis` flag. The frontend renders items with category icons, priority colors, and a legal disclaimer.

**Tech Stack:** Django 5, DRF, Django cache framework (backend); Next.js 16, React 19, shadcn/ui, TanStack Query v5 (frontend)

**Spec:** `docs/specs/portfolio-advice-rules.md`

---

## File Structure

| File | Action | Task | Responsibility |
|------|--------|------|----------------|
| `backend/apps/portfolios/advice/__init__.py` | Create | A | Package init, exports `AdviceEngine` |
| `backend/apps/portfolios/advice/models.py` | Create | A | `AdviceItem`, `AdviceContext`, `AdviceResponse` dataclasses |
| `backend/apps/portfolios/advice/context.py` | Create | A | `build_advice_context()` — shared data computation |
| `backend/apps/portfolios/advice/engine.py` | Create | A | `AdviceEngine` class — orchestration, dedup, sort, limit, caching |
| `backend/apps/portfolios/advice/rules_fast.py` | Create | B | Fast-tier rule methods (RISK_001-006, DIV_*, PERF_*, INC_*, COST_*, BEHAV_001/003/005, HEALTH_*) |
| `backend/apps/portfolios/advice/rules_slow.py` | Create | B | Slow-tier rule methods (RISK_007, TECH_001-006, BEHAV_002, BEHAV_004) |
| `backend/apps/portfolios/advice/dedup.py` | Create | A | Deduplication logic (e.g. PERF_002 vs PERF_004) |
| `backend/apps/portfolios/views.py` | Modify | C | Replace `PortfolioAdviceView` with engine-backed view |
| `backend/apps/portfolios/serializers.py` | Modify | C | Add `AdviceItemSerializer`, `AdviceResponseSerializer` |
| `backend/apps/portfolios/tests/test_advice_engine.py` | Create | E | Unit tests for engine orchestration |
| `backend/apps/portfolios/tests/test_advice_rules.py` | Create | E | Unit tests for individual rules |
| `backend/apps/portfolios/tests/test_advice_api.py` | Create | E | Integration tests for the advice API endpoint |
| `frontend/src/types/api.ts` | Modify | D | Add `AdviceItem`, `AdviceResponse` types |
| `frontend/src/lib/api/portfolios.ts` | Modify | D | Update `getPortfolioAdvice` return type |
| `frontend/src/app/(app)/dashboard/page.tsx` | Modify | D | Rewrite advice card with structured rendering |

---

## Dependencies

```
Task A (Core)  ──┐
                  ├──> Task C (API) ──> Task E (Tests, API portion)
Task B (Rules) ──┘
                       Task D (Frontend) can run in parallel with B/C
Task E (Tests, unit portion) can start after Task A
```

---

### Task A: Backend Core — Advice Engine Architecture

**Files:**
- Create: `backend/apps/portfolios/advice/__init__.py`
- Create: `backend/apps/portfolios/advice/models.py`
- Create: `backend/apps/portfolios/advice/context.py`
- Create: `backend/apps/portfolios/advice/engine.py`
- Create: `backend/apps/portfolios/advice/dedup.py`

**Depends on:** Nothing
**Blocks:** Task C, Task E

---

- [ ] **Step 1: Create the advice package with `__init__.py`**

Create `backend/apps/portfolios/advice/__init__.py`:

```python
from .engine import AdviceEngine
from .models import AdviceItem, AdviceContext, AdviceResponse

__all__ = ["AdviceEngine", "AdviceItem", "AdviceContext", "AdviceResponse"]
```

---

- [ ] **Step 2: Define data models in `models.py`**

Create `backend/apps/portfolios/advice/models.py` with these dataclasses:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

@dataclass
class AdviceItem:
    rule_id: str                          # e.g. "RISK_001"
    category: str                         # risk | performance | diversification | cost | income | technical | behavioral | health
    priority: str                         # critical | warning | info | positive
    title: str
    message: str
    holdings: list[str] = field(default_factory=list)   # tickers of affected holdings
    metadata: dict = field(default_factory=dict)

@dataclass
class HoldingData:
    """Pre-computed holding data passed to every rule."""
    ticker: str
    name: str
    isin: str
    instrument_id: int
    quantity: Decimal
    avg_buy_price: Decimal
    current_price: Decimal | None         # None if pricing failed
    market_value: Decimal | None          # quantity * current_price, None if unpriced
    cost_basis: Decimal                   # quantity * avg_buy_price
    weight_pct: float | None              # % of total portfolio value
    return_pct: float | None              # unrealized gain/loss %
    sector: str
    country: str
    asset_type: str
    currency: str

@dataclass
class AdviceContext:
    """Shared pre-computed data for all rules. Built once, passed to every rule method."""
    # Portfolio basics
    portfolio_id: int
    holding_count: int
    holdings: list[HoldingData]
    unpriced_holdings: list[HoldingData]  # holdings where current_price is None

    # Aggregates
    total_value: Decimal                  # sum of market values (priced holdings only)
    total_cost: Decimal                   # sum of cost basis (all holdings)
    overall_return_pct: float

    # Allocation maps: {key: weight_pct}
    sector_weights: dict[str, float]
    country_weights: dict[str, float]
    currency_weights: dict[str, float]
    asset_type_weights: dict[str, float]

    # Transaction data (pre-fetched)
    all_transactions: list               # QuerySet result list of Transaction objects
    dividend_txs_12m: list               # DIVIDEND txs in last 12 months
    fee_total: Decimal                   # sum of all fees
    first_transaction_date: date | None
    last_trade_date: date | None         # most recent BUY or SELL

    # Performance series (may be None if insufficient data)
    perf_series: list | None             # list of (date, Decimal) tuples from PortfolioPerformanceView logic

@dataclass
class AdviceResponse:
    items: list[AdviceItem]
    has_pending_analysis: bool
    disclaimer: str
```

---

- [ ] **Step 3: Implement `build_advice_context()` in `context.py`**

Create `backend/apps/portfolios/advice/context.py`. This function takes a `Portfolio` instance and returns an `AdviceContext`:

```python
from datetime import date, timedelta
from decimal import Decimal
from apps.market_data.services import MarketDataService
from apps.portfolios.models import Portfolio, TransactionType
from .models import AdviceContext, HoldingData

DISCLAIMER = (
    "These insights are generated automatically for educational purposes only "
    "and do not constitute financial advice. Past performance does not guarantee "
    "future results. Always consult a qualified financial advisor before making "
    "investment decisions."
)

def build_advice_context(portfolio: Portfolio, service: MarketDataService | None = None) -> AdviceContext:
    ...
```

Key implementation details:
- Fetch all holdings with `select_related("instrument")`
- Call `service.get_current_price()` for each holding, catching exceptions to build `unpriced_holdings` list
- Compute `total_value`, `total_cost`, per-holding `weight_pct` and `return_pct`
- Build allocation dicts by grouping holdings on `sector`, `country`, `currency`, `asset_type`
- Fetch all transactions for the portfolio in one query: `portfolio.transactions.select_related("instrument").order_by("date")`
- Filter dividend txs (type=DIVIDEND, date >= today - 365)
- Sum fees: `sum(tx.fee for tx in all_txs) + sum(tx.quantity * tx.price for tx in all_txs if tx.type == TransactionType.FEE)`
- Find `first_transaction_date` and `last_trade_date` (most recent BUY or SELL)
- `perf_series` can be set to `None` here (expensive); it will be computed lazily only if rules need it

---

- [ ] **Step 4: Implement deduplication in `dedup.py`**

Create `backend/apps/portfolios/advice/dedup.py`:

```python
from .models import AdviceItem

# Map of (rule_id that gets dropped) -> (rule_id that supersedes it)
SUPERSEDE_MAP = {
    "PERF_002": "PERF_004",  # deep loser supersedes underperformer for same ticker
}

PRIORITY_ORDER = {"critical": 0, "warning": 1, "info": 2, "positive": 3}

def deduplicate(items: list[AdviceItem]) -> list[AdviceItem]:
    """Remove lower-severity duplicates for the same holding where rules overlap."""
    ...
```

Logic:
- Group items by affected tickers
- For each ticker, if both PERF_002 and PERF_004 fire, drop PERF_002
- Return the filtered list (general-purpose, extensible via `SUPERSEDE_MAP`)

---

- [ ] **Step 5: Implement `AdviceEngine` in `engine.py`**

Create `backend/apps/portfolios/advice/engine.py`:

```python
import logging
from django.core.cache import cache
from apps.portfolios.models import Portfolio
from apps.market_data.services import MarketDataService
from .models import AdviceContext, AdviceItem, AdviceResponse
from .context import build_advice_context, DISCLAIMER
from .dedup import deduplicate, PRIORITY_ORDER
from .rules_fast import FastRules
from .rules_slow import SlowRules

logger = logging.getLogger(__name__)

FAST_CACHE_TTL = 15 * 60       # 15 minutes
SLOW_CACHE_TTL = 24 * 60 * 60  # 24 hours
MAX_ITEMS = 10

class AdviceEngine:
    def __init__(self, portfolio: Portfolio, service: MarketDataService | None = None):
        self.portfolio = portfolio
        self.service = service or MarketDataService()

    def evaluate(self) -> AdviceResponse:
        """Main entry point. Returns fast-tier results immediately, flags if slow tier is pending."""
        ...

    def _get_fast_results(self, ctx: AdviceContext) -> list[AdviceItem]:
        """Evaluate all fast rules, cache result."""
        ...

    def _get_slow_results(self, ctx: AdviceContext) -> list[AdviceItem] | None:
        """Return cached slow results, or None if not yet computed."""
        ...

    def _trigger_slow_computation(self, ctx: AdviceContext) -> None:
        """Compute slow rules and store in cache. Called in a thread."""
        ...

    @staticmethod
    def _sort_and_limit(items: list[AdviceItem]) -> list[AdviceItem]:
        """Sort by priority, limit to MAX_ITEMS, ensure at least 1 positive if available."""
        ...
```

Key implementation details for `evaluate()`:
1. Build `AdviceContext` via `build_advice_context()`
2. Check fast cache (`advice:fast:{portfolio_id}`); if miss, run `FastRules(ctx).evaluate_all()`, cache result
3. Check slow cache (`advice:slow:{portfolio_id}`); if miss, set `has_pending_analysis = True` and spawn `_trigger_slow_computation` in a `threading.Thread(daemon=True)`
4. Merge fast + slow (if available), run `deduplicate()`, then `_sort_and_limit()`
5. Return `AdviceResponse(items=..., has_pending_analysis=..., disclaimer=DISCLAIMER)`

Key implementation details for `_sort_and_limit()`:
- Sort by `PRIORITY_ORDER[item.priority]`
- If list > MAX_ITEMS: take first 9, then scan remainder for the first `positive` item and append it as item 10
- If no positive was found, just take first 10

---

- [ ] **Step 6: Verify the module imports correctly**

```bash
cd backend && python -c "from apps.portfolios.advice.models import AdviceItem, AdviceContext, AdviceResponse; print('OK')"
```

---

- [ ] **Step 7: Commit**

```bash
git add backend/apps/portfolios/advice/
git commit -m "feat: add advice engine core — AdviceItem, AdviceContext, AdviceEngine, dedup"
```

---

### Task B: Backend Rules — Implement All 37 Rules

**Files:**
- Create: `backend/apps/portfolios/advice/rules_fast.py`
- Create: `backend/apps/portfolios/advice/rules_slow.py`

**Depends on:** Task A (needs `AdviceItem`, `AdviceContext`)
**Blocks:** Task C

---

- [ ] **Step 1: Create `rules_fast.py` with the `FastRules` class**

Create `backend/apps/portfolios/advice/rules_fast.py`. Each rule is a method that receives `self.ctx` (the `AdviceContext`) and returns `list[AdviceItem]`.

```python
from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from .models import AdviceContext, AdviceItem

class FastRules:
    def __init__(self, ctx: AdviceContext):
        self.ctx = ctx

    def evaluate_all(self) -> list[AdviceItem]:
        """Run all fast rules and collect results."""
        results: list[AdviceItem] = []
        for method_name in dir(self):
            if method_name.startswith("rule_"):
                results.extend(getattr(self, method_name)())
        return results

    # ── Risk Management (fast) ───────────────────────────
    def rule_risk_001(self) -> list[AdviceItem]: ...   # Single-Holding Concentration
    def rule_risk_002(self) -> list[AdviceItem]: ...   # Top-3 Concentration
    def rule_risk_003(self) -> list[AdviceItem]: ...   # Portfolio Volatility (needs perf_series)
    def rule_risk_004(self) -> list[AdviceItem]: ...   # Max Drawdown (needs perf_series)
    def rule_risk_005(self) -> list[AdviceItem]: ...   # Currency Exposure
    def rule_risk_006(self) -> list[AdviceItem]: ...   # Single-Country Exposure

    # ── Diversification ──────────────────────────────────
    def rule_div_001(self) -> list[AdviceItem]: ...    # Insufficient Holdings
    def rule_div_002(self) -> list[AdviceItem]: ...    # Sector Concentration
    def rule_div_003(self) -> list[AdviceItem]: ...    # Missing Sector Exposure
    def rule_div_004(self) -> list[AdviceItem]: ...    # Asset Class Imbalance
    def rule_div_005(self) -> list[AdviceItem]: ...    # Single-Geography

    # ── Performance ──────────────────────────────────────
    def rule_perf_001(self) -> list[AdviceItem]: ...   # Overall Return
    def rule_perf_002(self) -> list[AdviceItem]: ...   # Significant Underperformers
    def rule_perf_003(self) -> list[AdviceItem]: ...   # Strong Performers
    def rule_perf_004(self) -> list[AdviceItem]: ...   # Deep Losers (>50% loss)
    def rule_perf_005(self) -> list[AdviceItem]: ...   # Period Return (needs perf_series)
    def rule_perf_006(self) -> list[AdviceItem]: ...   # Best/Worst Summary

    # ── Income ───────────────────────────────────────────
    def rule_inc_001(self) -> list[AdviceItem]: ...    # Dividend Yield
    def rule_inc_002(self) -> list[AdviceItem]: ...    # Dividend Concentration
    def rule_inc_003(self) -> list[AdviceItem]: ...    # No Dividend Income

    # ── Cost ─────────────────────────────────────────────
    def rule_cost_001(self) -> list[AdviceItem]: ...   # Fee Drag
    def rule_cost_002(self) -> list[AdviceItem]: ...   # High-Fee Transactions
    def rule_cost_003(self) -> list[AdviceItem]: ...   # Tax-Loss Harvesting

    # ── Behavioral (fast subset) ─────────────────────────
    def rule_behav_001(self) -> list[AdviceItem]: ...  # Holding Losers Too Long
    def rule_behav_003(self) -> list[AdviceItem]: ...  # Overtrading
    def rule_behav_005(self) -> list[AdviceItem]: ...  # Rebalancing Nudge

    # ── Health ───────────────────────────────────────────
    def rule_health_001(self) -> list[AdviceItem]: ... # Negligible Positions
    def rule_health_002(self) -> list[AdviceItem]: ... # Stale Positions
    def rule_health_003(self) -> list[AdviceItem]: ... # Large Unrealized Gain
    def rule_health_004(self) -> list[AdviceItem]: ... # Portfolio Age
    def rule_health_005(self) -> list[AdviceItem]: ... # Unpriced Instruments
```

Implementation notes for specific rules:

**RISK_001** (Single-Holding Concentration):
- Iterate `ctx.holdings` where `h.weight_pct is not None`
- If `weight_pct >= 40`: priority = "critical", threshold = 40
- Elif `weight_pct >= 25`: priority = "warning", threshold = 25
- Use template from spec, interpolate `name`, `ticker`, `weight_pct`, `threshold`

**RISK_003 / RISK_004** (Volatility / Drawdown):
- These need the performance series. If `ctx.perf_series` is None, compute it lazily within the rule (call the same logic used by `PortfolioPerformanceView` but returning raw (date, Decimal) tuples). Cache the result on `ctx.perf_series` so RISK_004 and PERF_005 reuse it.
- Use pandas for the math: `pd.Series(values).pct_change().dropna().std() * sqrt(252) * 100`

**HEALTH_001** (Negligible Positions):
- If more than 3 negligible positions (< 1% weight), group them into a single AdviceItem listing all tickers

**COST_002** (High-Fee Transactions):
- Filter BUY/SELL txs where `fee / (quantity * price) > 0.03`, sort by fee_pct descending, take top 3

**BEHAV_001** (Disposition Effect):
- For each holding with `return_pct < -20`, find the most recent transaction for that instrument, check if it's a BUY older than 6 months

---

- [ ] **Step 2: Create `rules_slow.py` with the `SlowRules` class**

Create `backend/apps/portfolios/advice/rules_slow.py`:

```python
from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
import pandas as pd
from apps.market_data.services import MarketDataService
from apps.market_data.indicators import calculate_rsi, calculate_sma
from .models import AdviceContext, AdviceItem

class SlowRules:
    def __init__(self, ctx: AdviceContext, service: MarketDataService):
        self.ctx = ctx
        self.service = service

    def evaluate_all(self) -> list[AdviceItem]:
        """Run all slow rules."""
        results: list[AdviceItem] = []
        for method_name in dir(self):
            if method_name.startswith("rule_"):
                results.extend(getattr(self, method_name)())
        return results

    # ── Risk (slow) ──────────────────────────────────────
    def rule_risk_007(self) -> list[AdviceItem]: ...   # Correlated Holdings

    # ── Technical ────────────────────────────────────────
    def rule_tech_001(self) -> list[AdviceItem]: ...   # RSI Overbought
    def rule_tech_002(self) -> list[AdviceItem]: ...   # RSI Oversold
    def rule_tech_003(self) -> list[AdviceItem]: ...   # Golden Cross
    def rule_tech_004(self) -> list[AdviceItem]: ...   # Death Cross
    def rule_tech_005(self) -> list[AdviceItem]: ...   # Price Below SMA50
    def rule_tech_006(self) -> list[AdviceItem]: ...   # Portfolio Momentum Score

    # ── Behavioral (slow subset) ─────────────────────────
    def rule_behav_002(self) -> list[AdviceItem]: ...  # Selling Winners Too Early
    def rule_behav_004(self) -> list[AdviceItem]: ...  # Recency Bias
```

Implementation notes:

**RISK_007** (Correlated Holdings):
- Skip if < 3 holdings with tickers
- For each holding, call `service.get_ohlcv(instrument, "3mo", "1d")` and compute daily returns
- Compute all pairwise correlations, take the average
- Use `itertools.combinations` for pairs
- Wrap each `get_ohlcv` call in try/except; skip holdings that fail

**TECH_001-006** (Technical signals):
- Batch-fetch OHLCV data for all holdings with tickers (reuse data across TECH rules)
- Pre-compute RSI(14), SMA(20), SMA(50) for each holding using existing `calculate_rsi` and `calculate_sma` from `apps.market_data.indicators`
- Note: `calculate_sma` and `calculate_rsi` return `list[dict]` with `{time, value}` format — extract the `value` fields
- For TECH_003/004 (crossovers): compare SMA20 vs SMA50 at index [-1] and [-5] (or nearest available)
- For TECH_006 (portfolio momentum): compute weighted average RSI using holding weights

**BEHAV_002** (Selling Winners Too Early):
- Find SELL txs in last 6 months where sale was profitable (`price > avg_buy_price` at time of sale)
- For each such sale, call `service.get_current_price()` on the instrument
- If current price > sale price by > 15%, trigger
- Max 2 items

**BEHAV_004** (Recency Bias):
- Find BUY txs in last 30 days
- For each, need price 30 days before the buy date — call `service.get_historical_prices()` with a 30-day window ending at buy date
- If the instrument gained > 15% in the month prior to purchase, flag it
- Trigger only if >= 2 such buys

---

- [ ] **Step 3: Verify all rule methods exist and return correct types**

```bash
cd backend && python -c "
from apps.portfolios.advice.rules_fast import FastRules
from apps.portfolios.advice.rules_slow import SlowRules
fast_rules = [m for m in dir(FastRules) if m.startswith('rule_')]
slow_rules = [m for m in dir(SlowRules) if m.startswith('rule_')]
print(f'Fast rules: {len(fast_rules)}, Slow rules: {len(slow_rules)}')
assert len(fast_rules) + len(slow_rules) == 37, f'Expected 37, got {len(fast_rules) + len(slow_rules)}'
print('All 37 rules accounted for')
"
```

---

- [ ] **Step 4: Commit**

```bash
git add backend/apps/portfolios/advice/rules_fast.py backend/apps/portfolios/advice/rules_slow.py
git commit -m "feat: implement all 37 advice rules (fast + slow tiers)"
```

---

### Task C: Backend API — Wire Up the View

**Files:**
- Modify: `backend/apps/portfolios/views.py`
- Modify: `backend/apps/portfolios/serializers.py`

**Depends on:** Task A + Task B
**Blocks:** Nothing (frontend can code against the contract)

---

- [ ] **Step 1: Add serializers for the advice response**

In `backend/apps/portfolios/serializers.py`, add:

```python
from rest_framework import serializers

class AdviceItemSerializer(serializers.Serializer):
    rule_id = serializers.CharField()
    category = serializers.CharField()
    priority = serializers.CharField()
    title = serializers.CharField()
    message = serializers.CharField()
    holdings = serializers.ListField(child=serializers.CharField(), required=False)
    metadata = serializers.DictField(required=False)

class AdviceResponseSerializer(serializers.Serializer):
    items = AdviceItemSerializer(many=True)
    has_pending_analysis = serializers.BooleanField()
    disclaimer = serializers.CharField()
```

---

- [ ] **Step 2: Replace `PortfolioAdviceView` in `views.py`**

Replace the entire `PortfolioAdviceView` class in `backend/apps/portfolios/views.py`:

```python
class PortfolioAdviceView(APIView):
    """Structured portfolio advice powered by the rule-based advice engine."""

    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        holdings = portfolio.holdings.exists()

        if not holdings:
            return Response({
                "items": [],
                "has_pending_analysis": False,
                "disclaimer": DISCLAIMER,
            })

        engine = AdviceEngine(portfolio)
        response = engine.evaluate()

        return Response(AdviceResponseSerializer(response).data)
```

Add the necessary imports at the top of `views.py`:

```python
from .advice import AdviceEngine
from .advice.context import DISCLAIMER
from .serializers import AdviceResponseSerializer
```

---

- [ ] **Step 3: Verify the endpoint returns structured data**

```bash
cd backend && python -c "
from apps.portfolios.advice.models import AdviceResponse, AdviceItem
from apps.portfolios.serializers import AdviceResponseSerializer
resp = AdviceResponse(
    items=[AdviceItem(rule_id='RISK_001', category='risk', priority='critical', title='Test', message='Test msg', holdings=['AAPL'], metadata={'weight_pct': 45.0})],
    has_pending_analysis=True,
    disclaimer='Test disclaimer',
)
data = AdviceResponseSerializer(resp).data
assert 'items' in data and len(data['items']) == 1
assert data['has_pending_analysis'] is True
print('Serializer OK')
"
```

---

- [ ] **Step 4: Commit**

```bash
git add backend/apps/portfolios/views.py backend/apps/portfolios/serializers.py
git commit -m "feat: wire advice engine to PortfolioAdviceView with structured response"
```

---

### Task D: Frontend — Structured Advice Card

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/lib/api/portfolios.ts`
- Modify: `frontend/src/app/(app)/dashboard/page.tsx`

**Depends on:** Nothing (code against the API contract from Task C)
**Blocks:** Nothing

---

- [ ] **Step 1: Add TypeScript types for the advice response**

In `frontend/src/types/api.ts`, add:

```typescript
export interface AdviceItem {
  rule_id: string;
  category: "risk" | "performance" | "diversification" | "cost" | "income" | "technical" | "behavioral" | "health";
  priority: "critical" | "warning" | "info" | "positive";
  title: string;
  message: string;
  holdings: string[];
  metadata: Record<string, unknown>;
}

export interface AdviceResponse {
  items: AdviceItem[];
  has_pending_analysis: boolean;
  disclaimer: string;
}
```

---

- [ ] **Step 2: Update `getPortfolioAdvice` return type**

In `frontend/src/lib/api/portfolios.ts`, change:

```typescript
// Before:
export async function getPortfolioAdvice(portfolioId: number) {
  return apiClient<{ advice: string | string[] }>(`/portfolios/${portfolioId}/advice/`);
}

// After:
export async function getPortfolioAdvice(portfolioId: number) {
  return apiClient<AdviceResponse>(`/portfolios/${portfolioId}/advice/`);
}
```

Add `AdviceResponse` to the import from `@/types/api`.

---

- [ ] **Step 3: Rewrite the advice card in the dashboard**

Replace the "AI Portfolio Advice" `<Card>` block at the bottom of `frontend/src/app/(app)/dashboard/page.tsx`. The new version should:

**Category icons** (from lucide-react):
- `risk` -> `ShieldAlert`
- `performance` -> `TrendingUp`
- `diversification` -> `Layers`
- `cost` -> `BadgeDollarSign` (or `CircleDollarSign`)
- `income` -> `Banknote`
- `technical` -> `BarChart3`
- `behavioral` -> `Brain`
- `health` -> `HeartPulse`

**Priority colors** (Tailwind classes):
- `critical` -> `text-red-600 dark:text-red-400`, left border `border-l-red-500`
- `warning` -> `text-amber-600 dark:text-amber-400`, left border `border-l-amber-500`
- `info` -> `text-blue-600 dark:text-blue-400`, left border `border-l-blue-500`
- `positive` -> `text-green-600 dark:text-green-400`, left border `border-l-green-500`

**Layout:**
- Show up to 5 items by default
- If more than 5, show a "Show N more" toggle button that expands to show all
- Each item: left colored border (4px), category icon, title in bold, message below in muted text
- Keep it compact -- use `text-xs` for messages, `text-sm` for titles

**Pending analysis indicator:**
- If `has_pending_analysis` is true, show a subtle animated indicator (e.g. a small pulsing dot next to the header) and re-fetch after 10 seconds using TanStack Query's `refetchInterval`:

```typescript
const { data: adviceData, isLoading: adviceLoading } = useQuery({
  queryKey: ["portfolio-advice", selected?.id],
  queryFn: () => getPortfolioAdvice(selected!.id),
  enabled: !!selected,
  staleTime: 5 * 60 * 1000,
  refetchInterval: adviceData?.has_pending_analysis ? 10_000 : false,
});
```

**Disclaimer footer:**
- Render `adviceData.disclaimer` as a `text-[10px] text-muted-foreground/60 mt-3` paragraph at the bottom of the card

**Empty state:**
- If `items` is empty and `has_pending_analysis` is false: "No advice available."
- If `items` is empty and `has_pending_analysis` is true: show loading skeleton

---

- [ ] **Step 4: Verify the build passes**

```bash
cd frontend && npm run build
```

---

- [ ] **Step 5: Verify lint passes**

```bash
cd frontend && npx eslint src/
```

---

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/lib/api/portfolios.ts frontend/src/app/(app)/dashboard/page.tsx
git commit -m "feat: structured advice card with category icons, priority colors, and disclaimer"
```

---

### Task E: Tests — Comprehensive Advice Engine Test Suite

**Files:**
- Create: `backend/apps/portfolios/tests/test_advice_engine.py`
- Create: `backend/apps/portfolios/tests/test_advice_rules.py`
- Create: `backend/apps/portfolios/tests/test_advice_api.py`

**Depends on:** Task A (for engine tests), Task A+B (for rule tests), Task C (for API tests)

---

- [ ] **Step 1: Create `test_advice_engine.py` — engine orchestration tests**

Create `backend/apps/portfolios/tests/test_advice_engine.py`:

Test class: `TestAdviceEngine`

Tests to write:
- `test_empty_portfolio_returns_no_items` — portfolio with no holdings returns empty items list
- `test_sort_order_critical_first` — items are sorted critical > warning > info > positive
- `test_max_10_items` — never more than 10 items returned
- `test_at_least_one_positive_included` — if a positive rule fires, it appears in final output even if 10+ higher-priority items exist
- `test_dedup_perf002_vs_perf004` — holding triggering both PERF_002 and PERF_004 only keeps PERF_004
- `test_has_pending_analysis_true_when_slow_cache_empty` — first call with no slow cache sets flag
- `test_disclaimer_always_present` — disclaimer field is always in response

Pattern: Use `unittest.mock.patch` to mock `MarketDataService` and provide controlled `PriceResult` values. Create test fixtures with `Portfolio`, `Holding`, `Instrument`, `Transaction` objects.

Setup method pattern (reuse across test files):

```python
@pytest.mark.django_db
class TestAdviceEngine:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="testpass123")
        self.portfolio = Portfolio.objects.create(user=self.user, name="Test")
        self.inst_aapl = Instrument.objects.create(
            isin="US0378331005", ticker="AAPL", name="Apple Inc",
            currency="USD", sector="Technology", country="US", asset_type="STOCK",
        )
        self.inst_msft = Instrument.objects.create(
            isin="US5949181045", ticker="MSFT", name="Microsoft Corp",
            currency="USD", sector="Technology", country="US", asset_type="STOCK",
        )
        # Add more instruments for diversification tests
```

---

- [ ] **Step 2: Create `test_advice_rules.py` — individual rule unit tests**

Create `backend/apps/portfolios/tests/test_advice_rules.py`:

Test the rules by constructing `AdviceContext` objects directly (no DB needed for most) and calling individual rule methods. This is faster and more isolated.

Test classes organized by category:

```python
class TestRiskRules:
    def test_risk_001_critical_at_40pct(self): ...
    def test_risk_001_warning_at_25pct(self): ...
    def test_risk_001_no_trigger_below_25pct(self): ...
    def test_risk_002_top3_above_70pct(self): ...
    def test_risk_002_no_trigger_below_70pct(self): ...
    def test_risk_005_currency_above_40pct(self): ...
    def test_risk_005_eur_exempt(self): ...  # EUR is base currency, should not trigger
    def test_risk_006_country_above_60pct(self): ...

class TestDiversificationRules:
    def test_div_001_warning_under_5(self): ...
    def test_div_001_info_under_10(self): ...
    def test_div_001_no_trigger_at_10(self): ...
    def test_div_002_critical_at_60pct(self): ...
    def test_div_002_warning_at_40pct(self): ...
    def test_div_003_few_sectors_many_holdings(self): ...
    def test_div_004_all_stocks(self): ...
    def test_div_005_single_country(self): ...

class TestPerformanceRules:
    def test_perf_001_positive_return(self): ...
    def test_perf_001_negative_return(self): ...
    def test_perf_002_loss_above_20pct(self): ...
    def test_perf_002_loss_10_to_20pct(self): ...
    def test_perf_003_gain_above_25pct(self): ...
    def test_perf_004_deep_loser_above_50pct(self): ...
    def test_perf_004_recovery_needed_pct_correct(self): ...
    def test_perf_006_best_worst_spread(self): ...

class TestIncomeRules:
    def test_inc_001_yield_above_3pct(self): ...
    def test_inc_002_concentration_above_50pct(self): ...
    def test_inc_003_no_dividends(self): ...

class TestCostRules:
    def test_cost_001_fee_ratio_above_2pct(self): ...
    def test_cost_002_high_fee_transaction(self): ...
    def test_cost_002_max_3_items(self): ...
    def test_cost_003_tax_loss_opportunity(self): ...

class TestBehavioralRules:
    def test_behav_001_holding_loser_6_months(self): ...
    def test_behav_003_overtrading_20_txs(self): ...
    def test_behav_003_round_tripping(self): ...
    def test_behav_005_rebalancing_nudge(self): ...

class TestHealthRules:
    def test_health_001_negligible_single(self): ...
    def test_health_001_negligible_grouped(self): ...  # >3 negligible -> single item
    def test_health_002_stale_position(self): ...
    def test_health_003_large_gain_high_weight(self): ...
    def test_health_004_young_portfolio(self): ...
    def test_health_005_unpriced_instruments(self): ...
```

Pattern for constructing test contexts directly:

```python
def _make_context(**overrides) -> AdviceContext:
    """Helper to build an AdviceContext with sensible defaults, overridden by kwargs."""
    defaults = {
        "portfolio_id": 1,
        "holding_count": 0,
        "holdings": [],
        "unpriced_holdings": [],
        "total_value": Decimal("10000"),
        "total_cost": Decimal("9000"),
        "overall_return_pct": 11.1,
        "sector_weights": {},
        "country_weights": {},
        "currency_weights": {},
        "asset_type_weights": {},
        "all_transactions": [],
        "dividend_txs_12m": [],
        "fee_total": Decimal("0"),
        "first_transaction_date": None,
        "last_trade_date": None,
        "perf_series": None,
    }
    defaults.update(overrides)
    return AdviceContext(**defaults)

def _make_holding(**overrides) -> HoldingData:
    """Helper to build a HoldingData with sensible defaults."""
    defaults = {
        "ticker": "AAPL", "name": "Apple", "isin": "US0378331005",
        "instrument_id": 1, "quantity": Decimal("10"),
        "avg_buy_price": Decimal("150"), "current_price": Decimal("160"),
        "market_value": Decimal("1600"), "cost_basis": Decimal("1500"),
        "weight_pct": 16.0, "return_pct": 6.67,
        "sector": "Technology", "country": "US",
        "asset_type": "STOCK", "currency": "USD",
    }
    defaults.update(overrides)
    return HoldingData(**defaults)
```

---

- [ ] **Step 3: Create `test_advice_api.py` — endpoint integration tests**

Create `backend/apps/portfolios/tests/test_advice_api.py`:

```python
@pytest.mark.django_db
class TestAdviceAPI:
    def setup_method(self):
        # Create user, portfolio, holdings, transactions
        ...

    @patch("apps.portfolios.advice.context.MarketDataService")
    def test_advice_returns_structured_response(self, MockService): ...
        # Assert response has keys: items, has_pending_analysis, disclaimer

    @patch("apps.portfolios.advice.context.MarketDataService")
    def test_advice_empty_portfolio(self, MockService): ...
        # Assert empty items list

    @patch("apps.portfolios.advice.context.MarketDataService")
    def test_advice_requires_authentication(self, MockService): ...
        # Assert 401 without auth

    @patch("apps.portfolios.advice.context.MarketDataService")
    def test_advice_other_user_portfolio_403(self, MockService): ...
        # Assert 404 for another user's portfolio

    @patch("apps.portfolios.advice.context.MarketDataService")
    def test_advice_max_10_items(self, MockService): ...
        # Create a portfolio that triggers many rules, assert <= 10
```

---

- [ ] **Step 4: Run the full test suite**

```bash
cd backend && python -m pytest apps/portfolios/tests/test_advice_engine.py apps/portfolios/tests/test_advice_rules.py apps/portfolios/tests/test_advice_api.py -v
```

---

- [ ] **Step 5: Run the entire project test suite to check for regressions**

```bash
cd backend && python -m pytest
```

---

- [ ] **Step 6: Commit**

```bash
git add backend/apps/portfolios/tests/test_advice_engine.py backend/apps/portfolios/tests/test_advice_rules.py backend/apps/portfolios/tests/test_advice_api.py
git commit -m "test: comprehensive advice engine test suite (engine, rules, API)"
```

---

### Final Verification

- [ ] **Step 1: Run backend lint**

```bash
cd backend && python -m ruff check .
```

- [ ] **Step 2: Run all backend tests**

```bash
cd backend && python -m pytest
```

- [ ] **Step 3: Run frontend lint and build**

```bash
cd frontend && npx eslint src/ && npm run build
```

- [ ] **Step 4: Run frontend tests**

```bash
cd frontend && npm test
```
