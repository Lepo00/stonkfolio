import csv
import hashlib
from datetime import datetime
from decimal import Decimal

from .base import BrokerImporter, TransactionData, TransactionType, sanitize_csv_value


class TradeRepublicCsvImporter(BrokerImporter):
    """
    Importer for Trade Republic CSV exports.

    Trade Republic exports transactions in a CSV with columns like:
    Date, Time, Asset Name, ISIN, Type, Shares, Price per share, Total, Fee, Tax, Currency, Note

    This implementation parses the standard Trade Republic export format.
    Adjust column names if your export uses a different language.
    """

    broker_name = "trade_republic"

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

        tx_type_str = row.get("Type", "").strip().lower()
        tx_type = self._map_type(tx_type_str)
        if tx_type is None:
            return None

        quantity = self._parse_decimal(row.get("Shares", "0"))
        price = self._parse_decimal(row.get("Price per share", "0"))
        fee = self._parse_decimal(row.get("Fee", "0"))

        date_str = row.get("Date", "")
        tx_date = self._parse_date(date_str)
        if tx_date is None:
            return None

        currency = row.get("Currency", "EUR").strip()
        product_name = row.get("Asset Name", "").strip()

        broker_ref = self._make_reference(isin, tx_date, quantity, price, row)

        return TransactionData(
            isin=isin,
            product_name=sanitize_csv_value(product_name),
            type=tx_type,
            quantity=abs(quantity),
            price=abs(price),
            fee=abs(fee),
            date=tx_date,
            currency=currency,
            broker_reference=broker_ref,
            broker_source="trade_republic",
        )

    def _map_type(self, type_str: str) -> TransactionType | None:
        mapping = {
            "buy": TransactionType.BUY,
            "purchase": TransactionType.BUY,
            "kauf": TransactionType.BUY,
            "sell": TransactionType.SELL,
            "sale": TransactionType.SELL,
            "verkauf": TransactionType.SELL,
            "dividend": TransactionType.DIVIDEND,
            "dividende": TransactionType.DIVIDEND,
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
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _make_reference(self, isin, date, quantity, price, row):
        note = row.get("Note", row.get("ID", ""))
        raw = f"trade_republic:{isin}:{date}:{quantity}:{price}:{note}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
