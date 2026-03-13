import yfinance as yf
from django.db import IntegrityError

from .models import AssetType, Instrument

QUOTE_TYPE_MAP = {
    "EQUITY": AssetType.STOCK,
    "ETF": AssetType.ETF,
    "MUTUALFUND": AssetType.FUND,
    "BOND": AssetType.BOND,
}


class InstrumentResolver:
    def get_or_create(self, isin: str, name: str, currency: str) -> Instrument:
        try:
            return Instrument.objects.get(isin=isin)
        except Instrument.DoesNotExist:
            pass

        ticker, sector, country, asset_type = self._resolve_from_yfinance(isin)

        try:
            return Instrument.objects.create(
                isin=isin,
                ticker=ticker,
                name=name,
                currency=currency,
                sector=sector,
                country=country,
                asset_type=asset_type or AssetType.OTHER,
            )
        except IntegrityError:
            return Instrument.objects.get(isin=isin)

    def _resolve_from_yfinance(self, isin: str):
        try:
            search = yf.Search(isin)
            if not search.quotes:
                return None, None, None, None

            symbol = search.quotes[0]["symbol"]
            info = yf.Ticker(symbol).info
            asset_type = QUOTE_TYPE_MAP.get(info.get("quoteType", ""), None)

            return symbol, info.get("sector"), info.get("country"), asset_type
        except Exception:
            return None, None, None, None
