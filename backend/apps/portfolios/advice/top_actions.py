from __future__ import annotations

import logging

from .dedup import PRIORITY_ORDER
from .models import AdviceItem, TopAction

logger = logging.getLogger(__name__)

ACTION_TEMPLATES: dict[str, dict[str, str]] = {
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


def _safe_format(template: str, metadata: dict) -> str:
    """Format template string with metadata, falling back gracefully."""
    try:
        return template.format(**metadata)
    except (KeyError, ValueError, IndexError):
        # Remove unresolvable placeholders
        return template


def derive_top_actions(items: list[AdviceItem]) -> list[TopAction]:
    """Derive top 5 action cards from advice items."""
    # Sort by priority (critical first)
    sorted_items = sorted(items, key=lambda it: PRIORITY_ORDER.get(it.priority, 99))

    seen_actions: set[str] = set()
    actions: list[TopAction] = []

    for item in sorted_items:
        template = ACTION_TEMPLATES.get(item.rule_id)
        if template is None:
            continue

        action_text = _safe_format(template["action"], item.metadata)
        impact_text = _safe_format(template["impact"], item.metadata)

        # Deduplicate by action text
        if action_text in seen_actions:
            continue
        seen_actions.add(action_text)

        actions.append(
            TopAction(
                action=action_text,
                rationale=item.message,
                impact=impact_text,
                urgency=template["urgency"],
                related_rule_id=item.rule_id,
                related_holdings=item.holdings,
            )
        )

        if len(actions) >= 5:
            break

    return actions
