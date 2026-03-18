from __future__ import annotations

from .models import AdviceItem

# Map of (rule_id that gets dropped) -> (rule_id that supersedes it)
SUPERSEDE_MAP: dict[str, str] = {
    "PERF_002": "PERF_004",  # deep loser supersedes underperformer for same ticker
}

PRIORITY_ORDER: dict[str, int] = {
    "critical": 0,
    "warning": 1,
    "info": 2,
    "positive": 3,
}


def deduplicate(items: list[AdviceItem]) -> list[AdviceItem]:
    """Remove lower-severity duplicates for the same holding where rules overlap.

    For each pair defined in SUPERSEDE_MAP, if both rules fire for overlapping
    tickers, the lower-severity rule is dropped.
    """
    # Build a lookup: rule_id -> set of tickers for that rule
    rule_tickers: dict[str, set[str]] = {}
    for item in items:
        rule_tickers.setdefault(item.rule_id, set()).update(item.holdings)

    # Determine which (rule_id, ticker) pairs should be suppressed
    suppressed_rules: set[str] = set()
    for lower_rule, higher_rule in SUPERSEDE_MAP.items():
        if lower_rule in rule_tickers and higher_rule in rule_tickers:
            # If there is any ticker overlap, suppress the lower rule
            overlap = rule_tickers[lower_rule] & rule_tickers[higher_rule]
            if overlap:
                suppressed_rules.add(lower_rule)

    if not suppressed_rules:
        return items

    # Filter: for suppressed rules, only drop items whose tickers overlap
    # with the superseding rule's tickers
    result: list[AdviceItem] = []
    for item in items:
        if item.rule_id in suppressed_rules:
            higher_rule = SUPERSEDE_MAP[item.rule_id]
            higher_tickers = rule_tickers.get(higher_rule, set())
            # Drop this item if all its tickers are covered by the higher rule
            if set(item.holdings) <= higher_tickers:
                continue
        result.append(item)

    return result
