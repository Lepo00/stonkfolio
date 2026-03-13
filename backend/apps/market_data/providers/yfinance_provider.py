from datetime import date
from decimal import Decimal

import yfinance as yf

from .base import PricePoint, PriceProvider, PriceResult


class YFinancePriceProvider(PriceProvider):
    def get_current_price(self, ticker: str) -> PriceResult:
        try:
            t = yf.Ticker(ticker)
            info = t.info
            price = info.get("regularMarketPrice")
            if price is None:
                raise ValueError(f"No price data for {ticker}")
            return PriceResult(
                price=Decimal(str(price)),
                currency=info.get("currency", "USD"),
            )
        except Exception as e:
            raise ValueError(f"Failed to fetch price for {ticker}: {e}")

    def get_historical_prices(self, ticker: str, start: date, end: date) -> list[PricePoint]:
        t = yf.Ticker(ticker)
        df = t.history(start=str(start), end=str(end))
        return [PricePoint(date=row.Index.date(), price=Decimal(str(row.Close))) for row in df.itertuples()]

    def get_ohlcv(self, ticker: str, period: str, interval: str):
        """Fetch OHLC+Volume data from yfinance. Returns a pandas DataFrame."""
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval, timeout=10)
        if df.empty:
            raise ValueError(f"No OHLCV data for {ticker} (period={period})")
        return df
