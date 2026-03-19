from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from apps.market_data.services import MarketDataService
from apps.portfolios.models import Portfolio, TransactionType

from .models import AdviceContext, HoldingData

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "These insights are generated automatically for educational purposes only "
    "and do not constitute financial advice. Past performance does not guarantee "
    "future results. Always consult a qualified financial advisor before making "
    "investment decisions."
)


def build_advice_context(
    portfolio: Portfolio,
    service: MarketDataService | None = None,
) -> AdviceContext:
    """Build a shared AdviceContext for all rules from a portfolio instance."""
    service = service or MarketDataService()

    # ── Fetch holdings with related instruments ──────────────
    db_holdings = list(portfolio.holdings.select_related("instrument").all())

    # ── Price each holding ───────────────────────────────────
    holdings: list[HoldingData] = []
    unpriced: list[HoldingData] = []

    for h in db_holdings:
        inst = h.instrument
        current_price: Decimal | None = None
        try:
            result = service.get_current_price(inst)
            current_price = result.price
        except Exception:
            logger.warning("Could not price %s (%s)", inst.ticker, inst.isin)

        market_value = h.quantity * current_price if current_price is not None else None
        cost_basis = h.quantity * h.avg_buy_price

        # return_pct: unrealised gain/loss percentage
        return_pct: float | None = None
        if current_price is not None and h.avg_buy_price:
            return_pct = float((current_price - h.avg_buy_price) / h.avg_buy_price * 100)

        hd = HoldingData(
            ticker=inst.ticker or inst.isin,
            name=inst.name,
            isin=inst.isin,
            instrument_id=inst.id,
            quantity=h.quantity,
            avg_buy_price=h.avg_buy_price,
            current_price=current_price,
            market_value=market_value,
            cost_basis=cost_basis,
            weight_pct=None,  # computed after totals
            return_pct=return_pct,
            sector=inst.sector or "Unknown",
            country=inst.country or "Unknown",
            asset_type=inst.asset_type or "OTHER",
            currency=inst.currency or "Unknown",
        )
        holdings.append(hd)
        if current_price is None:
            unpriced.append(hd)

    # ── Aggregates ───────────────────────────────────────────
    total_value = sum(
        (h.market_value for h in holdings if h.market_value is not None),
        Decimal("0"),
    )
    total_cost = sum((h.cost_basis for h in holdings), Decimal("0"))

    overall_return_pct = 0.0
    if total_cost:
        overall_return_pct = float((total_value - total_cost) / total_cost * 100)

    # ── Per-holding weight ───────────────────────────────────
    if total_value:
        for h in holdings:
            if h.market_value is not None:
                h.weight_pct = float(h.market_value / total_value * 100)

    # ── Allocation maps ──────────────────────────────────────
    sector_weights: dict[str, float] = defaultdict(float)
    country_weights: dict[str, float] = defaultdict(float)
    currency_weights: dict[str, float] = defaultdict(float)
    asset_type_weights: dict[str, float] = defaultdict(float)

    for h in holdings:
        if h.weight_pct is not None:
            sector_weights[h.sector] += h.weight_pct
            country_weights[h.country] += h.weight_pct
            currency_weights[h.currency] += h.weight_pct
            asset_type_weights[h.asset_type] += h.weight_pct

    # ── Transactions ─────────────────────────────────────────
    # list() forces queryset evaluation so the result is safe for background threads
    all_transactions = list(portfolio.transactions.select_related("instrument").order_by("date"))

    today = date.today()
    one_year_ago = today - timedelta(days=365)

    # Already a materialized list (filtered from all_transactions); safe for threads
    dividend_txs_12m = [
        tx for tx in all_transactions if tx.type == TransactionType.DIVIDEND and tx.date >= one_year_ago
    ]

    # Fee total: sum of fee fields + value of explicit FEE-type transactions
    fee_total = sum((tx.fee for tx in all_transactions), Decimal("0")) + sum(
        (tx.quantity * tx.price for tx in all_transactions if tx.type == TransactionType.FEE),
        Decimal("0"),
    )

    # First transaction date
    first_transaction_date: date | None = all_transactions[0].date if all_transactions else None

    # Last BUY or SELL date
    trade_txs = [tx for tx in all_transactions if tx.type in (TransactionType.BUY, TransactionType.SELL)]
    last_trade_date: date | None = trade_txs[-1].date if trade_txs else None

    # perf_series: set to None; computed lazily by rules that need it
    perf_series = None

    return AdviceContext(
        portfolio_id=portfolio.id,
        holding_count=len(holdings),
        holdings=holdings,
        unpriced_holdings=unpriced,
        total_value=total_value,
        total_cost=total_cost,
        overall_return_pct=overall_return_pct,
        sector_weights=dict(sector_weights),
        country_weights=dict(country_weights),
        currency_weights=dict(currency_weights),
        asset_type_weights=dict(asset_type_weights),
        all_transactions=all_transactions,
        dividend_txs_12m=dividend_txs_12m,
        fee_total=fee_total,
        first_transaction_date=first_transaction_date,
        last_trade_date=last_trade_date,
        perf_series=perf_series,
    )
