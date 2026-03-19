# AI Advice Page -- Content Specification

> **Status:** Draft
> **Date:** 2026-03-19
> **Endpoint:** `GET /api/portfolios/<id>/advice/full/`

---

## Overview

A dedicated full-page AI Advice view that expands the existing compact "Portfolio Insights" card into five distinct sections: a portfolio health score, prioritised top actions, ETF purchase recommendations (gap analysis), optimisation scenarios, and a legal disclaimer.

The page reuses and extends the existing `AdviceEngine` (two-tier fast/slow evaluation with caching), the `AdviceContext` data model, and the `AdviceItem` schema. New logic lives in a separate `RecommendationEngine` class alongside the existing `FastRules` / `SlowRules`.

---

## Section 1: Portfolio Health Score

### What the user sees

| Element | Detail |
|---------|--------|
| Overall score | 0-100 gauge / radial progress bar |
| One-line summary | e.g. "Well-diversified but with sector concentration risk" |
| Category breakdown | Mini horizontal bars for each sub-score |

### Sub-score categories (0-100 each)

| Category | Weight | Inputs |
|----------|--------|--------|
| **Diversification** | 25% | holding count, sector count, country count, asset-type count, HHI of sector weights, HHI of country weights |
| **Risk** | 25% | single-holding concentration max, top-3 concentration, currency exposure, annualised volatility, max drawdown, pairwise correlation |
| **Performance** | 20% | overall return, 1m/3m return vs 0% benchmark, count of deep losers (>-50%), best/worst spread |
| **Income** | 10% | trailing 12m yield, dividend concentration |
| **Cost** | 10% | fee ratio, high-fee transaction count |
| **Health** | 10% | unpriced count, negligible position count, stale position count, portfolio age |

### Scoring algorithm

Each sub-score starts at 100 and receives penalty deductions based on triggered `AdviceItem` rules:

```
penalty_map = {
    "critical": -40,
    "warning":  -20,
    "info":     -5,
    "positive": +5,   # cap contribution at +10 per category
}
```

For each `AdviceItem` returned by the existing `FastRules` + `SlowRules`, map its `category` to the corresponding sub-score and apply the penalty. Clamp each sub-score to [0, 100].

Overall score = weighted sum of sub-scores, rounded to nearest integer.

### Summary sentence generation

Use the two lowest-scoring categories to construct the summary:

```python
CATEGORY_PHRASES = {
    "diversification": "diversification gaps",
    "risk": "concentration risk",
    "performance": "underperforming positions",
    "income": "low income generation",
    "cost": "high fee drag",
    "health": "portfolio hygiene issues",
}

if overall >= 80:
    prefix = "Your portfolio is in strong shape"
elif overall >= 60:
    prefix = "Your portfolio is on the right track"
elif overall >= 40:
    prefix = "Your portfolio needs attention"
else:
    prefix = "Your portfolio has significant issues"

# Append the two weakest categories
weakest = sorted(sub_scores.items(), key=lambda x: x[1])[:2]
suffix = " and ".join(CATEGORY_PHRASES[c] for c, _ in weakest)
summary = f"{prefix}, with {suffix}."
```

### Backend data needed

- Existing `AdviceContext` (already computed by `build_advice_context`)
- Existing `AdviceItem` list (already computed by `AdviceEngine.evaluate()`)
- No new data fetches required; scoring is a pure post-processing step

### Response format

```jsonc
{
  "overall_score": 72,
  "summary": "Your portfolio is on the right track, with diversification gaps and concentration risk.",
  "sub_scores": {
    "diversification": { "score": 55, "weight": 25, "item_count": 3 },
    "risk":            { "score": 60, "weight": 25, "item_count": 2 },
    "performance":     { "score": 85, "weight": 20, "item_count": 1 },
    "income":          { "score": 90, "weight": 10, "item_count": 0 },
    "cost":            { "score": 95, "weight": 10, "item_count": 0 },
    "health":          { "score": 80, "weight": 10, "item_count": 1 }
  }
}
```

---

## Section 2: Top Actions

### What the user sees

3-5 prioritised action cards, each containing:

- Action title (imperative verb: "Reduce", "Add", "Review", "Sell")
- One-sentence rationale ("why")
- Expected impact ("Reduces sector concentration from 65% to ~45%")
- Urgency badge: `urgent` | `recommended` | `consider`

### Action derivation logic

Actions are derived from the existing `AdviceItem` list, not invented independently. Each rule ID maps to an action template:

```python
ACTION_TEMPLATES = {
    # Risk
    "RISK_001": {
        "action": "Reduce position in {ticker}",
        "impact": "Lowers single-stock concentration from {weight_pct:.0f}% toward 15-20%",
        "urgency": "urgent",
    },
    "RISK_002": {
        "action": "Rebalance top-heavy portfolio",
        "impact": "Spreads risk across more positions, reducing top-3 from {top3_pct:.0f}%",
        "urgency": "urgent",
    },
    "RISK_003": {
        "action": "Add low-volatility holdings",
        "impact": "Targets annualised volatility below 20% (currently {annualized_vol:.0f}%)",
        "urgency": "recommended",
    },
    "RISK_005": {
        "action": "Hedge {currency} currency exposure",
        "impact": "Reduces FX risk on {weight_pct:.0f}% of portfolio",
        "urgency": "consider",
    },
    "RISK_006": {
        "action": "Diversify beyond {country}",
        "impact": "Reduces single-country exposure from {weight_pct:.0f}%",
        "urgency": "recommended",
    },

    # Diversification
    "DIV_001": {
        "action": "Add more holdings to your portfolio",
        "impact": "Increases position count from {holding_count} toward 15-20",
        "urgency": "recommended",
    },
    "DIV_002": {
        "action": "Reduce {sector} sector weight",
        "impact": "Brings sector allocation from {weight_pct:.0f}% toward 20-30%",
        "urgency": "recommended",
    },
    "DIV_004": {
        "action": "Add a different asset class",
        "impact": "Introduces bond/ETF exposure to reduce equity-only volatility",
        "urgency": "recommended",
    },

    # Performance
    "PERF_004": {
        "action": "Review deep loss in {ticker}",
        "impact": "Assess whether to cut losses or hold (currently {loss_pct:.0f}% down)",
        "urgency": "urgent",
    },

    # Behavioral
    "BEHAV_001": {
        "action": "Reassess {ticker} position",
        "impact": "Held at {loss_pct:.0f}% loss for {months_held:.0f} months -- decide to hold or cut",
        "urgency": "recommended",
    },
    "BEHAV_003": {
        "action": "Reduce trading frequency",
        "impact": "Lower fee drag and improve after-cost returns",
        "urgency": "consider",
    },

    # Income
    "INC_003": {
        "action": "Consider dividend-paying positions",
        "impact": "Adds passive income stream to portfolio",
        "urgency": "consider",
    },

    # Health
    "HEALTH_001": {
        "action": "Clean up negligible positions",
        "impact": "Simplifies portfolio by removing sub-1% positions",
        "urgency": "consider",
    },
    "HEALTH_005": {
        "action": "Fix unpriced instruments",
        "impact": "Ensures accurate portfolio valuation and analytics",
        "urgency": "urgent",
    },
}
```

Processing steps:
1. Iterate over `AdviceItem` list sorted by priority (critical first).
2. For each item, look up `ACTION_TEMPLATES[item.rule_id]`.
3. Interpolate template strings using `item.metadata`.
4. Deduplicate: if two items map to the same action text, keep the higher-priority one.
5. Return the top 5 actions.

### Response format

```jsonc
{
  "actions": [
    {
      "action": "Reduce position in AAPL",
      "rationale": "AAPL represents 45.2% of your portfolio, creating significant concentration risk.",
      "impact": "Lowers single-stock concentration from 45% toward 15-20%",
      "urgency": "urgent",
      "related_rule_id": "RISK_001",
      "related_holdings": ["AAPL"]
    }
    // ... up to 5 items
  ]
}
```

---

## Section 3: What to Buy (Recommendation Engine)

This is the core novel section. It recommends **broad ETFs and index funds only** -- never individual stocks.

### Architecture

A new class `RecommendationEngine` in `backend/apps/portfolios/advice/recommendations.py` that takes an `AdviceContext` and produces a list of `Recommendation` dataclasses.

```python
@dataclass
class Recommendation:
    category: str          # "sector_fill" | "geographic" | "asset_class" | "income" | "defensive" | "low_correlation"
    title: str             # "Add Healthcare Exposure"
    rationale: str         # "Your portfolio has 0% healthcare but 62% technology..."
    suggested_etfs: list[SuggestedETF]
    impact: str            # "Would reduce technology concentration from 62% to ~48%"
    confidence: str        # "high" | "medium" | "low"
    priority: int          # 1 = most important

@dataclass
class SuggestedETF:
    name: str              # "iShares STOXX Europe 600 Health Care UCITS ETF"
    ticker: str            # "SXDPEX" (Xetra ticker)
    isin: str              # "DE000A0Q4R36"
    provider: str          # "iShares"
    ter: str               # "0.46%"
    index_tracked: str     # "STOXX Europe 600 Health Care"
    why: str               # "Broad European healthcare, 53 holdings, UCITS compliant"
```

### 3.1 Gap Analysis Rules

The engine runs six independent gap-analysis passes. Each produces zero or more `Recommendation` objects.

#### 3.1.1 Sector Gap Analysis

**Thresholds and reference allocation:**

The reference model is a simplified global market-cap sector distribution (MSCI ACWI as proxy):

```python
REFERENCE_SECTOR_WEIGHTS = {
    "Technology":        22.0,
    "Financial Services": 16.0,
    "Healthcare":        12.0,
    "Consumer Cyclical":  11.0,
    "Communication Services": 8.0,
    "Industrials":        10.0,
    "Consumer Defensive":  7.0,
    "Energy":              5.0,
    "Utilities":           3.0,
    "Real Estate":         3.0,
    "Basic Materials":     3.0,
}
```

**Logic:**

```python
for sector, ref_weight in REFERENCE_SECTOR_WEIGHTS.items():
    user_weight = ctx.sector_weights.get(sector, 0.0)
    gap = ref_weight - user_weight

    if gap >= 10.0:
        confidence = "high"
    elif gap >= 5.0:
        confidence = "medium"
    else:
        continue  # gap too small to recommend

    recommendation = Recommendation(
        category="sector_fill",
        title=f"Add {sector} Exposure",
        rationale=(
            f"Your portfolio has {user_weight:.0f}% in {sector} vs. "
            f"a global benchmark weight of {ref_weight:.0f}%. "
            f"This {gap:.0f}pp gap leaves you underexposed to the sector."
        ),
        suggested_etfs=SECTOR_ETF_MAP[sector],  # see ETF catalogue below
        impact=_compute_sector_impact(ctx, sector, ref_weight),
        confidence=confidence,
        priority=1 if gap >= 10 else 2,
    )
```

**Sector ETF catalogue** (European-listed UCITS ETFs, sorted by preference):

| Sector | ETF 1 | ETF 2 | ETF 3 |
|--------|-------|-------|-------|
| Technology | iShares S&P 500 Info Tech (IUIT.L, IE00B3WJKG14, TER 0.15%) | Xtrackers MSCI World IT (XDWT.DE, IE00BM67HT60, TER 0.25%) | Amundi MSCI World IT (WTEC.PA, LU1681046931, TER 0.35%) |
| Healthcare | iShares STOXX Europe 600 HC (SXDPEX.DE, DE000A0Q4R36, TER 0.46%) | iShares S&P 500 HC (IUHC.L, IE00B43HR379, TER 0.15%) | Xtrackers MSCI World HC (XDWH.DE, IE00BM67HK77, TER 0.25%) |
| Financial Services | iShares S&P 500 Financials (IUFS.L, IE00B4JNQZ49, TER 0.15%) | Xtrackers MSCI World Financials (XDWF.DE, IE00BM67HL84, TER 0.25%) | Amundi STOXX Europe 600 Banks (BNKE.PA, LU1834983477, TER 0.30%) |
| Consumer Cyclical | iShares S&P 500 Cons Discr (IUCD.L, IE00B4MCHD36, TER 0.15%) | Xtrackers MSCI World Cons Discr (XDWC.DE, IE00BM67HP23, TER 0.25%) | - |
| Communication Services | iShares S&P 500 Comm Svcs (IUCM.L, IE00BDDRF700, TER 0.15%) | Xtrackers MSCI World Comm Svcs (XDWM.DE, IE00BM67HR47, TER 0.25%) | - |
| Industrials | iShares S&P 500 Industrials (IUIS.L, IE00B4LN9N13, TER 0.15%) | Xtrackers MSCI World Industrials (XDWI.DE, IE00BM67HV82, TER 0.25%) | Amundi STOXX Europe 600 Industrials (STIP.PA, LU1834987890, TER 0.30%) |
| Consumer Defensive | iShares S&P 500 Cons Staples (IUCS.L, IE00B40B8R38, TER 0.15%) | Xtrackers MSCI World Cons Staples (XDWS.DE, IE00BM67HN09, TER 0.25%) | - |
| Energy | iShares S&P 500 Energy (IUES.L, IE00B4KBBD01, TER 0.15%) | Xtrackers MSCI World Energy (XDWE.DE, IE00BM67HM91, TER 0.25%) | iShares STOXX Europe 600 Oil & Gas (SXEPEX.DE, DE000A0H08M3, TER 0.46%) |
| Utilities | iShares S&P 500 Utilities (IUUS.L, IE00B4KBBD01, TER 0.15%) | Xtrackers MSCI World Utilities (XDWU.DE, IE00BM67HR47, TER 0.25%) | - |
| Real Estate | iShares Dvlp Mkts Prop Yield (IWDP.L, IE00B1FZS350, TER 0.59%) | Xtrackers FTSE EPRA/NAREIT Dev Europe (XDER.DE, LU0489337690, TER 0.33%) | - |
| Basic Materials | iShares S&P 500 Materials (IUMS.L, IE00B4MKCJ84, TER 0.15%) | Xtrackers MSCI World Materials (XDWP.DE, IE00BM67HS53, TER 0.25%) | - |

**Selection logic:** Return up to 3 ETFs per recommendation. Prefer lower TER. If user already holds an instrument from the same provider, prefer that provider for consistency.

#### 3.1.2 Geographic Gap Analysis

**Reference allocation (MSCI ACWI):**

```python
REFERENCE_REGION_WEIGHTS = {
    "North America":    62.0,  # US + Canada
    "Europe":           16.0,
    "Asia Pacific":     11.0,  # Japan, Australia, HK, Singapore
    "Emerging Markets":  11.0,  # China, India, Brazil, etc.
}

# Country-to-region mapping for user holdings
COUNTRY_TO_REGION = {
    "United States": "North America",
    "Canada": "North America",
    "Germany": "Europe", "France": "Europe", "Netherlands": "Europe",
    "United Kingdom": "Europe", "Switzerland": "Europe", "Spain": "Europe",
    "Italy": "Europe", "Sweden": "Europe", "Ireland": "Europe",
    "Japan": "Asia Pacific", "Australia": "Asia Pacific",
    "Hong Kong": "Asia Pacific", "Singapore": "Asia Pacific",
    "China": "Emerging Markets", "India": "Emerging Markets",
    "Brazil": "Emerging Markets", "South Korea": "Emerging Markets",
    "Taiwan": "Emerging Markets",
    # ... extend as needed, default to "Other"
}
```

**Logic:**

```python
# Aggregate user's country weights into regions
user_region_weights = defaultdict(float)
for country, pct in ctx.country_weights.items():
    region = COUNTRY_TO_REGION.get(country, "Other")
    user_region_weights[region] += pct

for region, ref_weight in REFERENCE_REGION_WEIGHTS.items():
    user_weight = user_region_weights.get(region, 0.0)
    gap = ref_weight - user_weight

    if gap < 8.0:
        continue

    # Generate recommendation with region-specific ETFs
```

**Geographic ETF catalogue:**

| Region | ETF 1 | ETF 2 | ETF 3 |
|--------|-------|-------|-------|
| North America | iShares Core S&P 500 (CSPX.L, IE00B5BMR087, TER 0.07%) | Vanguard S&P 500 (VUSA.L, IE00B3XXRP09, TER 0.07%) | Xtrackers S&P 500 (XSPX.DE, IE00BM67HT60, TER 0.06%) |
| Europe | iShares Core MSCI Europe (SMEA.L, IE00B4K48X80, TER 0.12%) | Vanguard FTSE Developed Europe (VEUR.L, IE00B945VN12, TER 0.10%) | Xtrackers MSCI Europe (XMEU.DE, LU0274209237, TER 0.12%) |
| Asia Pacific | iShares Core MSCI Pacific ex Japan (CPXJ.L, IE00B52MJY50, TER 0.20%) | Vanguard FTSE Japan (VJPN.L, IE00B95PGT31, TER 0.15%) | Xtrackers MSCI Japan (XMJP.DE, LU0274209740, TER 0.12%) |
| Emerging Markets | iShares Core MSCI EM IMI (EIMI.L, IE00BKM4GZ66, TER 0.18%) | Vanguard FTSE Emerging Mkts (VFEM.L, IE00B3VVMM84, TER 0.22%) | Xtrackers MSCI Emerging Mkts (XMME.DE, IE00BTJRMP35, TER 0.18%) |

**Confidence:** `high` if gap >= 15pp, `medium` if gap >= 8pp.

#### 3.1.3 Asset Class Gap Analysis

**Logic:**

```python
stock_pct = ctx.asset_type_weights.get("STOCK", 0.0)
etf_pct = ctx.asset_type_weights.get("ETF", 0.0)
bond_pct = ctx.asset_type_weights.get("BOND", 0.0)
fund_pct = ctx.asset_type_weights.get("FUND", 0.0)

equity_pct = stock_pct + etf_pct + fund_pct  # approximate
fixed_income_pct = bond_pct

# Rule 1: 100% equities, 0% bonds -> recommend bond ETFs
if equity_pct > 90 and fixed_income_pct < 5:
    recommendations.append(Recommendation(
        category="asset_class",
        title="Add Fixed Income for Stability",
        rationale=(
            f"Your portfolio is {equity_pct:.0f}% equities with no meaningful "
            f"bond allocation. Adding 10-30% bonds historically reduces volatility "
            f"by 20-40% with a modest return trade-off."
        ),
        suggested_etfs=BOND_ETFS,  # see below
        impact="Adding 20% bonds could reduce annualised volatility by ~25%",
        confidence="high",
        priority=1,
    ))

# Rule 2: 100% bonds -> recommend equity ETFs
if fixed_income_pct > 90:
    # recommend global equity ETFs
    ...

# Rule 3: all individual stocks, no ETFs
if stock_pct > 80 and etf_pct < 10:
    recommendations.append(Recommendation(
        category="asset_class",
        title="Consider Broad Market ETFs",
        rationale=(
            f"Your portfolio is {stock_pct:.0f}% individual stocks. Adding broad "
            f"index ETFs provides instant diversification across hundreds of "
            f"companies with a single purchase."
        ),
        suggested_etfs=GLOBAL_EQUITY_ETFS,
        impact="A global ETF adds exposure to 1,500+ companies",
        confidence="medium",
        priority=2,
    ))
```

**Bond ETF catalogue:**

| Name | Ticker | ISIN | TER | Duration |
|------|--------|------|-----|----------|
| iShares Core Euro Govt Bond | IEGA.DE | IE00B4WXJJ64 | 0.09% | Intermediate |
| iShares Core Euro Corp Bond | IEAC.DE | IE00B3F81R35 | 0.20% | Intermediate |
| Vanguard EUR Eurozone Govt Bond | VETY.DE | IE00BH04GL39 | 0.07% | Intermediate |
| Xtrackers II EUR Corp Bond | XB4F.DE | LU0478205379 | 0.12% | Intermediate |
| iShares EUR HY Corp Bond | IHYG.DE | IE00B66F4759 | 0.50% | Short |
| iShares Global Aggregate Bond | AGGH.L | IE00BYX2JD69 | 0.10% | Intermediate |

**Global equity ETF catalogue (for "add equities" or "add broad ETF" recommendations):**

| Name | Ticker | ISIN | TER |
|------|--------|------|-----|
| iShares Core MSCI World | IWDA.L | IE00B4L5Y983 | 0.20% |
| Vanguard FTSE All-World | VWRL.L | IE00B3RBWM25 | 0.22% |
| Xtrackers MSCI World | XDWD.DE | IE00BJ0KDQ92 | 0.19% |
| SPDR MSCI ACWI | ACWI.L | IE00B6R52259 | 0.40% |

#### 3.1.4 Defensive Position Analysis

**Logic:**

```python
DEFENSIVE_SECTORS = {"Consumer Defensive", "Utilities", "Healthcare"}

defensive_pct = sum(
    ctx.sector_weights.get(s, 0.0) for s in DEFENSIVE_SECTORS
)

if defensive_pct < 10.0 and ctx.holding_count >= 5:
    recommendations.append(Recommendation(
        category="defensive",
        title="Add Defensive Holdings",
        rationale=(
            f"Only {defensive_pct:.0f}% of your portfolio is in traditionally "
            f"defensive sectors (utilities, consumer staples, healthcare). "
            f"These sectors tend to hold up better during market downturns."
        ),
        suggested_etfs=[
            # Global minimum volatility
            SuggestedETF(
                name="iShares Edge MSCI World Min Vol",
                ticker="MVOL.L",
                isin="IE00B8FHGS14",
                provider="iShares",
                ter="0.30%",
                index_tracked="MSCI World Minimum Volatility",
                why="Systematic low-volatility strategy across 300+ global stocks",
            ),
            # Consumer staples
            SuggestedETF(
                name="iShares S&P 500 Consumer Staples",
                ticker="IUCS.L",
                isin="IE00B40B8R38",
                provider="iShares",
                ter="0.15%",
                index_tracked="S&P 500 Consumer Staples",
                why="Recession-resistant consumer brands (P&G, Coca-Cola, Walmart)",
            ),
            # Utilities
            SuggestedETF(
                name="iShares S&P 500 Utilities",
                ticker="IUUS.L",
                isin="IE00B4KBBD01",
                provider="iShares",
                ter="0.15%",
                index_tracked="S&P 500 Utilities",
                why="Stable cash flows, regulated revenues, low beta",
            ),
        ],
        impact=f"Raising defensive allocation to 15-20% can reduce drawdowns by 10-15%",
        confidence="high" if defensive_pct < 5 else "medium",
        priority=1 if defensive_pct < 5 else 2,
    ))
```

#### 3.1.5 Income / Dividend Analysis

**Logic:**

```python
# Calculate trailing 12m yield (reuse from INC_001 rule data)
total_div_12m = sum(float(tx.quantity * tx.price) for tx in ctx.dividend_txs_12m)
yield_pct = (total_div_12m / float(ctx.total_value) * 100) if ctx.total_value else 0

if yield_pct < 1.0 and ctx.holding_count >= 5:
    recommendations.append(Recommendation(
        category="income",
        title="Boost Dividend Income",
        rationale=(
            f"Your trailing 12-month yield is {yield_pct:.1f}%. Adding high-dividend "
            f"ETFs can create a passive income stream while maintaining diversification."
        ),
        suggested_etfs=DIVIDEND_ETFS,
        impact=f"A 10-15% allocation to dividend ETFs could raise portfolio yield to ~2%",
        confidence="medium",
        priority=2,
    ))
```

**Dividend ETF catalogue:**

| Name | Ticker | ISIN | TER | Yield |
|------|--------|------|-----|-------|
| Vanguard FTSE All-World High Dividend Yield | VHYL.L | IE00B8GKDB10 | 0.29% | ~3.5% |
| iShares STOXX Global Select Dividend 100 | ISPA.DE | DE000A0F5UH1 | 0.46% | ~4.5% |
| SPDR S&P Euro Dividend Aristocrats | EUDV.DE | IE00B5M1WJ87 | 0.30% | ~3.0% |
| Xtrackers STOXX Global Sel. Dividend 100 | XGSD.DE | LU0292096186 | 0.50% | ~4.0% |

#### 3.1.6 Low-Correlation Asset Analysis

**Logic:**

This rule fires only when the slow-tier `RISK_007` (Correlated Holdings) was triggered, meaning average pairwise correlation > 0.70.

```python
# Check if RISK_007 fired
risk_007_items = [item for item in advice_items if item.rule_id == "RISK_007"]
if risk_007_items:
    avg_corr = risk_007_items[0].metadata.get("avg_correlation", 0)
    recommendations.append(Recommendation(
        category="low_correlation",
        title="Add Uncorrelated Assets",
        rationale=(
            f"Your holdings have an average correlation of {avg_corr:.2f}. "
            f"Adding assets with low or negative correlation to equities -- such as "
            f"government bonds, gold, or real estate -- would improve true diversification."
        ),
        suggested_etfs=[
            SuggestedETF(
                name="iShares Physical Gold ETC",
                ticker="IGLN.L",
                isin="IE00B4ND3602",
                provider="iShares",
                ter="0.12%",
                index_tracked="LBMA Gold Price",
                why="Gold historically has near-zero correlation with equities",
            ),
            SuggestedETF(
                name="iShares Core Euro Govt Bond",
                ticker="IEGA.DE",
                isin="IE00B4WXJJ64",
                provider="iShares",
                ter="0.09%",
                index_tracked="Bloomberg Euro Treasury Bond",
                why="Government bonds provide ballast during equity sell-offs",
            ),
            SuggestedETF(
                name="iShares Developed Markets Property Yield",
                ticker="IWDP.L",
                isin="IE00B1FZS350",
                provider="iShares",
                ter="0.59%",
                index_tracked="FTSE EPRA/NAREIT Developed Dividend+",
                why="Real estate returns have moderate equity correlation (~0.5)",
            ),
        ],
        impact="Adding 10-20% uncorrelated assets could reduce portfolio correlation to ~0.50",
        confidence="high",
        priority=1,
    ))
```

### 3.2 Recommendation Prioritisation

After all six passes, sort recommendations by:

1. `priority` ascending (1 = highest)
2. Within same priority, by `confidence` descending (`high` > `medium` > `low`)
3. Limit to **maximum 5 recommendations**

If there are more than 5, prefer diversity of categories (at most 2 per category).

### 3.3 What NOT to recommend (hard rules)

- NEVER recommend individual stocks or single-company instruments
- NEVER suggest specific purchase amounts, quantities, or allocation percentages in euros
- NEVER recommend leveraged, inverse, or structured products
- NEVER recommend crypto assets or speculative instruments
- Only recommend UCITS-compliant ETFs available on major European exchanges (Xetra, London SE, Euronext)
- ETF TER must be below 0.65%
- Always show at least 2 ETF options per recommendation to avoid the appearance of endorsing a single product

### 3.4 Response format

```jsonc
{
  "recommendations": [
    {
      "category": "sector_fill",
      "title": "Add Healthcare Exposure",
      "rationale": "Your portfolio has 0% in Healthcare vs. a global benchmark weight of 12%. This 12pp gap leaves you underexposed to the sector.",
      "suggested_etfs": [
        {
          "name": "iShares STOXX Europe 600 Health Care UCITS ETF",
          "ticker": "SXDPEX.DE",
          "isin": "DE000A0Q4R36",
          "provider": "iShares",
          "ter": "0.46%",
          "index_tracked": "STOXX Europe 600 Health Care",
          "why": "Broad European healthcare, 53 holdings, UCITS compliant"
        },
        {
          "name": "iShares S&P 500 Health Care Sector UCITS ETF",
          "ticker": "IUHC.L",
          "isin": "IE00B43HR379",
          "provider": "iShares",
          "ter": "0.15%",
          "index_tracked": "S&P 500 Health Care",
          "why": "US-focused healthcare with lower TER, includes JNJ, UNH, Pfizer"
        },
        {
          "name": "Xtrackers MSCI World Health Care UCITS ETF",
          "ticker": "XDWH.DE",
          "isin": "IE00BM67HK77",
          "provider": "Xtrackers",
          "ter": "0.25%",
          "index_tracked": "MSCI World Health Care",
          "why": "Global healthcare exposure across developed markets"
        }
      ],
      "impact": "Would reduce technology concentration from 62% to ~48% and add healthcare at ~12%",
      "confidence": "high",
      "priority": 1
    }
    // ... up to 5 recommendations
  ]
}
```

---

## Section 4: Portfolio Optimisation Scenarios

### What the user sees

2-3 "What If" scenario cards. Each shows a before/after comparison:

- Allocation pie chart (before vs. after)
- Key metrics table: sector HHI, country HHI, estimated volatility, estimated yield, number of sectors covered

### Scenario generation

Scenarios are derived from the top recommendations in Section 3. Each scenario models what the portfolio would look like if the user followed 1-2 recommendations.

**Logic:**

```python
def generate_scenarios(ctx: AdviceContext, recommendations: list[Recommendation]) -> list[Scenario]:
    scenarios = []

    # Scenario 1: Follow the #1 recommendation
    if recommendations:
        rec = recommendations[0]
        scenario = model_allocation_change(ctx, rec)
        scenarios.append(scenario)

    # Scenario 2: Follow all "high confidence" recommendations
    high_conf = [r for r in recommendations if r.confidence == "high"]
    if len(high_conf) >= 2:
        scenario = model_combined_change(ctx, high_conf)
        scenarios.append(scenario)

    # Scenario 3: "Balanced portfolio" -- what equal-weight across present sectors looks like
    scenario = model_equal_weight(ctx)
    scenarios.append(scenario)

    return scenarios[:3]
```

**Modelling a single recommendation change:**

The scenario assumes the user adds a new position equal to 10% of current portfolio value in the recommended asset class/sector. The existing positions are proportionally diluted.

```python
def model_allocation_change(ctx, rec):
    NEW_POSITION_WEIGHT = 10.0  # assume 10% of portfolio
    scale_factor = (100 - NEW_POSITION_WEIGHT) / 100

    after_sector_weights = {
        sector: weight * scale_factor
        for sector, weight in ctx.sector_weights.items()
    }

    # Add the new sector weight
    target_sector = rec.metadata.get("sector") or infer_sector(rec)
    after_sector_weights[target_sector] = (
        after_sector_weights.get(target_sector, 0) + NEW_POSITION_WEIGHT
    )

    # Compute HHI before and after
    hhi_before = sum(w**2 for w in ctx.sector_weights.values())
    hhi_after = sum(w**2 for w in after_sector_weights.values())

    return Scenario(
        title=rec.title,
        description=f"Adds ~10% position in {target_sector}",
        before_allocation=ctx.sector_weights,
        after_allocation=after_sector_weights,
        metrics_before={"sector_hhi": round(hhi_before), "sector_count": len(ctx.sector_weights)},
        metrics_after={"sector_hhi": round(hhi_after), "sector_count": len(after_sector_weights)},
    )
```

### Response format

```jsonc
{
  "scenarios": [
    {
      "title": "Add Healthcare Exposure",
      "description": "Adds ~10% position in Healthcare sector",
      "before": {
        "allocation": { "Technology": 62.0, "Financial Services": 20.0, "Energy": 18.0 },
        "metrics": {
          "sector_hhi": 4448,
          "sector_count": 3,
          "estimated_yield": 0.8
        }
      },
      "after": {
        "allocation": { "Technology": 55.8, "Financial Services": 18.0, "Energy": 16.2, "Healthcare": 10.0 },
        "metrics": {
          "sector_hhi": 3634,
          "sector_count": 4,
          "estimated_yield": 0.8
        }
      }
    }
    // ... up to 3 scenarios
  ]
}
```

---

## Section 5: Disclaimer

A persistent footer banner displayed at the bottom of the page and repeated inside the API response.

### Text

> **Important:** The information on this page is generated automatically for educational and informational purposes only. It does **not** constitute financial advice, an investment recommendation, or a solicitation to buy or sell any financial instrument. Past performance is not indicative of future results. The ETFs mentioned are examples only and not endorsements of specific products. Always conduct your own research and consult a qualified, licensed financial advisor before making any investment decisions. The authors of this application accept no liability for any financial loss arising from the use of this information.

### Response format

```jsonc
{
  "disclaimer": "Important: The information on this page is generated automatically for educational and informational purposes only. It does not constitute financial advice, an investment recommendation, or a solicitation to buy or sell any financial instrument. Past performance is not indicative of future results. The ETFs mentioned are examples only and not endorsements of specific products. Always conduct your own research and consult a qualified, licensed financial advisor before making any investment decisions. The authors of this application accept no liability for any financial loss arising from the use of this information."
}
```

---

## Combined API Response

A single endpoint returns all five sections:

```
GET /api/portfolios/<id>/advice/full/
```

```jsonc
{
  "health_score": {
    "overall_score": 72,
    "summary": "...",
    "sub_scores": { /* ... */ }
  },
  "top_actions": {
    "actions": [ /* ... */ ]
  },
  "recommendations": {
    "recommendations": [ /* ... */ ]
  },
  "scenarios": {
    "scenarios": [ /* ... */ ]
  },
  "advice_items": [ /* existing AdviceItem list for reference */ ],
  "has_pending_analysis": false,
  "disclaimer": "..."
}
```

**Caching:**

- Health score, top actions: same TTL as fast-tier (15 min)
- Recommendations and scenarios: same TTL as slow-tier (24 hours), since they depend on correlation data
- Cache key: `advice:full:{portfolio_id}`

---

## Implementation Plan

### Backend

| Step | File | Description |
|------|------|-------------|
| 1 | `advice/models.py` | Add `Recommendation`, `SuggestedETF`, `Scenario`, `HealthScore`, `TopAction` dataclasses |
| 2 | `advice/etf_catalogue.py` | Static ETF catalogue (sector, geographic, bond, dividend, defensive, correlation) |
| 3 | `advice/health_score.py` | `compute_health_score(items: list[AdviceItem]) -> HealthScore` |
| 4 | `advice/top_actions.py` | `derive_top_actions(items: list[AdviceItem]) -> list[TopAction]` |
| 5 | `advice/recommendations.py` | `RecommendationEngine(ctx, items).evaluate() -> list[Recommendation]` |
| 6 | `advice/scenarios.py` | `generate_scenarios(ctx, recs) -> list[Scenario]` |
| 7 | `advice/engine.py` | Add `evaluate_full()` method that orchestrates all sections |
| 8 | `views.py` | Add `PortfolioFullAdviceView` |
| 9 | `urls.py` | Wire up `advice/full/` endpoint |
| 10 | `serializers.py` | Add serializers for new response types |
| 11 | `tests/test_recommendations.py` | Unit tests for gap analysis logic |

### Frontend

| Step | File | Description |
|------|------|-------------|
| 1 | `lib/api/portfolios.ts` | Add `getFullAdvice()` API call |
| 2 | `types/api.ts` | Add TypeScript types for full advice response |
| 3 | `(app)/advice/page.tsx` | Main AI Advice page layout |
| 4 | `components/advice/HealthScoreGauge.tsx` | Radial gauge component |
| 5 | `components/advice/TopActions.tsx` | Prioritised action cards |
| 6 | `components/advice/Recommendations.tsx` | "What to Buy" section with ETF cards |
| 7 | `components/advice/Scenarios.tsx` | Before/after pie charts |
| 8 | `components/advice/Disclaimer.tsx` | Disclaimer banner |

---

## Thresholds Summary

| Parameter | Value | Used in |
|-----------|-------|---------|
| Sector gap trigger | >= 5pp vs. MSCI ACWI | Sector gap analysis |
| Sector gap high confidence | >= 10pp | Sector gap analysis |
| Geographic gap trigger | >= 8pp vs. MSCI ACWI | Geographic gap analysis |
| Geographic gap high confidence | >= 15pp | Geographic gap analysis |
| All-equity trigger | > 90% equities, < 5% bonds | Asset class gap |
| Defensive trigger | < 10% in defensive sectors | Defensive analysis |
| Income trigger | < 1.0% trailing yield | Income analysis |
| Correlation trigger | avg pairwise > 0.70 | Low-correlation analysis |
| Max recommendations shown | 5 | Prioritisation |
| Max ETFs per recommendation | 3 | ETF selection |
| Max TER for recommended ETFs | 0.65% | ETF catalogue filter |
| Scenario new-position weight | 10% of portfolio | Scenario modelling |
| Health score penalty (critical) | -40 | Health score |
| Health score penalty (warning) | -20 | Health score |
| Health score penalty (info) | -5 | Health score |
| Health score bonus (positive) | +5 (cap +10/category) | Health score |
