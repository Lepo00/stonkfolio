from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pandas as pd


@dataclass
class PriceResult:
    price: Decimal
    currency: str


@dataclass
class PricePoint:
    date: date
    price: Decimal


class PriceProvider(ABC):
    @abstractmethod
    def get_current_price(self, ticker: str) -> PriceResult: ...

    @abstractmethod
    def get_historical_prices(self, ticker: str, start: date, end: date) -> list[PricePoint]: ...

    @abstractmethod
    def get_ohlcv(self, ticker: str, period: str, interval: str) -> pd.DataFrame:
        """Return OHLC+Volume data as a pandas DataFrame."""
        ...
