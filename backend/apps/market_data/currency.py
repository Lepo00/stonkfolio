from decimal import Decimal

import yfinance as yf
from django.core.cache import cache


class CurrencyConverter:
    def convert(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        if from_currency == to_currency:
            return amount
        rate = self._get_rate(from_currency, to_currency)
        return (amount * rate).quantize(Decimal("0.01"))

    def _get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        cache_key = f"fx_rate_{from_currency}_{to_currency}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        symbol = f"{from_currency}{to_currency}=X"
        try:
            ticker = yf.Ticker(symbol)
            price = ticker.info.get("regularMarketPrice", 1.0)
            rate = Decimal(str(price))
        except Exception:
            rate = Decimal("1.0")
        cache.set(cache_key, rate, timeout=300)  # 5 minutes
        return rate
