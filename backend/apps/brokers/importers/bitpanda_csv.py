import csv
import hashlib
from datetime import datetime
from decimal import Decimal

from .base import BrokerImporter, TransactionData, TransactionType, sanitize_csv_value


class BitpandaCsvImporter(BrokerImporter):
    """
    Importer for Bitpanda CSV exports.

    Bitpanda exports transactions with columns like:
    Transaction ID, Timestamp, Transaction Type, Asset, ISIN, Amount, Price, Fee, Currency

    This implementation parses the Bitpanda transaction export format.
    Bitpanda supports stocks, ETFs, and crypto — this importer handles
    stocks and ETFs (rows with ISIN). Crypto rows without ISIN are skipped.
    """

    broker_name = "bitpanda"

    def import_transactions(self, source) -> list[TransactionData]:
        reader = csv.DictReader(source)
        transactions = []

        for row in reader:
            parsed = self._parse_row(row)
            if parsed:
                transactions.append(parsed)

        return transactions

    def _parse_row(self, row: dict) -> TransactionData | None:
        isin = row.get("ISIN", "").strip()
        if not isin:
            return None

        tx_type_str = row.get("Transaction Type", row.get("Type", "")).strip().lower()
        tx_type = self._map_type(tx_type_str)
        if tx_type is None:
            return None

        amount = self._parse_decimal(row.get("Amount", row.get("Shares", "0")))
        price = self._parse_decimal(row.get("Price", row.get("Asset price", "0")))
        fee = self._parse_decimal(row.get("Fee", "0"))

        timestamp = row.get("Timestamp", row.get("Date", ""))
        tx_date = self._parse_date(timestamp)
        if tx_date is None:
            return None

        currency = row.get("Currency", "EUR").strip()
        product_name = row.get("Asset", row.get("Asset Name", "")).strip()

        tx_id = row.get("Transaction ID", row.get("ID", ""))
        broker_ref = self._make_reference(isin, tx_date, amount, price, tx_id)

        return TransactionData(
            isin=isin,
            product_name=sanitize_csv_value(product_name),
            type=tx_type,
            quantity=abs(amount),
            price=abs(price),
            fee=abs(fee),
            date=tx_date,
            currency=currency,
            broker_reference=broker_ref,
            broker_source="bitpanda",
        )

    def _map_type(self, type_str: str) -> TransactionType | None:
        mapping = {
            "buy": TransactionType.BUY,
            "purchase": TransactionType.BUY,
            "sell": TransactionType.SELL,
            "sale": TransactionType.SELL,
            "dividend": TransactionType.DIVIDEND,
        }
        return mapping.get(type_str)

    def _parse_decimal(self, value: str) -> Decimal:
        if not value:
            return Decimal("0")
        cleaned = value.strip().replace(",", ".")
        try:
            return Decimal(cleaned)
        except Exception:
            return Decimal("0")

    def _parse_date(self, date_str: str):
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(date_str.strip()[:19], fmt).date()
            except ValueError:
                continue
        return None

    def _make_reference(self, isin, date, amount, price, tx_id):
        raw = f"bitpanda:{isin}:{date}:{amount}:{price}:{tx_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
