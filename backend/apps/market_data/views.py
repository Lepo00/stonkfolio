from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.instruments.models import Instrument

from .services import MarketDataService


class PriceView(APIView):
    def get(self, request, ticker):
        try:
            instrument = Instrument.objects.get(ticker=ticker)
        except Instrument.DoesNotExist:
            return Response({"error": "Instrument not found"}, status=status.HTTP_404_NOT_FOUND)

        service = MarketDataService()
        result = service.get_current_price(instrument)

        return Response(
            {
                "ticker": ticker,
                "price": f"{result.price:.2f}",
                "currency": result.currency,
            }
        )
