import csv
import hashlib
import re
from datetime import datetime
from decimal import Decimal

from .base import BrokerImporter, TransactionData, TransactionType, sanitize_csv_value


class DegiroCsvImporter(BrokerImporter):
    broker_name = "degiro"

    def import_transactions(self, source) -> list[TransactionData]:
        reader = csv.DictReader(source)
        transactions = []

        for row in reader:
            parsed = self._parse_row(row)
            if parsed:
                transactions.append(parsed)

        return transactions

    def _parse_row(self, row: dict) -> TransactionData | None:
        description = row.get("Description", "")
        isin = row.get("ISIN", "").strip()

        if not isin:
            return None

        tx_type, quantity, price = self._parse_description(description)
        if tx_type is None:
            return None

        date_str = row.get("Date", "")
        try:
            tx_date = datetime.strptime(date_str, "%d-%m-%Y").date()
        except ValueError:
            return None

        currency = row.get("Change", "").strip() or "EUR"
        for key, val in row.items():
            if key and key.startswith("Change"):
                currency = val.strip() if val.strip() else currency
                break

        broker_ref = self._make_reference(isin, tx_date, quantity, price, row.get("Order ID", ""))

        return TransactionData(
            isin=isin,
            product_name=sanitize_csv_value(row.get("Product", "")),
            type=tx_type,
            quantity=quantity,
            price=price,
            fee=Decimal("0"),
            date=tx_date,
            currency=currency,
            broker_reference=broker_ref,
            broker_source="degiro",
        )

    def _parse_description(self, desc: str):
        buy_match = re.match(r"Buy (\d+(?:\.\d+)?) @ ([\d.]+)", desc)
        if buy_match:
            return TransactionType.BUY, Decimal(buy_match.group(1)), Decimal(buy_match.group(2))

        sell_match = re.match(r"Sell (\d+(?:\.\d+)?) @ ([\d.]+)", desc)
        if sell_match:
            return TransactionType.SELL, Decimal(sell_match.group(1)), Decimal(sell_match.group(2))

        if "Dividend" in desc:
            return TransactionType.DIVIDEND, Decimal("0"), Decimal("0")

        return None, None, None

    def _make_reference(self, isin, date, quantity, price, order_id):
        raw = f"degiro:{isin}:{date}:{quantity}:{price}:{order_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
