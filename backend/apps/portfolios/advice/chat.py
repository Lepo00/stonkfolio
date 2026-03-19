from __future__ import annotations

import re

from .models import AdviceContext, AdviceItem, ChatMessage, ChatResponse, Recommendation

QUESTION_PATTERNS: list[tuple[str, str]] = [
    (r"(how|what).*(diversif|spread|concentrated)", "diversification"),
    (r"(what|which).*(buy|invest|add|purchase)", "what_to_buy"),
    (r"(how|what).*(perform|return|gain|loss)", "performance"),
    (r"(what|which).*(risk|danger|concern)", "risk"),
    (r"(how|what).*(dividend|income|yield)", "income"),
    (r"(what|which).*(fee|cost|expense)", "cost"),
    (r"(what|which).*(sell|remove|cut|trim)", "what_to_sell"),
    (r"(how).*(health|score|rating)", "health"),
    (r"(what|which).*(sector|industry)", "sectors"),
    (r"(what|which).*(country|region|geograph)", "geography"),
]

FALLBACK_RESPONSE = (
    "I can help you understand your portfolio better. Try asking about:\n"
    "- How diversified is my portfolio?\n"
    "- What should I buy next?\n"
    "- How is my portfolio performing?\n"
    "- What are my biggest risks?\n"
    "- What dividends am I earning?\n"
    "- What fees am I paying?\n"
    "- What should I sell?\n"
    "- How is my health score calculated?\n"
    "- What sectors am I invested in?\n"
    "- What countries am I exposed to?"
)


def detect_intent(question: str) -> str | None:
    """Match a user question to an intent category."""
    q = question.lower().strip()
    for pattern, intent in QUESTION_PATTERNS:
        if re.search(pattern, q):
            return intent
    return None


def _answer_diversification(ctx: AdviceContext, items: list[AdviceItem]) -> str:
    parts = [f"Your portfolio has {ctx.holding_count} holdings across {len(ctx.sector_weights)} sectors."]

    if ctx.sector_weights:
        top = max(ctx.sector_weights, key=ctx.sector_weights.get)  # type: ignore[arg-type]
        parts.append(f"The largest sector is {top} at {ctx.sector_weights[top]:.1f}%.")

    # Check for concentration warnings
    div_items = [i for i in items if i.category == "diversification"]
    if div_items:
        parts.append(f"There are {len(div_items)} diversification concern(s):")
        for item in div_items[:3]:
            parts.append(f"  - {item.title}")
    else:
        parts.append("No major diversification concerns were found.")

    return "\n".join(parts)


def _answer_what_to_buy(
    ctx: AdviceContext,
    recs: list[Recommendation],
) -> str:
    if not recs:
        return "Based on the current analysis, no specific purchase recommendations have been generated. Your portfolio may already be well-balanced."

    parts = [f"Based on gap analysis, here are the top {len(recs)} recommendation(s):"]
    for i, rec in enumerate(recs, 1):
        parts.append(f"\n{i}. **{rec.title}** (confidence: {rec.confidence})")
        parts.append(f"   {rec.rationale}")
        if rec.suggested_etfs:
            etf = rec.suggested_etfs[0]
            parts.append(f"   Consider: {etf.name} ({etf.ticker}, TER {etf.ter})")

    parts.append(
        "\nRemember: These are educational suggestions only, not financial advice. Always do your own research."
    )
    return "\n".join(parts)


def _answer_performance(ctx: AdviceContext, items: list[AdviceItem]) -> str:
    parts = [f"Your overall portfolio return is {ctx.overall_return_pct:.1f}%."]

    # Find best and worst holdings
    priced = [h for h in ctx.holdings if h.return_pct is not None]
    if priced:
        best = max(priced, key=lambda h: h.return_pct)  # type: ignore[arg-type,return-value]
        worst = min(priced, key=lambda h: h.return_pct)  # type: ignore[arg-type,return-value]
        parts.append(f"Best performer: {best.ticker} at {best.return_pct:+.1f}%")
        parts.append(f"Worst performer: {worst.ticker} at {worst.return_pct:+.1f}%")

    perf_items = [i for i in items if i.category == "performance"]
    if perf_items:
        parts.append(f"\nPerformance concerns ({len(perf_items)}):")
        for item in perf_items[:3]:
            parts.append(f"  - {item.title}")

    return "\n".join(parts)


def _answer_risk(ctx: AdviceContext, items: list[AdviceItem]) -> str:
    risk_items = [i for i in items if i.category == "risk"]
    if not risk_items:
        return "No significant risk concerns were identified in your portfolio."

    parts = [f"There are {len(risk_items)} risk concern(s) in your portfolio:"]
    for item in risk_items[:5]:
        badge = f"[{item.priority.upper()}]" if item.priority in ("critical", "warning") else ""
        parts.append(f"  - {badge} {item.title}: {item.message}")

    return "\n".join(parts)


def _answer_income(ctx: AdviceContext) -> str:
    total_div = sum(float(tx.quantity * tx.price) for tx in ctx.dividend_txs_12m)
    yield_pct = (total_div / float(ctx.total_value) * 100) if ctx.total_value else 0.0

    parts = [
        f"Trailing 12-month dividends received: {total_div:.2f}",
        f"Trailing 12-month yield: {yield_pct:.2f}%",
        f"Number of dividend payments: {len(ctx.dividend_txs_12m)}",
    ]

    if yield_pct < 1.0:
        parts.append("\nYour yield is below 1%. Consider adding high-dividend ETFs if passive income is a goal.")
    return "\n".join(parts)


def _answer_cost(ctx: AdviceContext) -> str:
    fee_ratio = (float(ctx.fee_total) / float(ctx.total_value) * 100) if ctx.total_value else 0.0
    parts = [
        f"Total fees paid: {float(ctx.fee_total):.2f}",
        f"Fee ratio (fees / portfolio value): {fee_ratio:.2f}%",
        f"Total transactions: {len(ctx.all_transactions)}",
    ]
    return "\n".join(parts)


def _answer_what_to_sell(ctx: AdviceContext, items: list[AdviceItem]) -> str:
    candidates = []

    # Deep losers
    for item in items:
        if item.rule_id == "PERF_004":
            candidates.append(f"- {', '.join(item.holdings)}: Deep loss ({item.title})")
        elif item.rule_id == "BEHAV_001":
            candidates.append(f"- {', '.join(item.holdings)}: Stale losing position ({item.title})")
        elif item.rule_id == "HEALTH_001":
            candidates.append(f"- Negligible positions: {item.title}")

    if not candidates:
        return "No holdings are flagged for potential selling at this time."

    parts = ["Holdings you might consider reviewing for potential sale:"]
    parts.extend(candidates[:5])
    parts.append(
        "\nThese are not sell recommendations. Always consider tax implications "
        "and your investment thesis before selling."
    )
    return "\n".join(parts)


def _answer_health(ctx: AdviceContext, items: list[AdviceItem]) -> str:
    # We re-compute a simple version here for the chat
    from .health_score import compute_health_score

    score = compute_health_score(items)
    parts = [
        f"Portfolio Health Score: {score.overall_score}/100",
        score.summary,
        "\nSub-scores:",
    ]
    for cat, data in score.sub_scores.items():
        parts.append(f"  - {cat.title()}: {data['score']}/100 ({data['item_count']} items)")

    return "\n".join(parts)


def _answer_sectors(ctx: AdviceContext) -> str:
    if not ctx.sector_weights:
        return "No sector data is available for your holdings."

    sorted_sectors = sorted(ctx.sector_weights.items(), key=lambda x: -x[1])
    parts = ["Your sector allocation:"]
    for sector, weight in sorted_sectors:
        parts.append(f"  - {sector}: {weight:.1f}%")

    return "\n".join(parts)


def _answer_geography(ctx: AdviceContext) -> str:
    if not ctx.country_weights:
        return "No country data is available for your holdings."

    sorted_countries = sorted(ctx.country_weights.items(), key=lambda x: -x[1])
    parts = ["Your geographic allocation:"]
    for country, weight in sorted_countries:
        parts.append(f"  - {country}: {weight:.1f}%")

    return "\n".join(parts)


def answer_question(
    question: str,
    ctx: AdviceContext,
    items: list[AdviceItem],
    recs: list[Recommendation],
) -> str:
    """Generate a contextual answer from portfolio data based on detected intent."""
    intent = detect_intent(question)

    if intent == "diversification":
        return _answer_diversification(ctx, items)
    elif intent == "what_to_buy":
        return _answer_what_to_buy(ctx, recs)
    elif intent == "performance":
        return _answer_performance(ctx, items)
    elif intent == "risk":
        return _answer_risk(ctx, items)
    elif intent == "income":
        return _answer_income(ctx)
    elif intent == "cost":
        return _answer_cost(ctx)
    elif intent == "what_to_sell":
        return _answer_what_to_sell(ctx, items)
    elif intent == "health":
        return _answer_health(ctx, items)
    elif intent == "sectors":
        return _answer_sectors(ctx)
    elif intent == "geography":
        return _answer_geography(ctx)
    else:
        return FALLBACK_RESPONSE


def build_context_summary(ctx: AdviceContext) -> str:
    """Build a short summary of portfolio context for the chat response."""
    return (
        f"Portfolio with {ctx.holding_count} holdings, "
        f"total value {float(ctx.total_value):.2f}, "
        f"overall return {ctx.overall_return_pct:.1f}%, "
        f"across {len(ctx.sector_weights)} sectors "
        f"and {len(ctx.country_weights)} countries."
    )


def handle_chat_message(
    message: str,
    ctx: AdviceContext,
    items: list[AdviceItem],
    recs: list[Recommendation],
) -> ChatResponse:
    """Process a chat message and return a response."""
    answer = answer_question(message, ctx, items, recs)

    messages = [
        ChatMessage(role="user", content=message),
        ChatMessage(role="assistant", content=answer),
    ]

    return ChatResponse(
        messages=messages,
        context_summary=build_context_summary(ctx),
    )
