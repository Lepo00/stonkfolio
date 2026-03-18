from __future__ import annotations

import itertools
import logging
from datetime import date, timedelta

import pandas as pd

from apps.market_data.indicators import calculate_rsi, calculate_sma
from apps.market_data.services import MarketDataService

from .models import AdviceContext, AdviceItem, HoldingData

logger = logging.getLogger(__name__)


class SlowRules:
    def __init__(self, ctx: AdviceContext, service: MarketDataService):
        self.ctx = ctx
        self.service = service
        # Pre-computed OHLCV cache: instrument_id -> DataFrame
        self._ohlcv_cache: dict[int, pd.DataFrame] = {}
        # Pre-computed indicator cache: instrument_id -> dict of indicators
        self._indicator_cache: dict[int, dict] = {}

    def evaluate_all(self) -> list[AdviceItem]:
        """Run all slow rules."""
        # Pre-fetch OHLCV data for all holdings to reuse across rules
        self._prefetch_ohlcv()
        self._precompute_indicators()

        results: list[AdviceItem] = []
        for method_name in sorted(dir(self)):
            if method_name.startswith("rule_"):
                try:
                    results.extend(getattr(self, method_name)())
                except Exception:
                    logger.exception("Slow rule %s failed", method_name)
        return results

    # ── Data pre-fetch helpers ──────────────────────────────

    def _prefetch_ohlcv(self) -> None:
        """Fetch 3-month daily OHLCV for all holdings with tickers."""
        for h in self.ctx.holdings:
            if not h.ticker or h.instrument_id in self._ohlcv_cache:
                continue
            try:
                # We need an instrument object for the service call.
                # The service.get_ohlcv expects an instrument with a .ticker attribute.
                # Create a minimal proxy object.
                inst = _InstrumentProxy(h.instrument_id, h.ticker)
                df = self.service.get_ohlcv(inst, "3mo", "1d")
                if df is not None and not df.empty:
                    self._ohlcv_cache[h.instrument_id] = df
            except Exception:
                logger.debug("Failed to fetch OHLCV for %s", h.ticker)

    def _precompute_indicators(self) -> None:
        """Pre-compute RSI(14), SMA(20), SMA(50) for all cached OHLCV data."""
        for inst_id, df in self._ohlcv_cache.items():
            if inst_id in self._indicator_cache:
                continue
            try:
                closes = df["Close"]
                rsi_data = calculate_rsi(closes, 14)
                sma20_data = calculate_sma(closes, 20)
                sma50_data = calculate_sma(closes, 50)

                self._indicator_cache[inst_id] = {
                    "rsi": rsi_data,
                    "sma20": sma20_data,
                    "sma50": sma50_data,
                    "closes": closes,
                }
            except Exception:
                logger.debug("Failed to compute indicators for instrument %s", inst_id)

    def _get_latest_rsi(self, instrument_id: int) -> float | None:
        """Get the latest RSI value for an instrument."""
        indicators = self._indicator_cache.get(instrument_id)
        if not indicators or not indicators["rsi"]:
            return None
        return indicators["rsi"][-1]["value"]

    def _get_latest_sma(self, instrument_id: int, window: int) -> float | None:
        """Get the latest SMA value for an instrument."""
        indicators = self._indicator_cache.get(instrument_id)
        if not indicators:
            return None
        key = f"sma{window}"
        sma_data = indicators.get(key, [])
        if not sma_data:
            return None
        return sma_data[-1]["value"]

    def _get_sma_at_offset(self, instrument_id: int, window: int, offset: int) -> float | None:
        """Get SMA value at a given negative offset (e.g. -5 for 5 days ago)."""
        indicators = self._indicator_cache.get(instrument_id)
        if not indicators:
            return None
        key = f"sma{window}"
        sma_data = indicators.get(key, [])
        if not sma_data or len(sma_data) < abs(offset):
            return None
        return sma_data[offset]["value"]

    def _holding_by_id(self, instrument_id: int) -> HoldingData | None:
        """Find a holding by instrument_id."""
        for h in self.ctx.holdings:
            if h.instrument_id == instrument_id:
                return h
        return None

    # ── Risk (slow) ─────────────────────────────────────────

    def rule_risk_007(self) -> list[AdviceItem]:
        """Correlated Holdings Warning."""
        # Need at least 3 holdings with OHLCV data
        holdings_with_data = [h for h in self.ctx.holdings if h.instrument_id in self._ohlcv_cache]
        if len(holdings_with_data) < 3:
            return []

        # Compute daily returns for each holding
        returns_map: dict[int, pd.Series] = {}
        for h in holdings_with_data:
            df = self._ohlcv_cache[h.instrument_id]
            try:
                returns = df["Close"].pct_change().dropna()
                if len(returns) >= 20:
                    returns_map[h.instrument_id] = returns
            except Exception:
                continue

        if len(returns_map) < 3:
            return []

        # Compute pairwise correlations
        ids = list(returns_map.keys())
        correlations: list[tuple[int, int, float]] = []
        for id_a, id_b in itertools.combinations(ids, 2):
            try:
                ret_a = returns_map[id_a]
                ret_b = returns_map[id_b]
                # Align by index
                aligned = pd.concat([ret_a, ret_b], axis=1, join="inner")
                if len(aligned) < 20:
                    continue
                corr = float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))
                if not pd.isna(corr):
                    correlations.append((id_a, id_b, corr))
            except Exception:
                continue

        if not correlations:
            return []

        avg_corr = sum(c[2] for c in correlations) / len(correlations)
        if avg_corr <= 0.7:
            return []

        # Find the most correlated pair
        most_correlated = max(correlations, key=lambda c: c[2])
        h_a = self._holding_by_id(most_correlated[0])
        h_b = self._holding_by_id(most_correlated[1])
        pair_tickers = [
            h_a.ticker if h_a else str(most_correlated[0]),
            h_b.ticker if h_b else str(most_correlated[1]),
        ]

        return [
            AdviceItem(
                rule_id="RISK_007",
                category="risk",
                priority="warning",
                title="Correlated Holdings",
                message=(
                    f"Your holdings have an average pairwise correlation of {avg_corr:.2f}. "
                    f"High correlation means your positions tend to move together, reducing the "
                    f"diversification benefit. Look for assets with lower or negative correlation "
                    f"to your existing holdings."
                ),
                metadata={
                    "avg_correlation": round(avg_corr, 2),
                    "most_correlated_pair": pair_tickers,
                    "pair_correlation": round(most_correlated[2], 2),
                },
            )
        ]

    # ── Technical ───────────────────────────────────────────

    def rule_tech_001(self) -> list[AdviceItem]:
        """RSI Overbought."""
        items: list[AdviceItem] = []
        for h in self.ctx.holdings:
            rsi = self._get_latest_rsi(h.instrument_id)
            if rsi is None or rsi <= 70:
                continue
            items.append(
                AdviceItem(
                    rule_id="TECH_001",
                    category="technical",
                    priority="info",
                    title="RSI Overbought",
                    message=(
                        f"{h.name} ({h.ticker}) has an RSI of {rsi:.0f}, indicating overbought "
                        f"conditions. This doesn't guarantee a decline, but historically suggests "
                        f"the stock may be due for a pullback or consolidation."
                    ),
                    holdings=[h.ticker],
                    metadata={"ticker": h.ticker, "rsi": round(rsi, 1)},
                )
            )
        return items

    def rule_tech_002(self) -> list[AdviceItem]:
        """RSI Oversold."""
        items: list[AdviceItem] = []
        for h in self.ctx.holdings:
            rsi = self._get_latest_rsi(h.instrument_id)
            if rsi is None or rsi >= 30:
                continue
            items.append(
                AdviceItem(
                    rule_id="TECH_002",
                    category="technical",
                    priority="info",
                    title="RSI Oversold",
                    message=(
                        f"{h.name} ({h.ticker}) has an RSI of {rsi:.0f}, indicating oversold "
                        f"conditions. This may represent a buying opportunity if the fundamentals "
                        f"are sound, but can also signal continued weakness."
                    ),
                    holdings=[h.ticker],
                    metadata={"ticker": h.ticker, "rsi": round(rsi, 1)},
                )
            )
        return items

    def rule_tech_003(self) -> list[AdviceItem]:
        """Golden Cross (Bullish SMA Crossover)."""
        items: list[AdviceItem] = []
        for h in self.ctx.holdings:
            indicators = self._indicator_cache.get(h.instrument_id)
            if not indicators:
                continue
            sma20_data = indicators.get("sma20", [])
            sma50_data = indicators.get("sma50", [])
            if len(sma20_data) < 6 or len(sma50_data) < 6:
                continue

            curr_sma20 = sma20_data[-1]["value"]
            curr_sma50 = sma50_data[-1]["value"]
            prev_sma20 = sma20_data[-5]["value"]
            prev_sma50 = sma50_data[-5]["value"]

            prev_diff = prev_sma20 - prev_sma50
            curr_diff = curr_sma20 - curr_sma50

            if prev_diff <= 0 and curr_diff > 0:
                items.append(
                    AdviceItem(
                        rule_id="TECH_003",
                        category="technical",
                        priority="positive",
                        title="Golden Cross",
                        message=(
                            f"{h.name} ({h.ticker}) just formed a golden cross (20-day SMA crossed "
                            f"above 50-day SMA). This bullish technical signal often precedes "
                            f"sustained upward momentum."
                        ),
                        holdings=[h.ticker],
                        metadata={
                            "ticker": h.ticker,
                            "sma20": round(curr_sma20, 2),
                            "sma50": round(curr_sma50, 2),
                        },
                    )
                )
        return items

    def rule_tech_004(self) -> list[AdviceItem]:
        """Death Cross (Bearish SMA Crossover)."""
        items: list[AdviceItem] = []
        for h in self.ctx.holdings:
            indicators = self._indicator_cache.get(h.instrument_id)
            if not indicators:
                continue
            sma20_data = indicators.get("sma20", [])
            sma50_data = indicators.get("sma50", [])
            if len(sma20_data) < 6 or len(sma50_data) < 6:
                continue

            curr_sma20 = sma20_data[-1]["value"]
            curr_sma50 = sma50_data[-1]["value"]
            prev_sma20 = sma20_data[-5]["value"]
            prev_sma50 = sma50_data[-5]["value"]

            prev_diff = prev_sma20 - prev_sma50
            curr_diff = curr_sma20 - curr_sma50

            if prev_diff >= 0 and curr_diff < 0:
                items.append(
                    AdviceItem(
                        rule_id="TECH_004",
                        category="technical",
                        priority="warning",
                        title="Death Cross",
                        message=(
                            f"{h.name} ({h.ticker}) just formed a death cross (20-day SMA crossed "
                            f"below 50-day SMA). This bearish signal suggests potential downward "
                            f"pressure. Review your thesis for this position."
                        ),
                        holdings=[h.ticker],
                        metadata={
                            "ticker": h.ticker,
                            "sma20": round(curr_sma20, 2),
                            "sma50": round(curr_sma50, 2),
                        },
                    )
                )
        return items

    def rule_tech_005(self) -> list[AdviceItem]:
        """Price Below SMA50 (Downtrend)."""
        items: list[AdviceItem] = []
        for h in self.ctx.holdings:
            if h.current_price is None:
                continue
            sma50 = self._get_latest_sma(h.instrument_id, 50)
            if sma50 is None or sma50 == 0:
                continue
            current = float(h.current_price)
            pct_below = (current - sma50) / sma50 * 100
            if pct_below >= -10:
                continue
            items.append(
                AdviceItem(
                    rule_id="TECH_005",
                    category="technical",
                    priority="info",
                    title="Price Below SMA50",
                    message=(
                        f"{h.name} ({h.ticker}) is trading {pct_below:.1f}% below its 50-day "
                        f"moving average, suggesting a downtrend. Monitor for stabilization "
                        f"before adding to the position."
                    ),
                    holdings=[h.ticker],
                    metadata={
                        "ticker": h.ticker,
                        "current_price": current,
                        "sma50": round(sma50, 2),
                        "pct_below_sma": round(pct_below, 1),
                    },
                )
            )
        return items

    def rule_tech_006(self) -> list[AdviceItem]:
        """Portfolio-Wide Momentum Score."""
        weighted_rsi_sum = 0.0
        weight_sum = 0.0

        for h in self.ctx.holdings:
            rsi = self._get_latest_rsi(h.instrument_id)
            if rsi is None or h.weight_pct is None:
                continue
            weighted_rsi_sum += rsi * h.weight_pct
            weight_sum += h.weight_pct

        if weight_sum == 0:
            return []

        portfolio_rsi = weighted_rsi_sum / weight_sum

        if portfolio_rsi > 65:
            message = (
                f"Your portfolio's weighted average RSI is {portfolio_rsi:.0f}, suggesting "
                f"overall bullish momentum. Be cautious about adding to positions that are "
                f"already extended."
            )
        elif portfolio_rsi < 35:
            message = (
                f"Your portfolio's weighted average RSI is {portfolio_rsi:.0f}, suggesting "
                f"overall bearish conditions. This may present opportunities if you have "
                f"conviction in your holdings."
            )
        else:
            message = f"Your portfolio's weighted average RSI is {portfolio_rsi:.0f}, suggesting neutral momentum."

        return [
            AdviceItem(
                rule_id="TECH_006",
                category="technical",
                priority="info",
                title="Portfolio Momentum Score",
                message=message,
                metadata={"portfolio_rsi": round(portfolio_rsi, 1)},
            )
        ]

    # ── Behavioral (slow subset) ────────────────────────────

    def rule_behav_002(self) -> list[AdviceItem]:
        """Disposition Effect: Selling Winners Too Early."""
        today = date.today()
        cutoff = today - timedelta(days=180)
        items: list[AdviceItem] = []

        # Find SELL transactions in the last 6 months
        sell_txs = [tx for tx in self.ctx.all_transactions if tx.type == "SELL" and tx.date >= cutoff]

        for tx in sell_txs:
            if len(items) >= 2:
                break
            # Check if the sale was profitable (sale price > avg buy price is hard to know,
            # so we approximate: the sale price is tx.price)
            sale_price = float(tx.price)
            if sale_price <= 0:
                continue

            # Get current price for the instrument
            try:
                inst = _InstrumentProxy(tx.instrument_id, tx.instrument.ticker)
                if not inst.ticker:
                    continue
                price_result = self.service.get_current_price(inst)
                current_price = float(price_result.price)
            except Exception:
                continue

            post_sale_pct = (current_price - sale_price) / sale_price * 100
            if post_sale_pct <= 15:
                continue

            ticker = tx.instrument.ticker or tx.instrument.isin
            name = tx.instrument.name
            items.append(
                AdviceItem(
                    rule_id="BEHAV_002",
                    category="behavioral",
                    priority="info",
                    title="Selling Winners Too Early",
                    message=(
                        f"You sold {name} ({ticker}) on {tx.date} at a profit, but the stock has "
                        f"risen {post_sale_pct:.0f}% further since then. While taking profits is "
                        f"prudent, consider whether you're cutting winners short. Letting winners "
                        f"run is a key factor in long-term returns."
                    ),
                    holdings=[ticker],
                    metadata={
                        "ticker": ticker,
                        "sale_date": str(tx.date),
                        "sale_price": sale_price,
                        "current_price": current_price,
                        "post_sale_pct": round(post_sale_pct, 1),
                    },
                )
            )
        return items

    def rule_behav_004(self) -> list[AdviceItem]:
        """Recency Bias Warning."""
        today = date.today()
        cutoff = today - timedelta(days=30)

        # Find BUY transactions in the last 30 days
        recent_buys = [tx for tx in self.ctx.all_transactions if tx.type == "BUY" and tx.date >= cutoff]

        chasing_tickers: list[str] = []
        pre_buy_returns: list[float] = []

        for tx in recent_buys:
            ticker = tx.instrument.ticker
            if not ticker:
                continue
            try:
                # Get price 30 days before the buy date
                start_date = tx.date - timedelta(days=35)
                end_date = tx.date - timedelta(days=1)
                inst = _InstrumentProxy(tx.instrument_id, ticker)
                historical = self.service.get_historical_prices(inst, start_date, end_date)
                if not historical or len(historical) < 2:
                    continue
                price_30d_before = float(historical[0].price)
                price_at_buy = float(tx.price)
                if price_30d_before <= 0:
                    continue
                pre_buy_return = (price_at_buy / price_30d_before - 1) * 100
                if pre_buy_return > 15:
                    if ticker not in chasing_tickers:
                        chasing_tickers.append(ticker)
                        pre_buy_returns.append(round(pre_buy_return, 1))
            except Exception:
                continue

        if len(chasing_tickers) < 2:
            return []

        tickers_str = ", ".join(chasing_tickers)
        return [
            AdviceItem(
                rule_id="BEHAV_004",
                category="behavioral",
                priority="info",
                title="Recency Bias Warning",
                message=(
                    f"Several of your recent purchases ({tickers_str}) had strong runs before "
                    f"you bought them. Chasing recent performance (recency bias) often leads to "
                    f"buying near short-term tops. Ensure your purchases are based on fundamentals, "
                    f"not recent price action."
                ),
                metadata={
                    "tickers": chasing_tickers,
                    "pre_buy_returns": pre_buy_returns,
                },
            )
        ]


class _InstrumentProxy:
    """Minimal proxy to satisfy MarketDataService.get_ohlcv() which needs .ticker and .isin."""

    def __init__(self, instrument_id: int, ticker: str | None):
        self.id = instrument_id
        self.pk = instrument_id
        self.ticker = ticker
        self.isin = ""
