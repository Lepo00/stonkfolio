from datetime import date, timedelta

from django.utils import timezone

from apps.instruments.models import Instrument

from .models import PriceCache
from .providers.base import PricePoint, PriceResult
from .providers.yfinance_provider import YFinancePriceProvider

CACHE_TTL = timedelta(minutes=5)


class MarketDataService:
    def __init__(self, provider=None):
        self.provider = provider or YFinancePriceProvider()

    def get_current_price(self, instrument: Instrument) -> PriceResult:
        cache = PriceCache.objects.filter(instrument=instrument).first()
        if cache and (timezone.now() - cache.fetched_at) < CACHE_TTL:
            return PriceResult(price=cache.price, currency=instrument.currency)

        if not instrument.ticker:
            raise ValueError(f"No ticker for instrument {instrument.isin}")

        result = self.provider.get_current_price(instrument.ticker)
        PriceCache.objects.update_or_create(
            instrument=instrument,
            defaults={"price": result.price},
        )
        return result

    def get_historical_prices(self, instrument: Instrument, start: date, end: date) -> list[PricePoint]:
        if not instrument.ticker:
            raise ValueError(f"No ticker for instrument {instrument.isin}")
        return self.provider.get_historical_prices(instrument.ticker, start, end)

    def get_ohlcv(self, instrument, period: str, interval: str):
        """Fetch OHLCV data for an instrument. Returns a pandas DataFrame."""
        if not instrument.ticker:
            raise ValueError(f"No ticker for instrument {instrument.isin}")
        return self.provider.get_ohlcv(instrument.ticker, period, interval)
