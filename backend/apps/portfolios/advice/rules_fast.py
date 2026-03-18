from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from math import sqrt

from .models import AdviceContext, AdviceItem, HoldingData

logger = logging.getLogger(__name__)


class FastRules:
    def __init__(self, ctx: AdviceContext):
        self.ctx = ctx

    def evaluate_all(self) -> list[AdviceItem]:
        """Run all fast rules and collect results."""
        results: list[AdviceItem] = []
        for method_name in sorted(dir(self)):
            if method_name.startswith("rule_"):
                try:
                    results.extend(getattr(self, method_name)())
                except Exception:
                    logger.exception("Rule %s failed", method_name)
        return results

    # ── helpers ──────────────────────────────────────────────

    def _priced_holdings(self) -> list[HoldingData]:
        return [h for h in self.ctx.holdings if h.weight_pct is not None]

    def _compute_perf_series(self) -> bool:
        """Ensure perf_series is populated.  Returns True if available."""
        if self.ctx.perf_series is not None:
            return len(self.ctx.perf_series) > 0
        # perf_series is None => not available (will be computed lazily elsewhere)
        return False

    # ── Risk Management (fast) ──────────────────────────────

    def rule_risk_001(self) -> list[AdviceItem]:
        """Single-Holding Concentration."""
        items: list[AdviceItem] = []
        for h in self._priced_holdings():
            if h.weight_pct >= 40:
                priority = "critical"
                threshold = 40
            elif h.weight_pct >= 25:
                priority = "warning"
                threshold = 25
            else:
                continue
            items.append(
                AdviceItem(
                    rule_id="RISK_001",
                    category="risk",
                    priority=priority,
                    title="Single-Stock Concentration",
                    message=(
                        f"{h.name} ({h.ticker}) represents {h.weight_pct:.1f}% of your portfolio. "
                        f"A single position above {threshold}% creates significant concentration risk. "
                        f"Consider trimming to below 20% and reallocating to uncorrelated assets."
                    ),
                    holdings=[h.ticker],
                    metadata={"ticker": h.ticker, "weight_pct": h.weight_pct, "threshold": threshold},
                )
            )
        return items

    def rule_risk_002(self) -> list[AdviceItem]:
        """Top-3 Concentration."""
        priced = self._priced_holdings()
        if len(priced) < 4:
            return []
        sorted_h = sorted(priced, key=lambda h: h.weight_pct or 0, reverse=True)
        top3 = sorted_h[:3]
        top3_pct = sum(h.weight_pct for h in top3)
        if top3_pct <= 70:
            return []
        return [
            AdviceItem(
                rule_id="RISK_002",
                category="risk",
                priority="warning",
                title="Top-3 Concentration",
                message=(
                    f"Your top 3 holdings ({top3[0].name}, {top3[1].name}, {top3[2].name}) "
                    f"account for {top3_pct:.1f}% of total value. Portfolios with heavy "
                    f"top-concentration are vulnerable to idiosyncratic shocks. "
                    f"Target keeping the top 3 below 60%."
                ),
                holdings=[h.ticker for h in top3],
                metadata={"top3_pct": top3_pct, "holdings": [h.ticker for h in top3]},
            )
        ]

    def rule_risk_003(self) -> list[AdviceItem]:
        """Portfolio Volatility Alert."""
        if not self._compute_perf_series():
            return []
        series = self.ctx.perf_series
        if len(series) < 30:
            return []
        try:
            import pandas as pd

            values = pd.Series([float(v) for _, v in series])
            daily_returns = values.pct_change().dropna()
            if len(daily_returns) < 20:
                return []
            ann_vol = float(daily_returns.std() * sqrt(252) * 100)
        except Exception:
            logger.exception("RISK_003 volatility calculation failed")
            return []

        if ann_vol <= 25:
            return []

        if ann_vol > 40:
            priority = "critical"
        else:
            priority = "warning"

        qualifier = "moderately higher" if ann_vol <= 35 else "significantly higher"
        return [
            AdviceItem(
                rule_id="RISK_003",
                category="risk",
                priority=priority,
                title="Portfolio Volatility Alert",
                message=(
                    f"Your portfolio's annualized volatility is {ann_vol:.1f}%, which is "
                    f"{qualifier} than a typical balanced portfolio (12-15%). Consider adding "
                    f"bonds or low-volatility ETFs to reduce overall risk."
                ),
                metadata={"annualized_vol": ann_vol},
            )
        ]

    def rule_risk_004(self) -> list[AdviceItem]:
        """Maximum Drawdown Warning."""
        if not self._compute_perf_series():
            return []
        series = self.ctx.perf_series
        if len(series) < 60:
            return []
        try:
            import pandas as pd

            dates = [d for d, _ in series]
            values = pd.Series([float(v) for _, v in series], index=dates)
            cummax = values.cummax()
            drawdown = (values - cummax) / cummax * 100
            max_dd = float(drawdown.min())
            trough_idx = drawdown.idxmin()
            # Find the peak date: the date of cummax at the trough point
            peak_val = cummax[trough_idx]
            peak_dates = [d for d, v in zip(dates, cummax) if v == peak_val and d <= trough_idx]
            peak_date = peak_dates[0] if peak_dates else dates[0]
        except Exception:
            logger.exception("RISK_004 drawdown calculation failed")
            return []

        if max_dd > -15:
            return []

        if max_dd < -30:
            priority = "critical"
            follow_up = (
                "This exceeds typical bear-market thresholds. Review your risk tolerance "
                "and ensure you have adequate emergency reserves."
            )
        else:
            priority = "warning"
            follow_up = "Consider whether your asset allocation matches your risk tolerance."

        return [
            AdviceItem(
                rule_id="RISK_004",
                category="risk",
                priority=priority,
                title="Maximum Drawdown Warning",
                message=(
                    f"Your portfolio experienced a {max_dd:.1f}% drawdown from its peak "
                    f"in the past 12 months. {follow_up}"
                ),
                metadata={
                    "max_drawdown_pct": max_dd,
                    "peak_date": str(peak_date),
                    "trough_date": str(trough_idx),
                },
            )
        ]

    def rule_risk_005(self) -> list[AdviceItem]:
        """Currency Exposure Concentration."""
        items: list[AdviceItem] = []
        for currency, pct in self.ctx.currency_weights.items():
            if currency == "EUR":
                continue  # base currency, exempt
            if pct > 40:
                items.append(
                    AdviceItem(
                        rule_id="RISK_005",
                        category="risk",
                        priority="warning",
                        title="Currency Exposure Concentration",
                        message=(
                            f"{pct:.0f}% of your portfolio is denominated in {currency}. "
                            f"Significant unhedged foreign-currency exposure adds exchange-rate risk. "
                            f"Consider whether this aligns with your outlook on {currency}/EUR."
                        ),
                        metadata={"currency": currency, "weight_pct": pct},
                    )
                )
        return items

    def rule_risk_006(self) -> list[AdviceItem]:
        """Single-Country Exposure."""
        items: list[AdviceItem] = []
        for country, pct in self.ctx.country_weights.items():
            if country in ("Unknown", "", None):
                continue
            if pct > 60:
                items.append(
                    AdviceItem(
                        rule_id="RISK_006",
                        category="risk",
                        priority="warning",
                        title="Single-Country Exposure",
                        message=(
                            f"{pct:.0f}% of your portfolio is concentrated in {country}. "
                            f"Country-specific political, regulatory, or economic events could "
                            f"disproportionately impact your returns. Consider geographic diversification."
                        ),
                        metadata={"country": country, "weight_pct": pct},
                    )
                )
        return items

    # ── Diversification ─────────────────────────────────────

    def rule_div_001(self) -> list[AdviceItem]:
        """Insufficient Holdings."""
        count = self.ctx.holding_count
        if count >= 10:
            return []
        s = "" if count == 1 else "s"
        if count < 5:
            return [
                AdviceItem(
                    rule_id="DIV_001",
                    category="diversification",
                    priority="warning",
                    title="Insufficient Holdings",
                    message=(
                        f"Your portfolio has only {count} position{s}. Academic research suggests "
                        f"a minimum of 15-20 holdings to achieve basic diversification. With so few "
                        f"positions, a single stock event could significantly impact your portfolio."
                    ),
                    metadata={"holding_count": count},
                )
            ]
        # 5-9
        return [
            AdviceItem(
                rule_id="DIV_001",
                category="diversification",
                priority="info",
                title="Insufficient Holdings",
                message=(
                    f"Your portfolio has {count} positions. While better than a handful, you may "
                    f"still benefit from adding holdings across different sectors and geographies "
                    f"to improve diversification."
                ),
                metadata={"holding_count": count},
            )
        ]

    def rule_div_002(self) -> list[AdviceItem]:
        """Sector Concentration."""
        items: list[AdviceItem] = []
        for sector, pct in self.ctx.sector_weights.items():
            if sector in ("Unknown", "", None):
                continue
            if pct > 60:
                priority = "critical"
            elif pct > 40:
                priority = "warning"
            else:
                continue
            items.append(
                AdviceItem(
                    rule_id="DIV_002",
                    category="diversification",
                    priority=priority,
                    title="Sector Concentration",
                    message=(
                        f"{pct:.0f}% of your portfolio is in the {sector} sector. Sector-specific "
                        f"downturns (regulatory changes, commodity price shifts, tech corrections) "
                        f"could significantly impact your returns. Consider rebalancing to spread "
                        f"across at least 4-5 sectors."
                    ),
                    metadata={"sector": sector, "weight_pct": pct},
                )
            )
        return items

    def rule_div_003(self) -> list[AdviceItem]:
        """Missing Sector Exposure."""
        if self.ctx.holding_count < 8:
            return []
        unique_sectors = {h.sector for h in self.ctx.holdings if h.sector and h.sector != "Unknown"}
        if len(unique_sectors) > 2:
            return []
        sector_count = len(unique_sectors)
        s = "" if sector_count == 1 else "s"
        sectors_str = ", ".join(sorted(unique_sectors)) if unique_sectors else "Unknown"
        return [
            AdviceItem(
                rule_id="DIV_003",
                category="diversification",
                priority="info",
                title="Missing Sector Exposure",
                message=(
                    f"Despite having {self.ctx.holding_count} holdings, your portfolio only covers "
                    f"{sector_count} sector{s}: {sectors_str}. Spreading across more sectors can "
                    f"reduce correlation and smooth returns."
                ),
                metadata={
                    "holding_count": self.ctx.holding_count,
                    "sector_count": sector_count,
                    "sectors": sorted(unique_sectors),
                },
            )
        ]

    def rule_div_004(self) -> list[AdviceItem]:
        """Asset Class Imbalance."""
        if self.ctx.holding_count < 5:
            return []
        asset_types = {h.asset_type for h in self.ctx.holdings if h.asset_type}
        if len(asset_types) != 1:
            return []
        asset_type = next(iter(asset_types))
        return [
            AdviceItem(
                rule_id="DIV_004",
                category="diversification",
                priority="info",
                title="Asset Class Imbalance",
                message=(
                    f"Your portfolio is entirely composed of {asset_type}s. Adding other asset "
                    f"classes (bonds, ETFs, or funds) can reduce volatility and provide more "
                    f"stable returns during equity drawdowns."
                ),
                metadata={"asset_type": asset_type, "weight_pct": 100.0},
            )
        ]

    def rule_div_005(self) -> list[AdviceItem]:
        """Single-Geography Portfolio."""
        if self.ctx.holding_count < 5:
            return []
        countries = {h.country for h in self.ctx.holdings if h.country and h.country != "Unknown"}
        if len(countries) != 1:
            return []
        country = next(iter(countries))
        return [
            AdviceItem(
                rule_id="DIV_005",
                category="diversification",
                priority="info",
                title="Single-Geography Portfolio",
                message=(
                    f"All your holdings are domiciled in {country}. International diversification "
                    f"can reduce country-specific risk and provide access to different growth cycles."
                ),
                metadata={"country": country},
            )
        ]

    # ── Performance ─────────────────────────────────────────

    def rule_perf_001(self) -> list[AdviceItem]:
        """Overall Portfolio Return."""
        if self.ctx.holding_count == 0:
            return []
        ret = self.ctx.overall_return_pct
        gain_loss = float(self.ctx.total_value - self.ctx.total_cost)

        if ret > 0:
            if ret > 10:
                context = ""
            else:
                context = ""
            return [
                AdviceItem(
                    rule_id="PERF_001",
                    category="performance",
                    priority="positive",
                    title="Overall Portfolio Return",
                    message=(
                        f"Your portfolio is up {ret:.1f}% overall ({gain_loss:+.2f} EUR).{' ' + context if context else ''}"
                    ),
                    metadata={"return_pct": ret, "gain_loss_eur": gain_loss},
                )
            ]
        else:
            if ret < -10:
                context = "Stay focused on your long-term strategy and avoid panic-selling."
            else:
                context = "Markets fluctuate -- paper losses are only realized if you sell."
            return [
                AdviceItem(
                    rule_id="PERF_001",
                    category="performance",
                    priority="info",
                    title="Overall Portfolio Return",
                    message=(f"Your portfolio is down {abs(ret):.1f}% overall ({gain_loss:.2f} EUR). {context}"),
                    metadata={"return_pct": ret, "gain_loss_eur": gain_loss},
                )
            ]

    def rule_perf_002(self) -> list[AdviceItem]:
        """Significant Underperformers."""
        items: list[AdviceItem] = []
        for h in self._priced_holdings():
            if h.return_pct is None:
                continue
            if h.return_pct < -20:
                loss_pct = abs(h.return_pct)
                items.append(
                    AdviceItem(
                        rule_id="PERF_002",
                        category="performance",
                        priority="warning",
                        title="Significant Underperformer",
                        message=(
                            f"{h.name} ({h.ticker}) is down {loss_pct:.1f}% from your average cost. "
                            f"Losses of this magnitude warrant a fundamental review. Ask: would you "
                            f"buy this stock today at the current price? If not, consider cutting "
                            f"the position."
                        ),
                        holdings=[h.ticker],
                        metadata={
                            "ticker": h.ticker,
                            "loss_pct": loss_pct,
                            "cost_basis": float(h.cost_basis),
                            "current_price": float(h.current_price),
                        },
                    )
                )
            elif h.return_pct < -10:
                loss_pct = abs(h.return_pct)
                items.append(
                    AdviceItem(
                        rule_id="PERF_002",
                        category="performance",
                        priority="info",
                        title="Underperformer",
                        message=(
                            f"{h.name} ({h.ticker}) is down {loss_pct:.1f}% from your cost basis. "
                            f"Review whether the original investment thesis still holds."
                        ),
                        holdings=[h.ticker],
                        metadata={
                            "ticker": h.ticker,
                            "loss_pct": loss_pct,
                            "cost_basis": float(h.cost_basis),
                            "current_price": float(h.current_price),
                        },
                    )
                )
        return items

    def rule_perf_003(self) -> list[AdviceItem]:
        """Strong Performers."""
        items: list[AdviceItem] = []
        for h in self._priced_holdings():
            if h.return_pct is None:
                continue
            if h.return_pct > 25:
                items.append(
                    AdviceItem(
                        rule_id="PERF_003",
                        category="performance",
                        priority="positive",
                        title="Strong Performer",
                        message=(
                            f"{h.name} ({h.ticker}) is up {h.return_pct:.1f}% from your cost basis. "
                            f"Consider whether to take partial profits to lock in gains, or let it "
                            f"run if the fundamentals remain strong."
                        ),
                        holdings=[h.ticker],
                        metadata={"ticker": h.ticker, "gain_pct": h.return_pct},
                    )
                )
        return items

    def rule_perf_004(self) -> list[AdviceItem]:
        """Deep Losers (>50% loss)."""
        items: list[AdviceItem] = []
        for h in self._priced_holdings():
            if h.return_pct is None:
                continue
            if h.return_pct < -50:
                loss_pct = abs(h.return_pct)
                # recovery_needed_pct = (1 / (1 + return_pct/100) - 1) * 100
                recovery_needed = (1 / (1 + h.return_pct / 100) - 1) * 100
                items.append(
                    AdviceItem(
                        rule_id="PERF_004",
                        category="performance",
                        priority="critical",
                        title="Deep Loss Alert",
                        message=(
                            f"{h.name} ({h.ticker}) has lost {loss_pct:.1f}% of its value. A 50%+ "
                            f"loss requires a 100%+ gain just to break even. Seriously evaluate "
                            f"whether this position has a realistic recovery path or if the capital "
                            f"would be better deployed elsewhere."
                        ),
                        holdings=[h.ticker],
                        metadata={
                            "ticker": h.ticker,
                            "loss_pct": loss_pct,
                            "recovery_needed_pct": round(recovery_needed, 1),
                        },
                    )
                )
        return items

    def rule_perf_005(self) -> list[AdviceItem]:
        """Period Return Context."""
        if not self._compute_perf_series():
            return []
        series = self.ctx.perf_series
        if len(series) < 30:
            return []

        today_val = float(series[-1][1])

        # 1-month return
        target_1m = len(series) - 30
        if target_1m < 0:
            return []
        val_1m = float(series[target_1m][1])
        return_1m = (today_val / val_1m - 1) * 100 if val_1m else 0

        # 3-month return
        target_3m = len(series) - 90
        if target_3m >= 0:
            val_3m = float(series[target_3m][1])
            return_3m = (today_val / val_3m - 1) * 100 if val_3m else 0
        else:
            # Not enough data for 3m, use earliest available
            val_3m = float(series[0][1])
            return_3m = (today_val / val_3m - 1) * 100 if val_3m else 0

        return [
            AdviceItem(
                rule_id="PERF_005",
                category="performance",
                priority="info",
                title="Period Returns",
                message=(
                    f"Your portfolio has returned {return_1m:+.1f}% over the past month and "
                    f"{return_3m:+.1f}% over the past 3 months."
                ),
                metadata={"return_1m": round(return_1m, 1), "return_3m": round(return_3m, 1)},
            )
        ]

    def rule_perf_006(self) -> list[AdviceItem]:
        """Best and Worst Performers Summary."""
        priced = [h for h in self._priced_holdings() if h.return_pct is not None]
        if len(priced) < 3:
            return []
        best = max(priced, key=lambda h: h.return_pct)
        worst = min(priced, key=lambda h: h.return_pct)
        spread = best.return_pct - worst.return_pct
        return [
            AdviceItem(
                rule_id="PERF_006",
                category="performance",
                priority="info",
                title="Best & Worst Performers",
                message=(
                    f"Best performer: {best.name} ({best.ticker}) at {best.return_pct:+.1f}%. "
                    f"Worst performer: {worst.name} ({worst.ticker}) at {worst.return_pct:+.1f}%. "
                    f"Spread: {spread:.0f} percentage points."
                ),
                metadata={
                    "best_ticker": best.ticker,
                    "best_pct": best.return_pct,
                    "worst_ticker": worst.ticker,
                    "worst_pct": worst.return_pct,
                    "spread": spread,
                },
            )
        ]

    # ── Income ──────────────────────────────────────────────

    def rule_inc_001(self) -> list[AdviceItem]:
        """Portfolio Dividend Yield."""
        if not self.ctx.dividend_txs_12m:
            return []
        total_div = sum(float(tx.quantity * tx.price) for tx in self.ctx.dividend_txs_12m)
        if total_div <= 0 or self.ctx.total_value <= 0:
            return []
        yield_pct = total_div / float(self.ctx.total_value) * 100

        if yield_pct > 3:
            priority = "positive"
        else:
            priority = "info"

        if yield_pct > 2:
            context = "This is above the S&P 500 average yield of ~1.5%."
        else:
            context = "Consider adding dividend-paying stocks or ETFs if income is a priority."

        return [
            AdviceItem(
                rule_id="INC_001",
                category="income",
                priority=priority,
                title="Portfolio Dividend Yield",
                message=(
                    f"Your trailing 12-month dividend yield is {yield_pct:.2f}% "
                    f"(EUR {total_div:.2f} received). {context}"
                ),
                metadata={"yield_pct": round(yield_pct, 2), "total_dividends_12m": round(total_div, 2)},
            )
        ]

    def rule_inc_002(self) -> list[AdviceItem]:
        """Dividend Concentration."""
        if not self.ctx.dividend_txs_12m:
            return []
        # Group dividends by instrument
        per_instrument: dict[int, tuple[str, str, float]] = {}
        for tx in self.ctx.dividend_txs_12m:
            inst_id = tx.instrument_id
            amount = float(tx.quantity * tx.price)
            if inst_id in per_instrument:
                name, ticker, prev = per_instrument[inst_id]
                per_instrument[inst_id] = (name, ticker, prev + amount)
            else:
                ticker = tx.instrument.ticker or tx.instrument.isin
                name = tx.instrument.name
                per_instrument[inst_id] = (name, ticker, amount)

        total_div = sum(v[2] for v in per_instrument.values())
        if total_div <= 0:
            return []

        max_inst = max(per_instrument.values(), key=lambda x: x[2])
        max_pct = max_inst[2] / total_div * 100
        if max_pct <= 50:
            return []

        return [
            AdviceItem(
                rule_id="INC_002",
                category="income",
                priority="warning",
                title="Dividend Concentration",
                message=(
                    f"{max_pct:.0f}% of your dividend income comes from {max_inst[0]} ({max_inst[1]}). "
                    f"If this company cuts its dividend, your income stream would be significantly "
                    f"impacted. Diversify your income sources."
                ),
                holdings=[max_inst[1]],
                metadata={"ticker": max_inst[1], "income_concentration_pct": round(max_pct, 1)},
            )
        ]

    def rule_inc_003(self) -> list[AdviceItem]:
        """No Dividend Income."""
        if self.ctx.holding_count < 5:
            return []
        if self.ctx.dividend_txs_12m:
            return []
        return [
            AdviceItem(
                rule_id="INC_003",
                category="income",
                priority="info",
                title="No Dividend Income",
                message=(
                    "Your portfolio has not generated any dividend income in the past 12 months. "
                    "If passive income is a goal, consider allocating a portion to dividend-paying "
                    "stocks or income-focused ETFs."
                ),
                metadata={"holding_count": self.ctx.holding_count, "months_without_dividends": 12},
            )
        ]

    # ── Cost ────────────────────────────────────────────────

    def rule_cost_001(self) -> list[AdviceItem]:
        """Fee Drag."""
        if self.ctx.total_cost <= 0:
            return []
        total_fees = float(self.ctx.fee_total)
        if total_fees <= 0:
            return []
        fee_ratio = total_fees / float(self.ctx.total_cost) * 100

        if fee_ratio > 2:
            priority = "warning"
            context = (
                "This is eating into your returns. Consider using a lower-cost broker or making fewer, larger trades."
            )
        elif fee_ratio > 1:
            priority = "info"
            context = "Keep an eye on fees -- they compound against you over time."
        else:
            return []

        return [
            AdviceItem(
                rule_id="COST_001",
                category="cost",
                priority=priority,
                title="Fee Drag",
                message=(
                    f"You've paid EUR {total_fees:.2f} in transaction fees "
                    f"({fee_ratio:.2f}% of invested capital). {context}"
                ),
                metadata={"total_fees": round(total_fees, 2), "fee_ratio_pct": round(fee_ratio, 2)},
            )
        ]

    def rule_cost_002(self) -> list[AdviceItem]:
        """High-Fee Individual Transactions."""
        high_fee_txs: list[tuple[object, float]] = []
        for tx in self.ctx.all_transactions:
            if tx.type not in ("BUY", "SELL"):
                continue
            trade_value = float(tx.quantity * tx.price)
            if trade_value <= 0:
                continue
            fee = float(tx.fee)
            if fee <= 0:
                continue
            fee_pct = fee / trade_value * 100
            if fee_pct > 3:
                high_fee_txs.append((tx, fee_pct))

        if not high_fee_txs:
            return []

        # Sort by fee_pct descending, take top 3
        high_fee_txs.sort(key=lambda x: x[1], reverse=True)
        items: list[AdviceItem] = []
        for tx, fee_pct in high_fee_txs[:3]:
            ticker = tx.instrument.ticker or tx.instrument.isin
            trade_value = float(tx.quantity * tx.price)
            items.append(
                AdviceItem(
                    rule_id="COST_002",
                    category="cost",
                    priority="info",
                    title="High-Fee Transaction",
                    message=(
                        f"Transaction on {tx.date}: {tx.type} {ticker} had a {fee_pct:.1f}% fee "
                        f"({float(tx.fee):.2f} EUR on a {trade_value:.2f} EUR trade). Small trades "
                        f"with flat fees can have disproportionate costs."
                    ),
                    holdings=[ticker],
                    metadata={
                        "ticker": ticker,
                        "date": str(tx.date),
                        "fee_pct": round(fee_pct, 1),
                        "fee_eur": round(float(tx.fee), 2),
                    },
                )
            )
        return items

    def rule_cost_003(self) -> list[AdviceItem]:
        """Tax-Loss Harvesting Opportunity."""
        # Calculate realized gains in the current calendar year
        current_year = date.today().year
        realized_gains = Decimal("0")
        for tx in self.ctx.all_transactions:
            if tx.type != "SELL":
                continue
            if tx.date.year != current_year:
                continue
            # Approximate gain: we don't have per-lot cost basis in tx,
            # so use positive fee-adjusted proceeds as a proxy.
            # A more accurate approach would track lots, but this is a heuristic.
            realized_gains += tx.quantity * tx.price

        if realized_gains <= 0:
            return []

        items: list[AdviceItem] = []
        for h in self._priced_holdings():
            if h.return_pct is None or h.return_pct >= -5:
                continue
            unrealized_loss = float(h.current_price - h.avg_buy_price) * float(h.quantity)
            items.append(
                AdviceItem(
                    rule_id="COST_003",
                    category="cost",
                    priority="info",
                    title="Tax-Loss Harvesting Opportunity",
                    message=(
                        f"{h.name} ({h.ticker}) has an unrealized loss of EUR {abs(unrealized_loss):.2f} "
                        f"({abs(h.return_pct):.1f}%). You have EUR {float(realized_gains):.2f} in "
                        f"realized gains this year. Selling this position could offset taxable gains "
                        f"(check local tax rules for wash-sale restrictions)."
                    ),
                    holdings=[h.ticker],
                    metadata={
                        "ticker": h.ticker,
                        "unrealized_loss": round(abs(unrealized_loss), 2),
                        "realized_gains_ytd": round(float(realized_gains), 2),
                    },
                )
            )
        return items

    # ── Behavioral (fast subset) ────────────────────────────

    def rule_behav_001(self) -> list[AdviceItem]:
        """Disposition Effect: Holding Losers Too Long."""
        items: list[AdviceItem] = []
        today = date.today()

        for h in self._priced_holdings():
            if h.return_pct is None or h.return_pct >= -20:
                continue

            # Find the most recent transaction for this instrument
            last_tx_date = None
            last_tx_type = None
            for tx in self.ctx.all_transactions:
                if tx.instrument_id == h.instrument_id:
                    if last_tx_date is None or tx.date > last_tx_date:
                        last_tx_date = tx.date
                        last_tx_type = tx.type

            if last_tx_date is None:
                continue
            # Must be a BUY and older than 6 months
            if last_tx_type != "BUY":
                continue
            months_held = (today - last_tx_date).days / 30
            if months_held < 6:
                continue

            loss_pct = abs(h.return_pct)
            items.append(
                AdviceItem(
                    rule_id="BEHAV_001",
                    category="behavioral",
                    priority="warning",
                    title="Holding Losers Too Long",
                    message=(
                        f"You've held {h.name} ({h.ticker}) at a {loss_pct:.0f}% loss for over "
                        f"{months_held:.0f} months without action. Investors often hold losers hoping "
                        f"to break even (the 'disposition effect'). Objectively reassess: would you "
                        f"buy this stock today?"
                    ),
                    holdings=[h.ticker],
                    metadata={
                        "ticker": h.ticker,
                        "loss_pct": loss_pct,
                        "months_held": round(months_held, 1),
                    },
                )
            )
        return items

    def rule_behav_003(self) -> list[AdviceItem]:
        """Overtrading Warning."""
        today = date.today()
        cutoff = today - timedelta(days=90)
        items: list[AdviceItem] = []

        recent_trades = [tx for tx in self.ctx.all_transactions if tx.type in ("BUY", "SELL") and tx.date >= cutoff]
        tx_count = len(recent_trades)

        # Check high volume
        if tx_count > 20:
            items.append(
                AdviceItem(
                    rule_id="BEHAV_003",
                    category="behavioral",
                    priority="warning",
                    title="Overtrading Warning",
                    message=(
                        f"You've made {tx_count} trades in the last 3 months. Frequent trading "
                        f"increases costs and typically underperforms a buy-and-hold strategy. "
                        f"Studies show that the most active traders earn the lowest returns."
                    ),
                    metadata={"tx_count_3m": tx_count, "round_trip_tickers": []},
                )
            )

        # Check round-tripping: same ticker bought AND sold >2 times in 3 months
        ticker_actions: dict[str, dict[str, int]] = defaultdict(lambda: {"BUY": 0, "SELL": 0})
        for tx in recent_trades:
            ticker = tx.instrument.ticker or tx.instrument.isin
            ticker_actions[ticker][tx.type] += 1

        round_trip_tickers = [
            ticker for ticker, counts in ticker_actions.items() if counts["BUY"] > 2 and counts["SELL"] > 2
        ]

        for ticker in round_trip_tickers:
            counts = ticker_actions[ticker]
            round_trips = min(counts["BUY"], counts["SELL"])
            items.append(
                AdviceItem(
                    rule_id="BEHAV_003",
                    category="behavioral",
                    priority="warning",
                    title="Round-Tripping Detected",
                    message=(
                        f"{ticker} has been bought and sold {round_trips} times in 3 months. "
                        f"Frequent round-tripping suggests short-term trading behavior, which "
                        f"rarely outperforms after fees and taxes."
                    ),
                    holdings=[ticker],
                    metadata={
                        "tx_count_3m": tx_count,
                        "round_trip_tickers": round_trip_tickers,
                    },
                )
            )
        return items

    def rule_behav_005(self) -> list[AdviceItem]:
        """Rebalancing Nudge."""
        if self.ctx.holding_count < 2:
            return []
        priced = self._priced_holdings()
        if not priced:
            return []

        equal_weight = 100.0 / self.ctx.holding_count
        max_drift = max(abs((h.weight_pct or 0) - equal_weight) for h in priced)

        if max_drift <= 10:
            return []

        # Check months since last trade
        today = date.today()
        if self.ctx.last_trade_date:
            months_since = (today - self.ctx.last_trade_date).days / 30
        else:
            months_since = 12  # no trade on record

        if months_since < 3:
            return []

        return [
            AdviceItem(
                rule_id="BEHAV_005",
                category="behavioral",
                priority="info",
                title="Rebalancing Nudge",
                message=(
                    f"Your portfolio allocation has drifted significantly from equal weight "
                    f"(max drift: {max_drift:.0f}pp). You haven't traded in {months_since:.0f} months. "
                    f"Consider rebalancing to bring positions back to your target allocation."
                ),
                metadata={
                    "max_drift_pp": round(max_drift, 1),
                    "months_since_last_trade": int(months_since),
                },
            )
        ]

    # ── Health ──────────────────────────────────────────────

    def rule_health_001(self) -> list[AdviceItem]:
        """Negligible Positions."""
        negligible = [h for h in self._priced_holdings() if h.weight_pct is not None and h.weight_pct < 1]
        if not negligible:
            return []

        if len(negligible) > 3:
            # Group into a single item
            tickers = [h.ticker for h in negligible]
            return [
                AdviceItem(
                    rule_id="HEALTH_001",
                    category="health",
                    priority="info",
                    title="Negligible Positions",
                    message=(
                        f"You have {len(negligible)} positions each representing less than 1% of "
                        f"your portfolio ({', '.join(tickers)}). Positions this small have negligible "
                        f"impact on overall returns. Consider either building them to a meaningful "
                        f"size or closing them to simplify your portfolio."
                    ),
                    holdings=tickers,
                    metadata={
                        "count": len(negligible),
                        "tickers": tickers,
                    },
                )
            ]

        items: list[AdviceItem] = []
        for h in negligible:
            market_value = float(h.market_value) if h.market_value else 0
            items.append(
                AdviceItem(
                    rule_id="HEALTH_001",
                    category="health",
                    priority="info",
                    title="Negligible Position",
                    message=(
                        f"{h.name} ({h.ticker}) represents only {h.weight_pct:.1f}% of your "
                        f"portfolio (EUR {market_value:.2f}). Positions this small have negligible "
                        f"impact on overall returns. Consider either building the position to a "
                        f"meaningful size or closing it to simplify your portfolio."
                    ),
                    holdings=[h.ticker],
                    metadata={
                        "ticker": h.ticker,
                        "weight_pct": h.weight_pct,
                        "market_value": market_value,
                    },
                )
            )
        return items

    def rule_health_002(self) -> list[AdviceItem]:
        """Stale Positions (No Activity)."""
        today = date.today()
        items: list[AdviceItem] = []

        # Build a map of instrument_id -> most recent tx date
        last_tx_map: dict[int, date] = {}
        for tx in self.ctx.all_transactions:
            inst_id = tx.instrument_id
            if inst_id not in last_tx_map or tx.date > last_tx_map[inst_id]:
                last_tx_map[inst_id] = tx.date

        for h in self.ctx.holdings:
            last_tx_date = last_tx_map.get(h.instrument_id)
            if last_tx_date is None:
                continue
            months_since = (today - last_tx_date).days / 30
            if months_since <= 12:
                continue
            items.append(
                AdviceItem(
                    rule_id="HEALTH_002",
                    category="health",
                    priority="info",
                    title="Stale Position",
                    message=(
                        f"{h.name} ({h.ticker}) has had no activity for {months_since:.0f} months. "
                        f"While buy-and-hold is valid, ensure you're still periodically reviewing "
                        f"positions for fundamental changes."
                    ),
                    holdings=[h.ticker],
                    metadata={
                        "ticker": h.ticker,
                        "months_since_last_tx": round(months_since, 1),
                        "last_tx_date": str(last_tx_date),
                    },
                )
            )
        return items

    def rule_health_003(self) -> list[AdviceItem]:
        """Large Unrealized-Gain Position (Rebalance Consideration)."""
        items: list[AdviceItem] = []
        for h in self._priced_holdings():
            if h.return_pct is None or h.weight_pct is None:
                continue
            if h.return_pct > 50 and h.weight_pct > 15:
                items.append(
                    AdviceItem(
                        rule_id="HEALTH_003",
                        category="health",
                        priority="info",
                        title="Large Unrealized Gain",
                        message=(
                            f"{h.name} ({h.ticker}) has gained {h.return_pct:.0f}% and now represents "
                            f"{h.weight_pct:.1f}% of your portfolio. Consider taking partial profits "
                            f"to manage risk, even if you remain bullish on the stock."
                        ),
                        holdings=[h.ticker],
                        metadata={
                            "ticker": h.ticker,
                            "gain_pct": h.return_pct,
                            "weight_pct": h.weight_pct,
                        },
                    )
                )
        return items

    def rule_health_004(self) -> list[AdviceItem]:
        """Portfolio Age Context."""
        if self.ctx.first_transaction_date is None:
            return []
        today = date.today()
        months = (today - self.ctx.first_transaction_date).days / 30
        if months >= 3:
            return []
        return [
            AdviceItem(
                rule_id="HEALTH_004",
                category="health",
                priority="info",
                title="New Portfolio",
                message=(
                    f"Your portfolio is only {months:.0f} months old. Give your investments time "
                    f"to compound -- most investment strategies need at least 1-3 years to show "
                    f"their potential. Avoid making drastic changes based on short-term results."
                ),
                metadata={
                    "portfolio_age_months": round(months, 1),
                    "first_transaction_date": str(self.ctx.first_transaction_date),
                },
            )
        ]

    def rule_health_005(self) -> list[AdviceItem]:
        """Unpriced Instruments."""
        if not self.ctx.unpriced_holdings:
            return []
        count = len(self.ctx.unpriced_holdings)
        tickers = [h.ticker or h.isin for h in self.ctx.unpriced_holdings]
        s = "" if count == 1 else "s"
        return [
            AdviceItem(
                rule_id="HEALTH_005",
                category="health",
                priority="warning",
                title="Unpriced Instruments",
                message=(
                    f"{count} holding{s} ({', '.join(tickers)}) could not be priced. Portfolio "
                    f"valuations and analytics may be inaccurate. Check that ticker symbols are "
                    f"correctly assigned."
                ),
                holdings=tickers,
                metadata={"count": count, "tickers": tickers},
            )
        ]
