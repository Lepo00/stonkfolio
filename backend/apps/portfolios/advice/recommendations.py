from __future__ import annotations

import logging
from collections import defaultdict

from .etf_catalogue import (
    BOND_ETFS,
    CORRELATION_ETFS,
    DEFENSIVE_ETFS,
    DIVIDEND_ETFS,
    GLOBAL_EQUITY_ETFS,
    REGION_ETF_MAP,
    SECTOR_ETF_MAP,
)
from .models import AdviceContext, AdviceItem, Recommendation

logger = logging.getLogger(__name__)

# ── Reference allocations (MSCI ACWI proxy) ──────────────

REFERENCE_SECTOR_WEIGHTS: dict[str, float] = {
    "Technology": 22.0,
    "Financial Services": 16.0,
    "Healthcare": 12.0,
    "Consumer Cyclical": 11.0,
    "Communication Services": 8.0,
    "Industrials": 10.0,
    "Consumer Defensive": 7.0,
    "Energy": 5.0,
    "Utilities": 3.0,
    "Real Estate": 3.0,
    "Basic Materials": 3.0,
}

REFERENCE_REGION_WEIGHTS: dict[str, float] = {
    "North America": 62.0,
    "Europe": 16.0,
    "Asia Pacific": 11.0,
    "Emerging Markets": 11.0,
}

COUNTRY_TO_REGION: dict[str, str] = {
    "United States": "North America",
    "Canada": "North America",
    "Germany": "Europe",
    "France": "Europe",
    "Netherlands": "Europe",
    "United Kingdom": "Europe",
    "Switzerland": "Europe",
    "Spain": "Europe",
    "Italy": "Europe",
    "Sweden": "Europe",
    "Ireland": "Europe",
    "Denmark": "Europe",
    "Norway": "Europe",
    "Finland": "Europe",
    "Belgium": "Europe",
    "Austria": "Europe",
    "Portugal": "Europe",
    "Japan": "Asia Pacific",
    "Australia": "Asia Pacific",
    "Hong Kong": "Asia Pacific",
    "Singapore": "Asia Pacific",
    "New Zealand": "Asia Pacific",
    "China": "Emerging Markets",
    "India": "Emerging Markets",
    "Brazil": "Emerging Markets",
    "South Korea": "Emerging Markets",
    "Taiwan": "Emerging Markets",
    "Mexico": "Emerging Markets",
    "South Africa": "Emerging Markets",
    "Indonesia": "Emerging Markets",
    "Thailand": "Emerging Markets",
    "Malaysia": "Emerging Markets",
    "Poland": "Emerging Markets",
    "Turkey": "Emerging Markets",
    "Saudi Arabia": "Emerging Markets",
}

DEFENSIVE_SECTORS = {"Consumer Defensive", "Utilities", "Healthcare"}

CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}


class RecommendationEngine:
    """Gap-analysis recommendation engine that suggests broad ETFs."""

    def __init__(self, ctx: AdviceContext, items: list[AdviceItem]):
        self.ctx = ctx
        self.items = items

    def evaluate(self) -> list[Recommendation]:
        """Run all six gap analysis passes and return prioritised recommendations."""
        recommendations: list[Recommendation] = []

        recommendations.extend(self._sector_gaps())
        recommendations.extend(self._geographic_gaps())
        recommendations.extend(self._asset_class_gaps())
        recommendations.extend(self._defensive_gaps())
        recommendations.extend(self._income_gaps())
        recommendations.extend(self._correlation_gaps())

        return self._prioritise(recommendations)

    # ── Pass 1: Sector Gap Analysis ───────────────────────

    def _sector_gaps(self) -> list[Recommendation]:
        results: list[Recommendation] = []
        for sector, ref_weight in REFERENCE_SECTOR_WEIGHTS.items():
            user_weight = self.ctx.sector_weights.get(sector, 0.0)
            gap = ref_weight - user_weight

            if gap >= 10.0:
                confidence = "high"
            elif gap >= 5.0:
                confidence = "medium"
            else:
                continue

            etfs = SECTOR_ETF_MAP.get(sector, [])
            if not etfs:
                continue

            results.append(
                Recommendation(
                    category="sector_fill",
                    title=f"Add {sector} Exposure",
                    rationale=(
                        f"Your portfolio has {user_weight:.0f}% in {sector} vs. "
                        f"a global benchmark weight of {ref_weight:.0f}%. "
                        f"This {gap:.0f}pp gap leaves you underexposed to the sector."
                    ),
                    suggested_etfs=etfs[:3],
                    impact=self._compute_sector_impact(sector, ref_weight),
                    confidence=confidence,
                    priority=1 if gap >= 10 else 2,
                )
            )
        return results

    def _compute_sector_impact(self, sector: str, ref_weight: float) -> str:
        """Describe the impact of adding a sector position."""
        # Find the largest current sector
        if self.ctx.sector_weights:
            top_sector = max(self.ctx.sector_weights, key=self.ctx.sector_weights.get)  # type: ignore[arg-type]
            top_weight = self.ctx.sector_weights[top_sector]
            diluted = top_weight * 0.9  # 10% new position dilutes existing
            return (
                f"Would reduce {top_sector} concentration from "
                f"{top_weight:.0f}% to ~{diluted:.0f}% and add {sector} at ~10%"
            )
        return f"Would add {sector} exposure at ~10% of portfolio"

    # ── Pass 2: Geographic Gap Analysis ───────────────────

    def _geographic_gaps(self) -> list[Recommendation]:
        results: list[Recommendation] = []

        # Aggregate user countries into regions
        user_region_weights: dict[str, float] = defaultdict(float)
        for country, pct in self.ctx.country_weights.items():
            region = COUNTRY_TO_REGION.get(country, "Other")
            user_region_weights[region] += pct

        for region, ref_weight in REFERENCE_REGION_WEIGHTS.items():
            user_weight = user_region_weights.get(region, 0.0)
            gap = ref_weight - user_weight

            if gap < 8.0:
                continue

            confidence = "high" if gap >= 15.0 else "medium"

            etfs = REGION_ETF_MAP.get(region, [])
            if not etfs:
                continue

            results.append(
                Recommendation(
                    category="geographic",
                    title=f"Add {region} Exposure",
                    rationale=(
                        f"Your portfolio has {user_weight:.0f}% in {region} vs. "
                        f"a global benchmark weight of {ref_weight:.0f}%. "
                        f"This {gap:.0f}pp gap may leave you overly concentrated geographically."
                    ),
                    suggested_etfs=etfs[:3],
                    impact=f"Would add ~10% {region} exposure, improving geographic diversification",
                    confidence=confidence,
                    priority=1 if gap >= 15 else 2,
                )
            )
        return results

    # ── Pass 3: Asset Class Gap Analysis ──────────────────

    def _asset_class_gaps(self) -> list[Recommendation]:
        results: list[Recommendation] = []

        stock_pct = self.ctx.asset_type_weights.get("STOCK", 0.0)
        etf_pct = self.ctx.asset_type_weights.get("ETF", 0.0)
        bond_pct = self.ctx.asset_type_weights.get("BOND", 0.0)
        fund_pct = self.ctx.asset_type_weights.get("FUND", 0.0)

        equity_pct = stock_pct + etf_pct + fund_pct
        fixed_income_pct = bond_pct

        # Rule 1: >90% equities, <5% bonds
        if equity_pct > 90 and fixed_income_pct < 5:
            results.append(
                Recommendation(
                    category="asset_class",
                    title="Add Fixed Income for Stability",
                    rationale=(
                        f"Your portfolio is {equity_pct:.0f}% equities with no meaningful "
                        f"bond allocation. Adding 10-30% bonds historically reduces volatility "
                        f"by 20-40% with a modest return trade-off."
                    ),
                    suggested_etfs=BOND_ETFS[:3],
                    impact="Adding 20% bonds could reduce annualised volatility by ~25%",
                    confidence="high",
                    priority=1,
                )
            )

        # Rule 2: >90% bonds
        if fixed_income_pct > 90:
            results.append(
                Recommendation(
                    category="asset_class",
                    title="Add Equity Exposure for Growth",
                    rationale=(
                        f"Your portfolio is {fixed_income_pct:.0f}% fixed income. "
                        f"Adding broad equity exposure can improve long-term growth "
                        f"potential while maintaining a balanced risk profile."
                    ),
                    suggested_etfs=GLOBAL_EQUITY_ETFS[:3],
                    impact="Adding 20-40% equities could significantly improve long-term returns",
                    confidence="high",
                    priority=1,
                )
            )

        # Rule 3: >80% individual stocks, <10% ETFs
        if stock_pct > 80 and etf_pct < 10:
            results.append(
                Recommendation(
                    category="asset_class",
                    title="Consider Broad Market ETFs",
                    rationale=(
                        f"Your portfolio is {stock_pct:.0f}% individual stocks. Adding broad "
                        f"index ETFs provides instant diversification across hundreds of "
                        f"companies with a single purchase."
                    ),
                    suggested_etfs=GLOBAL_EQUITY_ETFS[:3],
                    impact="A global ETF adds exposure to 1,500+ companies",
                    confidence="medium",
                    priority=2,
                )
            )

        return results

    # ── Pass 4: Defensive Position Analysis ───────────────

    def _defensive_gaps(self) -> list[Recommendation]:
        if self.ctx.holding_count < 5:
            return []

        defensive_pct = sum(self.ctx.sector_weights.get(s, 0.0) for s in DEFENSIVE_SECTORS)

        if defensive_pct >= 10.0:
            return []

        return [
            Recommendation(
                category="defensive",
                title="Add Defensive Holdings",
                rationale=(
                    f"Only {defensive_pct:.0f}% of your portfolio is in traditionally "
                    f"defensive sectors (utilities, consumer staples, healthcare). "
                    f"These sectors tend to hold up better during market downturns."
                ),
                suggested_etfs=DEFENSIVE_ETFS[:3],
                impact="Raising defensive allocation to 15-20% can reduce drawdowns by 10-15%",
                confidence="high" if defensive_pct < 5 else "medium",
                priority=1 if defensive_pct < 5 else 2,
            )
        ]

    # ── Pass 5: Income / Dividend Analysis ────────────────

    def _income_gaps(self) -> list[Recommendation]:
        if self.ctx.holding_count < 5:
            return []

        total_div_12m = sum(float(tx.quantity * tx.price) for tx in self.ctx.dividend_txs_12m)
        yield_pct = (total_div_12m / float(self.ctx.total_value) * 100) if self.ctx.total_value else 0

        if yield_pct >= 1.0:
            return []

        return [
            Recommendation(
                category="income",
                title="Boost Dividend Income",
                rationale=(
                    f"Your trailing 12-month yield is {yield_pct:.1f}%. Adding high-dividend "
                    f"ETFs can create a passive income stream while maintaining diversification."
                ),
                suggested_etfs=DIVIDEND_ETFS[:3],
                impact="A 10-15% allocation to dividend ETFs could raise portfolio yield to ~2%",
                confidence="medium",
                priority=2,
            )
        ]

    # ── Pass 6: Low-Correlation Asset Analysis ────────────

    def _correlation_gaps(self) -> list[Recommendation]:
        risk_007_items = [item for item in self.items if item.rule_id == "RISK_007"]
        if not risk_007_items:
            return []

        avg_corr = risk_007_items[0].metadata.get("avg_correlation", 0)

        return [
            Recommendation(
                category="low_correlation",
                title="Add Uncorrelated Assets",
                rationale=(
                    f"Your holdings have an average correlation of {avg_corr:.2f}. "
                    f"Adding assets with low or negative correlation to equities -- such as "
                    f"government bonds, gold, or real estate -- would improve true diversification."
                ),
                suggested_etfs=CORRELATION_ETFS[:3],
                impact="Adding 10-20% uncorrelated assets could reduce portfolio correlation to ~0.50",
                confidence="high",
                priority=1,
            )
        ]

    # ── Prioritisation ────────────────────────────────────

    @staticmethod
    def _prioritise(recommendations: list[Recommendation]) -> list[Recommendation]:
        """Sort, enforce diversity of categories, and limit to 5."""
        # Sort by priority asc, then confidence desc
        recommendations.sort(key=lambda r: (r.priority, CONFIDENCE_ORDER.get(r.confidence, 99)))

        # Enforce max 2 per category
        category_counts: dict[str, int] = defaultdict(int)
        filtered: list[Recommendation] = []
        for rec in recommendations:
            if category_counts[rec.category] < 2:
                filtered.append(rec)
                category_counts[rec.category] += 1

        return filtered[:5]
