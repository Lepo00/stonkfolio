from __future__ import annotations

import logging
from datetime import date
from math import sqrt

from django.core.cache import cache

from apps.market_data.services import MarketDataService

from .models import Portfolio
from .returns import _build_daily_portfolio_values

logger = logging.getLogger(__name__)

RISK_METRICS_CACHE_TTL = 60 * 60 * 24  # 24 hours

MIN_DATA_POINTS = 30


def calculate_risk_metrics(
    portfolio: Portfolio,
    service: MarketDataService | None = None,
) -> dict:
    """Calculate Sharpe ratio, Sortino ratio, and Beta vs S&P 500.

    Returns dict with keys: sharpe_ratio, sortino_ratio, beta, alpha,
    annualized_volatility, annualized_return, benchmark_return.
    All as float or None if insufficient data.
    """
    cache_key = f"risk_metrics:{portfolio.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    result = _calculate_risk_metrics_uncached(portfolio, service)
    cache.set(cache_key, result, RISK_METRICS_CACHE_TTL)
    return result


def _calculate_risk_metrics_uncached(
    portfolio: Portfolio,
    service: MarketDataService | None = None,
) -> dict:
    """Internal calculation without caching."""
    empty = {
        "sharpe_ratio": None,
        "sortino_ratio": None,
        "beta": None,
        "alpha": None,
        "annualized_volatility": None,
        "annualized_return": None,
        "benchmark_return": None,
    }

    if service is None:
        service = MarketDataService()

    first_tx = portfolio.transactions.order_by("date").first()
    if not first_tx:
        return empty

    start = first_tx.date
    end = date.today()
    if start >= end:
        return empty

    # Build daily portfolio values
    daily_values = _build_daily_portfolio_values(portfolio, service, start, end)
    sorted_dates = sorted(daily_values.keys())

    if len(sorted_dates) < MIN_DATA_POINTS + 1:
        return empty

    # Compute daily portfolio returns
    port_returns: dict[date, float] = {}
    for i in range(1, len(sorted_dates)):
        prev_val = float(daily_values[sorted_dates[i - 1]])
        curr_val = float(daily_values[sorted_dates[i]])
        if prev_val > 0:
            port_returns[sorted_dates[i]] = curr_val / prev_val - 1.0

    # Fetch S&P 500 benchmark prices
    try:
        bench_prices = service.get_historical_prices_by_ticker("^GSPC", start, end)
    except Exception:
        logger.warning("Failed to fetch S&P 500 benchmark prices for risk metrics")
        return empty

    if not bench_prices or len(bench_prices) < 2:
        return empty

    # Compute daily benchmark returns
    bench_returns: dict[date, float] = {}
    for i in range(1, len(bench_prices)):
        prev_price = float(bench_prices[i - 1].price)
        curr_price = float(bench_prices[i].price)
        if prev_price > 0:
            bench_returns[bench_prices[i].date] = curr_price / prev_price - 1.0

    # Align by date
    common_dates = sorted(set(port_returns.keys()) & set(bench_returns.keys()))

    if len(common_dates) < MIN_DATA_POINTS:
        return empty

    port_rets = [port_returns[d] for d in common_dates]
    bench_rets = [bench_returns[d] for d in common_dates]
    n = len(port_rets)

    # Mean returns
    mean_pr = sum(port_rets) / n
    mean_br = sum(bench_rets) / n

    # Standard deviation of portfolio returns
    var_pr = sum((r - mean_pr) ** 2 for r in port_rets) / (n - 1)
    std_pr = sqrt(var_pr) if var_pr > 0 else 0.0

    # Annualized return and volatility
    annualized_return = mean_pr * 252
    annualized_volatility = std_pr * sqrt(252)

    # Annualized benchmark return
    annualized_bench_return = mean_br * 252

    # Sharpe Ratio (rf = 0)
    sharpe = (mean_pr / std_pr) * sqrt(252) if std_pr > 0 else None

    # Sortino Ratio (only penalizes downside)
    downside_returns = [r for r in port_rets if r < 0]
    if downside_returns:
        downside_var = sum(r**2 for r in downside_returns) / len(downside_returns)
        downside_std = sqrt(downside_var)
        sortino = (mean_pr / downside_std) * sqrt(252) if downside_std > 0 else None
    else:
        sortino = None

    # Beta
    cov = sum((pr - mean_pr) * (br - mean_br) for pr, br in zip(port_rets, bench_rets)) / (n - 1)
    var_bench = sum((br - mean_br) ** 2 for br in bench_rets) / (n - 1)
    beta = cov / var_bench if var_bench > 0 else None

    # Alpha (Jensen's alpha, annualized)
    alpha = (annualized_return - beta * annualized_bench_return) if beta is not None else None

    def _round(val: float | None, decimals: int = 2) -> float | None:
        if val is None:
            return None
        return round(val, decimals)

    result = {
        "sharpe_ratio": _round(sharpe),
        "sortino_ratio": _round(sortino),
        "beta": _round(beta),
        "alpha": _round(alpha * 100 if alpha is not None else None),  # as percentage
        "annualized_volatility": _round(annualized_volatility * 100),  # as percentage
        "annualized_return": _round(annualized_return * 100),  # as percentage
        "benchmark_return": _round(annualized_bench_return * 100),  # as percentage
    }
    return result
