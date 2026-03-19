from __future__ import annotations

import logging
import threading

from django.core.cache import cache

from apps.market_data.services import MarketDataService
from apps.portfolios.models import Portfolio

from .context import DISCLAIMER, build_advice_context
from .dedup import PRIORITY_ORDER, deduplicate
from .health_score import compute_health_score
from .models import AdviceContext, AdviceItem, AdviceResponse, FullAdviceResponse
from .recommendations import RecommendationEngine
from .scenarios import generate_scenarios
from .top_actions import derive_top_actions

# Graceful imports for rule modules (Task B creates these)
try:
    from .rules_fast import FastRules
except ImportError:
    FastRules = None  # type: ignore[assignment,misc]

try:
    from .rules_slow import SlowRules
except ImportError:
    SlowRules = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

FAST_CACHE_TTL = 15 * 60  # 15 minutes
SLOW_CACHE_TTL = 24 * 60 * 60  # 24 hours
FULL_CACHE_TTL = 15 * 60  # 15 minutes (matches fast tier)
MAX_ITEMS = 10

FULL_ADVICE_DISCLAIMER = (
    "Important: The information on this page is generated automatically for "
    "educational and informational purposes only. It does not constitute "
    "financial advice, an investment recommendation, or a solicitation to buy "
    "or sell any financial instrument. Past performance is not indicative of "
    "future results. The ETFs mentioned are examples only and not endorsements "
    "of specific products. Always conduct your own research and consult a "
    "qualified, licensed financial advisor before making any investment "
    "decisions. The authors of this application accept no liability for any "
    "financial loss arising from the use of this information."
)


class AdviceEngine:
    """Orchestrates two-tier advice evaluation with caching, dedup, and sorting."""

    def __init__(
        self,
        portfolio: Portfolio,
        service: MarketDataService | None = None,
    ):
        self.portfolio = portfolio
        self.service = service or MarketDataService()

    # ── Public API ───────────────────────────────────────────

    def evaluate(self) -> AdviceResponse:
        """Main entry point. Returns fast-tier results immediately,
        flags if slow tier is pending."""
        ctx = build_advice_context(self.portfolio, self.service)

        fast_items = self._get_fast_results(ctx)
        slow_items = self._get_slow_results(ctx)

        has_pending = slow_items is None
        if has_pending:
            self._trigger_slow_computation(ctx)

        merged = fast_items + (slow_items or [])
        merged = deduplicate(merged)
        merged = self._sort_and_limit(merged)

        return AdviceResponse(
            items=merged,
            has_pending_analysis=has_pending,
            disclaimer=DISCLAIMER,
        )

    def evaluate_full(self) -> FullAdviceResponse:
        """Full advice evaluation: health score, top actions, recommendations,
        scenarios, and all advice items."""
        cache_key = f"advice:full:{self.portfolio.id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        ctx = build_advice_context(self.portfolio, self.service)

        fast_items = self._get_fast_results(ctx)
        slow_items = self._get_slow_results(ctx)

        has_pending = slow_items is None
        if has_pending:
            self._trigger_slow_computation(ctx)

        all_items = fast_items + (slow_items or [])
        all_items = deduplicate(all_items)

        # Compute all sections
        health_score = compute_health_score(all_items)
        top_actions = derive_top_actions(all_items)
        recommendations = RecommendationEngine(ctx, all_items).evaluate()
        scenarios = generate_scenarios(ctx, recommendations)

        # Sort and limit advice items for the response
        display_items = self._sort_and_limit(list(all_items))

        result = FullAdviceResponse(
            health_score=health_score,
            top_actions=top_actions,
            recommendations=recommendations,
            scenarios=scenarios,
            advice_items=display_items,
            has_pending_analysis=has_pending,
            disclaimer=FULL_ADVICE_DISCLAIMER,
        )

        cache.set(cache_key, result, FULL_CACHE_TTL)
        return result

    # ── Fast tier ────────────────────────────────────────────

    def _get_fast_results(self, ctx: AdviceContext) -> list[AdviceItem]:
        """Evaluate all fast rules, cache result."""
        cache_key = f"advice:fast:{self.portfolio.id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        if FastRules is None:
            logger.debug("FastRules not yet implemented, returning empty list")
            return []

        items = FastRules(ctx).evaluate_all()
        cache.set(cache_key, items, FAST_CACHE_TTL)
        return items

    # ── Slow tier ────────────────────────────────────────────

    def _get_slow_results(self, ctx: AdviceContext) -> list[AdviceItem] | None:
        """Return cached slow results, or None if not yet computed."""
        cache_key = f"advice:slow:{self.portfolio.id}"
        return cache.get(cache_key)

    def _trigger_slow_computation(self, ctx: AdviceContext) -> None:
        """Spawn a daemon thread to compute slow rules and store in cache."""
        thread = threading.Thread(
            target=self._compute_slow_rules,
            args=(ctx,),
            daemon=True,
        )
        thread.start()

    def _compute_slow_rules(self, ctx: AdviceContext) -> None:
        """Compute slow rules and store in cache. Runs in a background thread."""
        cache_key = f"advice:slow:{self.portfolio.id}"
        try:
            if SlowRules is None:
                logger.debug("SlowRules not yet implemented, caching empty list")
                cache.set(cache_key, [], SLOW_CACHE_TTL)
                return

            items = SlowRules(ctx, self.service).evaluate_all()
            cache.set(cache_key, items, SLOW_CACHE_TTL)
        except Exception:
            logger.exception(
                "Failed to compute slow rules for portfolio %s",
                self.portfolio.id,
            )
            # Cache an empty list so we don't keep retrying on every request
            cache.set(cache_key, [], SLOW_CACHE_TTL)

    # ── Sorting & limiting ───────────────────────────────────

    @staticmethod
    def _sort_and_limit(items: list[AdviceItem]) -> list[AdviceItem]:
        """Sort by priority, limit to MAX_ITEMS, ensure at least 1 positive
        item is included if available."""
        items.sort(key=lambda it: PRIORITY_ORDER.get(it.priority, 99))

        if len(items) <= MAX_ITEMS:
            return items

        # Take the first 9 items (highest priority)
        result = items[: MAX_ITEMS - 1]

        # Check if there's already a positive item in the first 9
        has_positive = any(it.priority == "positive" for it in result)

        if not has_positive:
            # Scan the remainder for the first positive item
            for item in items[MAX_ITEMS - 1 :]:
                if item.priority == "positive":
                    result.append(item)
                    return result

        # No positive found (or already present): take the 10th item normally
        result.append(items[MAX_ITEMS - 1])
        return result
