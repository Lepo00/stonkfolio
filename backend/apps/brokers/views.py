import uuid
from io import TextIOWrapper

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.portfolios.models import Portfolio

from .importers.bitpanda_csv import BitpandaCsvImporter
from .importers.degiro_csv import DegiroCsvImporter
from .importers.interactive_brokers_csv import InteractiveBrokersCsvImporter
from .importers.trade_republic_csv import TradeRepublicCsvImporter
from .models import BrokerConnection
from .serializers import BrokerConnectionSerializer
from .services import ImportService

IMPORTERS = {
    "degiro": DegiroCsvImporter,
    "trade_republic": TradeRepublicCsvImporter,
    "interactive_brokers": InteractiveBrokersCsvImporter,
    "bitpanda": BitpandaCsvImporter,
}


class BrokerConnectionViewSet(viewsets.ModelViewSet):
    serializer_class = BrokerConnectionSerializer
    http_method_names = ["get", "post", "delete"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return BrokerConnection.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CsvPreviewView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, portfolio_id):
        get_object_or_404(Portfolio, id=portfolio_id, user=request.user)  # authz check
        broker = request.data.get("broker", "degiro")
        file = request.FILES.get("file")

        if not file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        if file.size > 5 * 1024 * 1024:
            return Response(
                {"error": "File too large (max 5MB)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not file.name.endswith(".csv"):
            return Response(
                {"error": "Only CSV files accepted"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        importer_cls = IMPORTERS.get(broker)
        if not importer_cls:
            return Response({"error": f"Unknown broker: {broker}"}, status=status.HTTP_400_BAD_REQUEST)

        importer = importer_cls()
        text_file = TextIOWrapper(file, encoding="utf-8")
        transactions = importer.import_transactions(text_file)

        preview_id = f"{request.user.id}_{uuid.uuid4().hex[:8]}"
        cache.set(f"import_preview_{preview_id}", transactions, timeout=600)

        return Response(
            {
                "preview_id": preview_id,
                "transactions": [
                    {
                        "isin": t.isin,
                        "product_name": t.product_name,
                        "type": t.type.value,
                        "quantity": str(t.quantity),
                        "price": str(t.price),
                        "date": str(t.date),
                        "currency": t.currency,
                    }
                    for t in transactions
                ],
            }
        )


class CsvConfirmView(APIView):
    def post(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        preview_id = request.data.get("preview_id")

        if not preview_id or not preview_id.startswith(f"{request.user.id}_"):
            return Response(
                {"error": "Invalid or expired preview"},
                status=status.HTTP_403_FORBIDDEN,
            )

        transactions = cache.get(f"import_preview_{preview_id}")
        if transactions is None:
            return Response({"error": "Preview expired"}, status=status.HTTP_400_BAD_REQUEST)

        service = ImportService()
        result = service.import_transactions(portfolio, transactions)
        cache.delete(f"import_preview_{preview_id}")

        return Response(
            {
                "imported": result.imported,
                "skipped": result.skipped,
                "warnings": result.warnings,
            }
        )


class ImportSyncView(APIView):
    def post(self, request, portfolio_id):
        get_object_or_404(Portfolio, id=portfolio_id, user=request.user)  # authz check
        return Response(
            {"error": "API sync not yet implemented"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
