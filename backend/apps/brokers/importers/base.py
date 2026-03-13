from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    FEE = "FEE"
    FX = "FX"


@dataclass
class TransactionData:
    isin: str
    product_name: str
    type: TransactionType
    quantity: Decimal
    price: Decimal
    fee: Decimal
    date: date
    currency: str
    broker_reference: str
    broker_source: str = ""


def sanitize_csv_value(value: str) -> str:
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


class BrokerImporter(ABC):
    broker_name: str = ""

    @abstractmethod
    def import_transactions(self, source) -> list[TransactionData]: ...
