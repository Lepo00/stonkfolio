from datetime import date, timedelta
from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market_data.services import MarketDataService

from .models import Holding, Portfolio, Transaction, TransactionType
from .serializers import HoldingSerializer, PortfolioSerializer, TransactionSerializer


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

        return Response(
            {
                "total_value": f"{total_value:.2f}",
                "total_cost": f"{total_cost:.2f}",
                "total_gain_loss": f"{total_value - total_cost:.2f}",
                "total_return_pct": f"{((total_value - total_cost) / total_cost * 100):.2f}" if total_cost else "0.00",
                "first_transaction_date": str(first_tx) if first_tx else None,
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

        txs = portfolio.transactions.select_related("instrument").order_by("date").all()

        instrument_changes = {}
        for tx in txs:
            if not tx.instrument.ticker:
                continue
            changes = instrument_changes.setdefault(tx.instrument_id, {"instrument": tx.instrument, "events": []})
            if tx.type == TransactionType.BUY:
                changes["events"].append((tx.date, tx.quantity))
            elif tx.type == TransactionType.SELL:
                changes["events"].append((tx.date, -tx.quantity))

        # Build per-instrument daily values
        inst_series = {}  # {instrument_id: {date: value}}
        for inst_data in instrument_changes.values():
            instrument = inst_data["instrument"]
            events = inst_data["events"]
            try:
                prices = service.get_historical_prices(instrument, start, end)
            except Exception:
                continue

            qty = Decimal("0")
            event_idx = 0
            daily = {}
            for pp in prices:
                while event_idx < len(events) and events[event_idx][0] <= pp.date:
                    qty += events[event_idx][1]
                    event_idx += 1
                if qty > 0:
                    daily[pp.date] = qty * pp.price

            if daily:
                inst_series[instrument.id] = daily

        # Build unified date range and carry forward missing values
        all_dates = sorted({d for daily in inst_series.values() for d in daily})
        series_map = {}
        for d in all_dates:
            total = Decimal("0")
            for inst_id, daily in inst_series.items():
                if d in daily:
                    total += daily[d]
                else:
                    # Carry forward: find the most recent date before d
                    prev_dates = [pd for pd in daily if pd < d]
                    if prev_dates:
                        total += daily[max(prev_dates)]
            series_map[d] = total

        series = [{"date": str(d), "value": f"{v:.2f}"} for d, v in sorted(series_map.items())]

        return Response({"series": series})


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
