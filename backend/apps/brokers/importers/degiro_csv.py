import csv
import hashlib
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .base import BrokerImporter, TransactionData, TransactionType, sanitize_csv_value

# Known header names per canonical field across languages
HEADER_NAMES = {
    "date": {"Date", "Data", "Datum"},
    "time": {"Time", "Ora", "Uhrzeit", "Tijd"},
    "product": {"Product", "Prodotto", "Produkt"},
    "isin": {"ISIN"},
    "description": {"Description", "Descrizione", "Beschreibung", "Omschrijving"},
    "order_id": {"Order ID", "ID Ordine", "Order-ID"},
}

# Patterns for buy/sell descriptions across languages
BUY_PATTERNS = [
    re.compile(r"Buy (\d+(?:[.,]\d+)?) (?:.*?)@\s*([\d.,]+)"),
    re.compile(r"Acquisto (\d+(?:[.,]\d+)?) (?:.*?)@\s*([\d.,]+)"),
    re.compile(r"Kauf (\d+(?:[.,]\d+)?) (?:.*?)@\s*([\d.,]+)"),
    re.compile(r"Koop (\d+(?:[.,]\d+)?) (?:.*?)@\s*([\d.,]+)"),
]

SELL_PATTERNS = [
    re.compile(r"Sell (\d+(?:[.,]\d+)?) (?:.*?)@\s*([\d.,]+)"),
    re.compile(r"Vendita (\d+(?:[.,]\d+)?) (?:.*?)@\s*([\d.,]+)"),
    re.compile(r"Verkauf (\d+(?:[.,]\d+)?) (?:.*?)@\s*([\d.,]+)"),
    re.compile(r"Verkoop (\d+(?:[.,]\d+)?) (?:.*?)@\s*([\d.,]+)"),
]

DIVIDEND_KEYWORDS = ["Dividend", "Dividendo", "Dividende"]

FEE_KEYWORDS = [
    "costi di transazione",
    "transaction",
    "transaktionsgebühr",
    "transactiekosten",
    "imposta sulle transazioni",
    "stamp duty",
    "stempelsteuer",
]

# Known currency/amount header names (the amount is the column right after)
CHANGE_HEADERS = {"Change", "Variazioni", "Änderung", "Mutatie"}


def _parse_european_decimal(value: str) -> Decimal:
    """Parse a decimal that may use comma as decimal separator."""
    value = value.strip().strip('"')
    if not value:
        raise ValueError("empty value")
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    return Decimal(value)


class DegiroCsvImporter(BrokerImporter):
    broker_name = "degiro"

    def import_transactions(self, source) -> list[TransactionData]:
        reader = csv.reader(source)
        header = next(reader)
        col_map = self._build_column_map(header)
        amount_idx = self._find_amount_column(header)

        raw_rows = []
        for row in reader:
            parsed = self._extract_fields(row, col_map, amount_idx)
            if parsed:
                raw_rows.append(parsed)

        # Group by order_id to aggregate fees
        order_groups: dict[str, list[dict]] = {}
        ungrouped = []
        for row in raw_rows:
            order_id = row.get("order_id", "").strip()
            if order_id:
                order_groups.setdefault(order_id, []).append(row)
            else:
                ungrouped.append(row)

        transactions = []
        for group in order_groups.values():
            parsed = self._parse_order_group(group)
            if parsed:
                transactions.append(parsed)

        for row in ungrouped:
            parsed = self._parse_single_row(row)
            if parsed:
                transactions.append(parsed)

        return transactions

    def _build_column_map(self, header: list[str]) -> dict[str, int]:
        """Map canonical field names to column indices."""
        col_map = {}
        for idx, name in enumerate(header):
            name = name.strip()
            for canonical, variants in HEADER_NAMES.items():
                if name in variants:
                    col_map[canonical] = idx
                    break
        return col_map

    def _find_amount_column(self, header: list[str]) -> int | None:
        """Find the amount column (the one right after Change/Variazioni)."""
        for idx, name in enumerate(header):
            if name.strip() in CHANGE_HEADERS:
                # Amount is the next column
                if idx + 1 < len(header):
                    return idx + 1
        # Fallback for English format: look for unnamed column after "Change"
        return None

    def _extract_fields(self, row: list[str], col_map: dict[str, int], amount_idx: int | None) -> dict | None:
        """Extract canonical fields from a positional row."""
        if len(row) < 5:
            return None

        def get(field: str) -> str:
            idx = col_map.get(field)
            if idx is not None and idx < len(row):
                return row[idx].strip()
            return ""

        # Scan for currency code in the row
        currency = "EUR"
        for val in row:
            if val.strip() in ("EUR", "USD", "GBP", "CHF", "SEK", "NOK", "DKK"):
                currency = val.strip()
                break

        amount = None
        if amount_idx is not None and amount_idx < len(row):
            try:
                amount = _parse_european_decimal(row[amount_idx])
            except (InvalidOperation, ValueError):
                pass

        return {
            "date": get("date"),
            "time": get("time"),
            "product": get("product"),
            "isin": get("isin"),
            "description": get("description"),
            "order_id": get("order_id"),
            "currency": currency,
            "amount": amount,
        }

    def _parse_order_group(self, group: list[dict]) -> TransactionData | None:
        tx_row = None
        total_fee = Decimal("0")

        for row in group:
            desc = row.get("description", "")
            if self._is_fee_row(desc):
                amount = row.get("amount")
                if amount is not None:
                    total_fee += abs(amount)
            else:
                tx_row = row

        if tx_row is None:
            return None

        return self._parse_single_row(tx_row, fee=total_fee)

    def _parse_single_row(self, row: dict, fee: Decimal = Decimal("0")) -> TransactionData | None:
        isin = row.get("isin", "").strip()
        description = row.get("description", "")

        if not isin:
            return None

        tx_type, quantity, price = self._parse_description(description)
        if tx_type is None:
            return None

        date_str = row.get("date", "")
        try:
            tx_date = datetime.strptime(date_str, "%d-%m-%Y").date()
        except ValueError:
            return None

        currency = row.get("currency", "EUR")

        broker_ref = self._make_reference(isin, tx_date, quantity, price, row.get("order_id", ""))

        return TransactionData(
            isin=isin,
            product_name=sanitize_csv_value(row.get("product", "")),
            type=tx_type,
            quantity=quantity,
            price=price,
            fee=fee,
            date=tx_date,
            currency=currency,
            broker_reference=broker_ref,
            broker_source="degiro",
        )

    def _parse_description(self, desc: str):
        for pattern in BUY_PATTERNS:
            match = pattern.search(desc)
            if match:
                qty = _parse_european_decimal(match.group(1))
                price = _parse_european_decimal(match.group(2))
                return TransactionType.BUY, qty, price

        for pattern in SELL_PATTERNS:
            match = pattern.search(desc)
            if match:
                qty = _parse_european_decimal(match.group(1))
                price = _parse_european_decimal(match.group(2))
                return TransactionType.SELL, qty, price

        for keyword in DIVIDEND_KEYWORDS:
            if keyword in desc:
                return TransactionType.DIVIDEND, Decimal("0"), Decimal("0")

        return None, None, None

    def _is_fee_row(self, description: str) -> bool:
        desc_lower = description.lower()
        return any(kw in desc_lower for kw in FEE_KEYWORDS)

    def _make_reference(self, isin, date, quantity, price, order_id):
        raw = f"degiro:{isin}:{date}:{quantity}:{price}:{order_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
