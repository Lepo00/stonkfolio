from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from apps.market_data.services import MarketDataService

from .models import Portfolio, TransactionType

logger = logging.getLogger(__name__)


def _build_daily_portfolio_values(
    portfolio: Portfolio,
    service: MarketDataService,
    start: date,
    end: date,
) -> dict[date, Decimal]:
    """Replay transactions against historical prices to build {date: total_value}.

    This is the same logic used by PortfolioPerformanceView, extracted for reuse.
    """
    txs = portfolio.transactions.select_related("instrument").order_by("date").all()

    instrument_changes: dict[int, dict] = {}
    for tx in txs:
        if not tx.instrument.ticker:
            continue
        changes = instrument_changes.setdefault(
            tx.instrument_id,
            {"instrument": tx.instrument, "events": []},
        )
        if tx.type == TransactionType.BUY:
            changes["events"].append((tx.date, tx.quantity))
        elif tx.type == TransactionType.SELL:
            changes["events"].append((tx.date, -tx.quantity))

    inst_series: dict[int, dict[date, Decimal]] = {}
    for inst_data in instrument_changes.values():
        instrument = inst_data["instrument"]
        events = inst_data["events"]
        try:
            prices = service.get_historical_prices(instrument, start, end)
        except Exception:
            continue

        qty = Decimal("0")
        event_idx = 0
        daily: dict[date, Decimal] = {}
        for pp in prices:
            while event_idx < len(events) and events[event_idx][0] <= pp.date:
                qty += events[event_idx][1]
                event_idx += 1
            if qty > 0:
                daily[pp.date] = qty * pp.price
        if daily:
            inst_series[instrument.id] = daily

    # Merge per-instrument series into a single portfolio series, carry-forward missing
    all_dates = sorted({d for daily in inst_series.values() for d in daily})
    result: dict[date, Decimal] = {}
    for d in all_dates:
        total = Decimal("0")
        for daily in inst_series.values():
            if d in daily:
                total += daily[d]
            else:
                prev_dates = [pd for pd in daily if pd < d]
                if prev_dates:
                    total += daily[max(prev_dates)]
        result[d] = total
    return result


def _get_cash_flow_dates(portfolio: Portfolio) -> list[date]:
    """Return sorted distinct dates where BUY or SELL transactions occurred."""
    txs = (
        portfolio.transactions.filter(
            type__in=[TransactionType.BUY, TransactionType.SELL],
        )
        .order_by("date")
        .values_list("date", flat=True)
        .distinct()
    )
    return list(txs)


def calculate_twr(
    portfolio: Portfolio,
    service: MarketDataService,
) -> Decimal | None:
    """Calculate annualized Time-Weighted Return.

    TWR eliminates the effect of cash flows by chaining sub-period returns
    at each cash flow event (BUY/SELL date).

    Returns annualized TWR as a percentage, or None if it cannot be calculated.
    """
    first_tx = portfolio.transactions.order_by("date").first()
    if not first_tx:
        return None

    start = first_tx.date
    end = date.today()
    if start >= end:
        return None

    daily_values = _build_daily_portfolio_values(portfolio, service, start, end)
    if len(daily_values) < 2:
        return None

    sorted_dates = sorted(daily_values.keys())
    cash_flow_dates = set(_get_cash_flow_dates(portfolio))

    # Build sub-period boundaries: start + each cash flow date + end
    boundaries = [sorted_dates[0]]
    for d in sorted_dates[1:]:
        if d in cash_flow_dates:
            boundaries.append(d)
    if boundaries[-1] != sorted_dates[-1]:
        boundaries.append(sorted_dates[-1])

    # Chain sub-period returns
    cumulative = Decimal("1")
    for i in range(len(boundaries) - 1):
        start_date = boundaries[i]
        end_date = boundaries[i + 1]

        # On a cash flow date the portfolio value already includes the new
        # shares.  We need the value just *before* that cash flow, which is
        # the previous trading day's value.
        start_val = daily_values.get(start_date, Decimal("0"))

        # For the ending value: if end_date is a cash flow boundary, use the
        # day before it (the last pre-cash-flow value).
        if end_date in cash_flow_dates:
            prev_dates = [d for d in sorted_dates if d < end_date]
            end_val = daily_values[prev_dates[-1]] if prev_dates else daily_values.get(end_date, Decimal("0"))
        else:
            end_val = daily_values.get(end_date, Decimal("0"))

        if start_val <= 0:
            continue

        sub_return = end_val / start_val
        cumulative *= sub_return

    twr = cumulative - 1
    days = (sorted_dates[-1] - sorted_dates[0]).days
    if days <= 0:
        return None

    try:
        # Annualize: (1 + twr) ^ (365/days) - 1
        exponent = Decimal("365") / Decimal(str(days))
        annualized = (Decimal("1") + twr) ** exponent - 1
        return (annualized * 100).quantize(Decimal("0.01"))
    except (InvalidOperation, OverflowError):
        return None


def _xirr_npv(rate: float, cash_flows: list[tuple[date, float]]) -> float:
    """Compute NPV for a given annual rate and dated cash flows."""
    if not cash_flows:
        return 0.0
    t0 = cash_flows[0][0]
    npv = 0.0
    for d, amount in cash_flows:
        years = (d - t0).days / 365.0
        npv += amount / ((1.0 + rate) ** years)
    return npv


def _xirr_npv_deriv(rate: float, cash_flows: list[tuple[date, float]]) -> float:
    """Compute derivative of NPV w.r.t. rate for Newton-Raphson."""
    if not cash_flows:
        return 0.0
    t0 = cash_flows[0][0]
    deriv = 0.0
    for d, amount in cash_flows:
        years = (d - t0).days / 365.0
        if years == 0:
            continue
        deriv -= years * amount / ((1.0 + rate) ** (years + 1.0))
    return deriv


def calculate_xirr(
    portfolio: Portfolio,
    service: MarketDataService,
    max_iterations: int = 100,
    tolerance: float = 1e-7,
) -> Decimal | None:
    """Calculate XIRR (Extended Internal Rate of Return) using Newton-Raphson.

    Cash flows:
    - BUY:      negative (money out) = -(quantity * price + fee)
    - SELL:     positive (money in)  = +(quantity * price - fee)
    - DIVIDEND: positive (money in)  = +(quantity * price)
    - Current portfolio value: positive on today's date

    Returns annualized XIRR as a percentage, or None if it cannot converge.
    """
    txs = portfolio.transactions.select_related("instrument").order_by("date").all()
    if not txs:
        return None

    cash_flows: list[tuple[date, float]] = []

    for tx in txs:
        amount: float
        if tx.type == TransactionType.BUY:
            amount = -float(tx.quantity * tx.price + tx.fee)
        elif tx.type == TransactionType.SELL:
            amount = float(tx.quantity * tx.price - tx.fee)
        elif tx.type == TransactionType.DIVIDEND:
            amount = float(tx.quantity * tx.price)
        else:
            continue  # FEE and FX types are not direct cash flows for XIRR
        cash_flows.append((tx.date, amount))

    if not cash_flows:
        return None

    # Add current portfolio value as a terminal positive cash flow
    holdings = portfolio.holdings.select_related("instrument").all()
    current_value = 0.0
    for h in holdings:
        try:
            price_result = service.get_current_price(h.instrument)
            current_value += float(h.quantity * price_result.price)
        except Exception:
            current_value += float(h.quantity * h.avg_buy_price)

    today = date.today()
    if current_value > 0:
        cash_flows.append((today, current_value))

    # Sort by date
    cash_flows.sort(key=lambda x: x[0])

    # Check that we have at least one positive and one negative cash flow
    has_positive = any(cf[1] > 0 for cf in cash_flows)
    has_negative = any(cf[1] < 0 for cf in cash_flows)
    if not (has_positive and has_negative):
        return None

    # Newton-Raphson with initial guess of 10%
    rate = 0.1
    for _ in range(max_iterations):
        npv = _xirr_npv(rate, cash_flows)
        deriv = _xirr_npv_deriv(rate, cash_flows)
        if abs(deriv) < 1e-12:
            return None  # derivative too small, cannot converge
        new_rate = rate - npv / deriv
        # Clamp to avoid divergence
        if new_rate > 100.0:  # 10,000% — clearly unreasonable
            new_rate = (rate + 100.0) / 2.0  # bisect toward upper bound
        if new_rate < -0.99:
            new_rate = (rate - 0.99) / 2.0  # bisect toward lower bound
        if abs(new_rate - rate) < tolerance:
            try:
                return (Decimal(str(new_rate)) * 100).quantize(Decimal("0.01"))
            except (InvalidOperation, OverflowError):
                return None
        rate = new_rate

    return None  # did not converge
