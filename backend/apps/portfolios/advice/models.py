from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class AdviceItem:
    rule_id: str  # e.g. "RISK_001"
    category: str  # risk | performance | diversification | cost | income | technical | behavioral | health
    priority: str  # critical | warning | info | positive
    title: str
    message: str
    holdings: list[str] = field(default_factory=list)  # tickers of affected holdings
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
    current_price: Decimal | None  # None if pricing failed
    market_value: Decimal | None  # quantity * current_price, None if unpriced
    cost_basis: Decimal  # quantity * avg_buy_price
    weight_pct: float | None  # % of total portfolio value
    return_pct: float | None  # unrealized gain/loss %
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
    total_value: Decimal  # sum of market values (priced holdings only)
    total_cost: Decimal  # sum of cost basis (all holdings)
    overall_return_pct: float

    # Allocation maps: {key: weight_pct}
    sector_weights: dict[str, float]
    country_weights: dict[str, float]
    currency_weights: dict[str, float]
    asset_type_weights: dict[str, float]

    # Transaction data (pre-fetched)
    all_transactions: list  # QuerySet result list of Transaction objects
    dividend_txs_12m: list  # DIVIDEND txs in last 12 months
    fee_total: Decimal  # sum of all fees
    first_transaction_date: date | None
    last_trade_date: date | None  # most recent BUY or SELL

    # Performance series (may be None if insufficient data)
    perf_series: list | None  # list of (date, Decimal) tuples from PortfolioPerformanceView logic


@dataclass
class AdviceResponse:
    items: list[AdviceItem]
    has_pending_analysis: bool
    disclaimer: str
