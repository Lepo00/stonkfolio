import itertools
import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.market_data.services import BENCHMARK_MAP, MarketDataService

from .advice import AdviceEngine
from .advice.chat import handle_chat_message
from .advice.context import DISCLAIMER, build_advice_context
from .advice.engine import FULL_ADVICE_DISCLAIMER
from .advice.recommendations import RecommendationEngine
from .models import Holding, Portfolio, Transaction, TransactionType
from .returns import _build_daily_portfolio_values, calculate_twr, calculate_xirr
from .risk_metrics import calculate_risk_metrics
from .serializers import (
    AdviceResponseSerializer,
    ChatRequestSerializer,
    ChatResponseSerializer,
    CorrelationResponseSerializer,
    FullAdviceResponseSerializer,
    HoldingSerializer,
    PortfolioSerializer,
    RebalanceResponseSerializer,
    RiskMetricsSerializer,
    TransactionSerializer,
)

logger = logging.getLogger(__name__)


class PortfolioViewSet(viewsets.ModelViewSet):
    serializer_class = PortfolioSerializer
    ordering = ["-created_at"]

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class HoldingListView(generics.ListAPIView):
    serializer_class = HoldingSerializer
    ordering = ["id"]

    def get_queryset(self):
        return Holding.objects.filter(
            portfolio_id=self.kwargs["portfolio_id"],
            portfolio__user=self.request.user,
        ).select_related("instrument")


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    filterset_fields = ["type", "instrument__ticker"]
    ordering_fields = ["date", "type"]
    ordering = ["-date"]

    def get_queryset(self):
        if "portfolio_id" in self.kwargs:
            return Transaction.objects.filter(
                portfolio_id=self.kwargs["portfolio_id"],
                portfolio__user=self.request.user,
            ).select_related("instrument")
        return Transaction.objects.filter(
            portfolio__user=self.request.user,
        ).select_related("instrument")


class PortfolioSummaryView(APIView):
    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        holdings = portfolio.holdings.select_related("instrument").all()
        service = MarketDataService()

        total_value = Decimal("0")
        total_cost = Decimal("0")

        for h in holdings:
            total_cost += h.quantity * h.avg_buy_price
            try:
                price_result = service.get_current_price(h.instrument)
                total_value += h.quantity * price_result.price
            except Exception:
                total_value += h.quantity * h.avg_buy_price  # fallback to cost basis

        first_tx = portfolio.transactions.order_by("date").values_list("date", flat=True).first()

        # Calculate advanced return metrics (cached for 15 minutes)
        twr_cache_key = f"twr:{portfolio_id}"
        xirr_cache_key = f"xirr:{portfolio_id}"

        twr = cache.get(twr_cache_key)
        if twr is None:
            twr = calculate_twr(portfolio, service)
            cache.set(twr_cache_key, twr, 15 * 60)

        xirr_val = cache.get(xirr_cache_key)
        if xirr_val is None:
            xirr_val = calculate_xirr(portfolio, service)
            cache.set(xirr_cache_key, xirr_val, 15 * 60)

        # Benchmark return
        benchmark_key = request.query_params.get("benchmark")
        benchmark_return_pct = None

        if benchmark_key and first_tx:
            benchmark_series = service.get_benchmark_series(benchmark_key, first_tx, date.today())
            if benchmark_series and len(benchmark_series) >= 2:
                start_val = Decimal(benchmark_series[0]["value"])
                end_val = Decimal(benchmark_series[-1]["value"])
                if start_val > 0:
                    benchmark_return_pct = f"{((end_val - start_val) / start_val * 100):.2f}"

        # Risk metrics (cached for 24 hours inside calculate_risk_metrics)
        risk_metrics_raw = calculate_risk_metrics(portfolio, service)
        risk_metrics_serializer = RiskMetricsSerializer(risk_metrics_raw)

        return Response(
            {
                "total_value": f"{total_value:.2f}",
                "total_cost": f"{total_cost:.2f}",
                "total_gain_loss": f"{total_value - total_cost:.2f}",
                "total_return_pct": f"{((total_value - total_cost) / total_cost * 100):.2f}" if total_cost else "0.00",
                "first_transaction_date": str(first_tx) if first_tx else None,
                "twr_return_pct": f"{twr:.2f}" if twr is not None else None,
                "xirr_return_pct": f"{xirr_val:.2f}" if xirr_val is not None else None,
                "benchmark_return_pct": benchmark_return_pct,
                "risk_metrics": risk_metrics_serializer.data,
            }
        )


PERIOD_MAP = {
    "1W": timedelta(weeks=1),
    "1M": timedelta(days=30),
    "3M": timedelta(days=90),
    "6M": timedelta(days=180),
    "1Y": timedelta(days=365),
}


class PortfolioPerformanceView(APIView):
    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        period = request.query_params.get("period", "1M")
        service = MarketDataService()

        if period == "ALL":
            first_tx = portfolio.transactions.order_by("date").first()
            start = first_tx.date if first_tx else date.today()
        else:
            delta = PERIOD_MAP.get(period, timedelta(days=30))
            start = date.today() - delta

        end = date.today()

        series_map = _build_daily_portfolio_values(portfolio, service, start, end)

        series = [{"date": str(d), "value": f"{v:.2f}"} for d, v in sorted(series_map.items())]

        # Handle benchmark
        benchmark_key = request.query_params.get("benchmark")
        benchmark_series = None
        benchmark_name = None

        if benchmark_key:
            benchmark_series = service.get_benchmark_series(benchmark_key, start, end)
            if benchmark_series:
                benchmark_name = BENCHMARK_MAP[benchmark_key]["name"]

        # When a benchmark is selected, normalize portfolio series to base-100 too
        if benchmark_series and series:
            base_value = Decimal(series[0]["value"])
            if base_value > 0:
                series = [
                    {
                        "date": point["date"],
                        "value": f"{(Decimal(point['value']) / base_value * 100):.2f}",
                    }
                    for point in series
                ]

        return Response(
            {
                "series": series,
                "benchmark_series": benchmark_series,
                "benchmark_name": benchmark_name,
            }
        )


ALLOWED_GROUP_BY = {"sector", "country", "asset_type", "currency"}


class PortfolioAllocationView(APIView):
    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        group_by = request.query_params.get("group_by", "sector")
        if group_by not in ALLOWED_GROUP_BY:
            return Response(
                {"error": "Invalid group_by parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        holdings = portfolio.holdings.select_related("instrument").all()

        groups = {}
        for h in holdings:
            key = getattr(h.instrument, group_by, "Unknown") or "Unknown"
            groups.setdefault(key, Decimal("0"))
            groups[key] += h.quantity * h.avg_buy_price

        total = sum(groups.values())
        result = [
            {
                "group": k,
                "value": f"{v:.2f}",
                "percentage": f"{(v / total * 100):.1f}" if total else "0",
            }
            for k, v in sorted(groups.items(), key=lambda x: -x[1])
        ]

        return Response(result)


class PortfolioDividendView(APIView):
    """Dividend income analytics: summary, monthly history, by instrument, recent payments."""

    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)

        today = date.today()
        twelve_months_ago = today - timedelta(days=365)

        # All dividend transactions for this portfolio
        all_dividends = (
            portfolio.transactions.filter(type=TransactionType.DIVIDEND).select_related("instrument").order_by("-date")
        )

        # Compute totals
        total_all_time = sum((tx.quantity * tx.price for tx in all_dividends), Decimal("0"))
        dividends_12m = [tx for tx in all_dividends if tx.date >= twelve_months_ago]
        total_12m = sum((tx.quantity * tx.price for tx in dividends_12m), Decimal("0"))
        monthly_avg = total_12m / 12 if total_12m else Decimal("0")

        # Trailing yield: total_12m / portfolio_value * 100
        holdings = portfolio.holdings.select_related("instrument").all()
        service = MarketDataService()
        portfolio_value = Decimal("0")
        for h in holdings:
            try:
                price_result = service.get_current_price(h.instrument)
                portfolio_value += h.quantity * price_result.price
            except Exception:
                portfolio_value += h.quantity * h.avg_buy_price

        trailing_yield = (total_12m / portfolio_value * 100) if portfolio_value else Decimal("0")

        # Dividend-paying holding count (instruments that paid dividends in 12m)
        dividend_instruments_12m = {tx.instrument_id for tx in dividends_12m}

        # --- Monthly history (last 24 months, newest first) ---
        monthly_totals = defaultdict(Decimal)
        for tx in all_dividends:
            month_key = tx.date.strftime("%Y-%m")
            monthly_totals[month_key] += tx.quantity * tx.price

        monthly_history = []
        cursor = today.replace(day=1)
        for _ in range(24):
            month_key = cursor.strftime("%Y-%m")
            monthly_history.append(
                {
                    "month": month_key,
                    "amount": f"{monthly_totals.get(month_key, Decimal('0')):.2f}",
                }
            )
            # Move to previous month
            cursor = (cursor - timedelta(days=1)).replace(day=1)

        # --- By instrument (12m, sorted by total desc) ---
        inst_totals = defaultdict(lambda: {"total": Decimal("0"), "count": 0, "instrument": None})
        for tx in dividends_12m:
            entry = inst_totals[tx.instrument_id]
            entry["total"] += tx.quantity * tx.price
            entry["count"] += 1
            entry["instrument"] = tx.instrument

        by_instrument = []
        for entry in sorted(inst_totals.values(), key=lambda e: -e["total"]):
            inst = entry["instrument"]
            pct = (entry["total"] / total_12m * 100) if total_12m else Decimal("0")
            by_instrument.append(
                {
                    "instrument_name": inst.name,
                    "ticker": inst.ticker or "",
                    "total_12m": f"{entry['total']:.2f}",
                    "pct_of_total": f"{pct:.1f}",
                    "payment_count_12m": entry["count"],
                }
            )

        # --- Recent payments (last 10) ---
        recent_payments = []
        for tx in all_dividends[:10]:
            recent_payments.append(
                {
                    "date": str(tx.date),
                    "instrument_name": tx.instrument.name,
                    "ticker": tx.instrument.ticker or "",
                    "amount": f"{tx.quantity * tx.price:.2f}",
                }
            )

        return Response(
            {
                "summary": {
                    "total_dividends_12m": f"{total_12m:.2f}",
                    "total_dividends_all_time": f"{total_all_time:.2f}",
                    "trailing_yield_pct": f"{trailing_yield:.2f}",
                    "monthly_average_12m": f"{monthly_avg:.2f}",
                    "dividend_holding_count": len(dividend_instruments_12m),
                    "total_holding_count": holdings.count(),
                },
                "monthly_history": monthly_history,
                "by_instrument": by_instrument,
                "recent_payments": recent_payments,
            }
        )


class PortfolioAdviceView(APIView):
    """Structured portfolio advice powered by the rule-based advice engine."""

    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)

        if not portfolio.holdings.exists():
            return Response(
                {
                    "items": [],
                    "has_pending_analysis": False,
                    "disclaimer": DISCLAIMER,
                }
            )

        engine = AdviceEngine(portfolio)
        response = engine.evaluate()

        return Response(AdviceResponseSerializer(response).data)


class PortfolioFullAdviceView(APIView):
    """Full AI Advice page: health score, top actions, recommendations, scenarios."""

    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)

        if not portfolio.holdings.exists():
            return Response(
                {
                    "health_score": {
                        "overall_score": 0,
                        "summary": "Add holdings to get portfolio advice.",
                        "sub_scores": {},
                    },
                    "top_actions": [],
                    "recommendations": [],
                    "scenarios": [],
                    "advice_items": [],
                    "has_pending_analysis": False,
                    "disclaimer": FULL_ADVICE_DISCLAIMER,
                }
            )

        engine = AdviceEngine(portfolio)
        response = engine.evaluate_full()

        return Response(FullAdviceResponseSerializer(response).data)


class ChatRateThrottle(UserRateThrottle):
    rate = "30/hour"


class PortfolioAdviceChatView(APIView):
    """Portfolio-aware chat endpoint for Q&A about holdings."""

    throttle_classes = [ChatRateThrottle]

    def post(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)

        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data["message"]

        # Use cached engine results instead of recomputing
        engine = AdviceEngine(portfolio)
        advice_response = engine.evaluate()  # This already uses 15-min cache internally
        items = advice_response.items

        # Build context only if not cached
        ctx_cache_key = f"advice:ctx:{portfolio_id}"
        ctx = cache.get(ctx_cache_key)
        if ctx is None:
            service = MarketDataService()
            ctx = build_advice_context(portfolio, service)
            cache.set(ctx_cache_key, ctx, 15 * 60)

        # Recommendations are cached by the engine too
        rec_cache_key = f"advice:recs:{portfolio_id}"
        recs = cache.get(rec_cache_key)
        if recs is None:
            recs = RecommendationEngine(ctx, items).evaluate()
            cache.set(rec_cache_key, recs, 15 * 60)

        chat_response = handle_chat_message(message, ctx, items, recs)
        return Response(ChatResponseSerializer(chat_response).data)


class PortfolioCorrelationView(APIView):
    """Pairwise correlation heatmap data for portfolio holdings."""

    MAX_HOLDINGS = 15

    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)

        # Check cache first (24 hours)
        cache_key = f"correlation:{portfolio_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        holdings = list(
            portfolio.holdings.select_related("instrument")
            .exclude(instrument__ticker__isnull=True)
            .exclude(instrument__ticker="")
            .all()
        )

        if len(holdings) < 2:
            empty = {"tickers": [], "matrix": [], "names": []}
            return Response(empty)

        # If more than MAX_HOLDINGS, keep the largest by value (qty * avg_buy_price)
        if len(holdings) > self.MAX_HOLDINGS:
            holdings.sort(key=lambda h: h.quantity * h.avg_buy_price, reverse=True)
            holdings = holdings[: self.MAX_HOLDINGS]

        service = MarketDataService()

        # Fetch OHLCV and compute daily returns for each holding
        returns_map: dict[int, pd.Series] = {}
        holding_info: dict[int, dict] = {}  # instrument_id -> {ticker, name}

        for h in holdings:
            try:
                df = service.get_ohlcv(h.instrument, "3mo", "1d")
                if df is None or df.empty:
                    continue
                returns = df["Close"].pct_change().dropna()
                if len(returns) >= 20:
                    returns_map[h.instrument_id] = returns
                    holding_info[h.instrument_id] = {
                        "ticker": h.instrument.ticker,
                        "name": h.instrument.name,
                    }
            except Exception:
                logger.debug("Failed to fetch OHLCV for %s", h.instrument.ticker)

        if len(returns_map) < 2:
            empty = {"tickers": [], "matrix": [], "names": []}
            return Response(empty)

        # Build ordered list of instrument IDs
        ids = list(returns_map.keys())
        n = len(ids)
        id_to_idx = {inst_id: i for i, inst_id in enumerate(ids)}

        # Initialize matrix with 1.0 on diagonal
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            matrix[i][i] = 1.0

        # Compute pairwise correlations
        for id_a, id_b in itertools.combinations(ids, 2):
            try:
                ret_a = returns_map[id_a]
                ret_b = returns_map[id_b]
                aligned = pd.concat([ret_a, ret_b], axis=1, join="inner")
                if len(aligned) < 20:
                    continue
                corr = float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))
                if pd.isna(corr):
                    corr = 0.0
                i, j = id_to_idx[id_a], id_to_idx[id_b]
                matrix[i][j] = round(corr, 4)
                matrix[j][i] = round(corr, 4)
            except Exception:
                continue

        tickers = [holding_info[inst_id]["ticker"] for inst_id in ids]
        names = [holding_info[inst_id]["name"] for inst_id in ids]

        result = {"tickers": tickers, "matrix": matrix, "names": names}

        serializer = CorrelationResponseSerializer(result)
        cache.set(cache_key, serializer.data, 24 * 60 * 60)

        return Response(serializer.data)


class PortfolioRebalanceView(APIView):
    """Rebalancing tool: compute drift and suggested trades for a given strategy."""

    DRIFT_THRESHOLD = 2.0  # percentage points: within +/-2% is considered balanced

    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        strategy = request.query_params.get("strategy", "equal_weight")

        if strategy not in ("equal_weight",):
            return Response(
                {"error": "Unsupported strategy. Supported: equal_weight"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check cache
        cache_key = f"rebalance:{portfolio_id}:{strategy}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        holdings = list(portfolio.holdings.select_related("instrument").all())

        if not holdings:
            empty = {
                "strategy": strategy,
                "total_value": "0.00",
                "holdings": [],
                "max_drift": 0.0,
                "rebalance_needed": False,
            }
            return Response(empty)

        service = MarketDataService()

        # Compute market value per holding
        holding_data = []
        total_value = Decimal("0")

        for h in holdings:
            try:
                price_result = service.get_current_price(h.instrument)
                market_value = h.quantity * price_result.price
            except Exception:
                market_value = h.quantity * h.avg_buy_price

            total_value += market_value
            holding_data.append(
                {
                    "ticker": h.instrument.ticker or h.instrument.isin,
                    "name": h.instrument.name,
                    "market_value": market_value,
                }
            )

        if total_value <= 0:
            empty = {
                "strategy": strategy,
                "total_value": "0.00",
                "holdings": [],
                "max_drift": 0.0,
                "rebalance_needed": False,
            }
            return Response(empty)

        # Compute target weights
        holding_count = len(holding_data)
        target_weight = Decimal(100) / Decimal(holding_count)

        result_holdings = []
        for hd in holding_data:
            current_weight = float(hd["market_value"] / total_value * 100)
            tw = float(target_weight)
            drift = round(current_weight - tw, 2)

            if drift > self.DRIFT_THRESHOLD:
                action = "SELL"
            elif drift < -self.DRIFT_THRESHOLD:
                action = "BUY"
            else:
                action = "HOLD"

            amount_eur = abs(drift) / 100 * float(total_value)

            result_holdings.append(
                {
                    "ticker": hd["ticker"],
                    "name": hd["name"],
                    "current_weight": round(current_weight, 2),
                    "target_weight": round(tw, 2),
                    "drift": drift,
                    "action": action,
                    "amount_eur": f"{amount_eur:.2f}",
                }
            )

        # Sort by abs(drift) descending
        result_holdings.sort(key=lambda x: abs(x["drift"]), reverse=True)

        max_drift = max(abs(h["drift"]) for h in result_holdings)
        rebalance_needed = max_drift > self.DRIFT_THRESHOLD

        result = {
            "strategy": strategy,
            "total_value": f"{total_value:.2f}",
            "holdings": result_holdings,
            "max_drift": round(max_drift, 2),
            "rebalance_needed": rebalance_needed,
        }

        serializer = RebalanceResponseSerializer(result)
        cache.set(cache_key, serializer.data, 15 * 60)

        return Response(serializer.data)
