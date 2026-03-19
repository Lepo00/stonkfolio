from __future__ import annotations

from .models import AdviceContext, Recommendation, Scenario

NEW_POSITION_WEIGHT = 10.0  # assume 10% of portfolio

# Map recommendation categories to likely sector names
CATEGORY_TO_SECTOR: dict[str, str] = {
    "asset_class": "Fixed Income",
    "defensive": "Consumer Defensive",
    "income": "High Dividend",
    "low_correlation": "Uncorrelated Assets",
}


def _infer_sector(rec: Recommendation) -> str:
    """Infer the target sector from a recommendation."""
    # For sector_fill, the title is "Add {Sector} Exposure"
    if rec.category == "sector_fill" and rec.title.startswith("Add ") and rec.title.endswith(" Exposure"):
        return rec.title[4:-9]  # strip "Add " and " Exposure"

    # For geographic, the title is "Add {Region} Exposure"
    if rec.category == "geographic" and rec.title.startswith("Add ") and rec.title.endswith(" Exposure"):
        return rec.title[4:-9]

    return CATEGORY_TO_SECTOR.get(rec.category, "New Position")


def _compute_hhi(weights: dict[str, float]) -> int:
    """Compute Herfindahl-Hirschman Index from weight percentages."""
    return round(sum(w**2 for w in weights.values()))


def _dilute_weights(weights: dict[str, float], new_weight: float) -> dict[str, float]:
    """Scale existing weights down to make room for a new position."""
    scale_factor = (100 - new_weight) / 100
    return {sector: weight * scale_factor for sector, weight in weights.items()}


def model_allocation_change(ctx: AdviceContext, rec: Recommendation) -> Scenario:
    """Model a single recommendation as a ~10% new position."""
    target_sector = _infer_sector(rec)

    after_weights = _dilute_weights(ctx.sector_weights, NEW_POSITION_WEIGHT)
    after_weights[target_sector] = after_weights.get(target_sector, 0) + NEW_POSITION_WEIGHT

    hhi_before = _compute_hhi(ctx.sector_weights)
    hhi_after = _compute_hhi(after_weights)

    return Scenario(
        title=rec.title,
        description=f"Adds ~10% position in {target_sector}",
        before_allocation=dict(ctx.sector_weights),
        after_allocation=after_weights,
        metrics_before={
            "sector_hhi": hhi_before,
            "sector_count": len(ctx.sector_weights),
        },
        metrics_after={
            "sector_hhi": hhi_after,
            "sector_count": len(after_weights),
        },
    )


def model_combined_change(ctx: AdviceContext, recs: list[Recommendation]) -> Scenario:
    """Model following all high-confidence recommendations (each at reduced weight)."""
    per_rec_weight = min(NEW_POSITION_WEIGHT, 30.0 / len(recs)) if recs else NEW_POSITION_WEIGHT
    total_new_weight = per_rec_weight * len(recs)

    after_weights = _dilute_weights(ctx.sector_weights, total_new_weight)

    sectors_added = []
    for rec in recs:
        target_sector = _infer_sector(rec)
        after_weights[target_sector] = after_weights.get(target_sector, 0) + per_rec_weight
        sectors_added.append(target_sector)

    hhi_before = _compute_hhi(ctx.sector_weights)
    hhi_after = _compute_hhi(after_weights)

    return Scenario(
        title="Follow All High-Confidence Recommendations",
        description=f"Adds positions in {', '.join(sectors_added)}",
        before_allocation=dict(ctx.sector_weights),
        after_allocation=after_weights,
        metrics_before={
            "sector_hhi": hhi_before,
            "sector_count": len(ctx.sector_weights),
        },
        metrics_after={
            "sector_hhi": hhi_after,
            "sector_count": len(after_weights),
        },
    )


def model_equal_weight(ctx: AdviceContext) -> Scenario:
    """Model equal-weighting across present sectors."""
    sectors = list(ctx.sector_weights.keys())
    if not sectors:
        return Scenario(
            title="Equal-Weight Portfolio",
            description="No sectors to rebalance",
            before_allocation={},
            after_allocation={},
            metrics_before={"sector_hhi": 0, "sector_count": 0},
            metrics_after={"sector_hhi": 0, "sector_count": 0},
        )

    equal_weight = 100.0 / len(sectors)
    after_weights = {sector: round(equal_weight, 2) for sector in sectors}

    hhi_before = _compute_hhi(ctx.sector_weights)
    hhi_after = _compute_hhi(after_weights)

    return Scenario(
        title="Equal-Weight Portfolio",
        description=f"Rebalances all {len(sectors)} sectors to equal weight ({equal_weight:.1f}% each)",
        before_allocation=dict(ctx.sector_weights),
        after_allocation=after_weights,
        metrics_before={
            "sector_hhi": hhi_before,
            "sector_count": len(ctx.sector_weights),
        },
        metrics_after={
            "sector_hhi": hhi_after,
            "sector_count": len(after_weights),
        },
    )


def generate_scenarios(
    ctx: AdviceContext,
    recommendations: list[Recommendation],
) -> list[Scenario]:
    """Generate up to 3 what-if scenarios from recommendations."""
    scenarios: list[Scenario] = []

    # Scenario 1: Follow the #1 recommendation
    if recommendations:
        scenarios.append(model_allocation_change(ctx, recommendations[0]))

    # Scenario 2: Follow all high-confidence recommendations
    high_conf = [r for r in recommendations if r.confidence == "high"]
    if len(high_conf) >= 2:
        scenarios.append(model_combined_change(ctx, high_conf))

    # Scenario 3: Equal-weight across present sectors
    scenarios.append(model_equal_weight(ctx))

    return scenarios[:3]
