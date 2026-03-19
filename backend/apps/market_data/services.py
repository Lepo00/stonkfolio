from datetime import date, timedelta

import pandas as pd
from django.core.cache import cache
from django.utils import timezone

from apps.instruments.models import Instrument

from .models import PriceCache
from .providers.base import PricePoint, PriceResult
from .providers.yfinance_provider import YFinancePriceProvider

CACHE_TTL = timedelta(minutes=5)

BENCHMARK_MAP = {
    "sp500": {"ticker": "^GSPC", "name": "S&P 500"},
    "msci_world": {"ticker": "IWDA.AS", "name": "MSCI World"},
}

BENCHMARK_CACHE_TTL = 60 * 60 * 24  # 24 hours in seconds


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

    def get_ohlcv(self, instrument, period: str, interval: str) -> pd.DataFrame:
        """Fetch OHLCV data for an instrument. Returns a pandas DataFrame."""
        if not instrument.ticker:
            raise ValueError(f"No ticker for instrument {instrument.isin}")
        return self.provider.get_ohlcv(instrument.ticker, period, interval)

    def get_historical_prices_by_ticker(self, ticker: str, start: date, end: date) -> list[PricePoint]:
        """Fetch historical prices by raw ticker string (no Instrument needed)."""
        return self.provider.get_historical_prices(ticker, start, end)

    def get_benchmark_series(self, benchmark: str, start: date, end: date) -> list[dict] | None:
        """Return base-100 normalized daily series for a benchmark, or None if invalid."""
        if benchmark not in BENCHMARK_MAP:
            return None

        ticker = BENCHMARK_MAP[benchmark]["ticker"]
        cache_key = f"benchmark:{benchmark}:{start}:{end}"

        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            prices = self.get_historical_prices_by_ticker(ticker, start, end)
        except Exception:
            return None

        if not prices:
            return None

        base_price = prices[0].price
        series = [
            {
                "date": str(pp.date),
                "value": f"{(pp.price / base_price * 100):.2f}",
            }
            for pp in prices
        ]

        cache.set(cache_key, series, BENCHMARK_CACHE_TTL)
        return series
