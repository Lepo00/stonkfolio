from __future__ import annotations

from .models import AdviceItem, HealthScore

# Map AdviceItem category → health score sub-score category
CATEGORY_MAP: dict[str, str] = {
    "diversification": "diversification",
    "risk": "risk",
    "performance": "performance",
    "income": "income",
    "cost": "cost",
    "health": "health",
    # Behavioral and technical items map to risk
    "behavioral": "risk",
    "technical": "performance",
}

CATEGORY_WEIGHTS: dict[str, int] = {
    "diversification": 25,
    "risk": 25,
    "performance": 20,
    "income": 10,
    "cost": 10,
    "health": 10,
}

PENALTY_MAP: dict[str, int] = {
    "critical": -40,
    "warning": -20,
    "info": -5,
    "positive": 5,
}

POSITIVE_CAP_PER_CATEGORY = 10

CATEGORY_PHRASES: dict[str, str] = {
    "diversification": "diversification gaps",
    "risk": "concentration risk",
    "performance": "underperforming positions",
    "income": "low income generation",
    "cost": "high fee drag",
    "health": "portfolio hygiene issues",
}


def compute_health_score(items: list[AdviceItem]) -> HealthScore:
    """Compute a penalty-based health score from advice items."""
    # Initialise sub-scores at 100
    scores: dict[str, int] = {cat: 100 for cat in CATEGORY_WEIGHTS}
    positive_bonus: dict[str, int] = {cat: 0 for cat in CATEGORY_WEIGHTS}
    item_counts: dict[str, int] = {cat: 0 for cat in CATEGORY_WEIGHTS}

    for item in items:
        sub_cat = CATEGORY_MAP.get(item.category)
        if sub_cat is None:
            continue

        penalty = PENALTY_MAP.get(item.priority, 0)
        item_counts[sub_cat] += 1

        if penalty > 0:
            # Positive bonus, capped
            remaining = POSITIVE_CAP_PER_CATEGORY - positive_bonus[sub_cat]
            bonus = min(penalty, remaining)
            if bonus > 0:
                scores[sub_cat] += bonus
                positive_bonus[sub_cat] += bonus
        else:
            scores[sub_cat] += penalty

    # Clamp each sub-score to [0, 100]
    for cat in scores:
        scores[cat] = max(0, min(100, scores[cat]))

    # Overall weighted score
    overall = sum(scores[cat] * CATEGORY_WEIGHTS[cat] for cat in CATEGORY_WEIGHTS) / 100
    overall = round(overall)

    # Summary sentence
    if overall >= 80:
        prefix = "Your portfolio is in strong shape"
    elif overall >= 60:
        prefix = "Your portfolio is on the right track"
    elif overall >= 40:
        prefix = "Your portfolio needs attention"
    else:
        prefix = "Your portfolio has significant issues"

    weakest = sorted(scores.items(), key=lambda x: x[1])[:2]
    suffix = " and ".join(CATEGORY_PHRASES[c] for c, _ in weakest)
    summary = f"{prefix}, with {suffix}."

    # Build sub_scores dict
    sub_scores = {
        cat: {
            "score": scores[cat],
            "weight": CATEGORY_WEIGHTS[cat],
            "item_count": item_counts[cat],
        }
        for cat in CATEGORY_WEIGHTS
    }

    return HealthScore(
        overall_score=overall,
        summary=summary,
        sub_scores=sub_scores,
    )
