import csv
import hashlib
from datetime import datetime
from decimal import Decimal

from .base import BrokerImporter, TransactionData, TransactionType, sanitize_csv_value


class InteractiveBrokersCsvImporter(BrokerImporter):
    """
    Importer for Interactive Brokers (IBKR) Flex Query CSV exports.

    IBKR Flex Queries export trades with columns like:
    TradeDate, Symbol, ISIN, Description, Buy/Sell, Quantity, TradePrice, IBCommission, CurrencyPrimary, TradeID

    This implementation parses the standard IBKR Flex Query trade report format.
    Users should generate a Flex Query with at minimum: Trades report including the fields above.
    """

    broker_name = "interactive_brokers"

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

        buy_sell = row.get("Buy/Sell", row.get("Code", "")).strip().upper()
        tx_type = self._map_type(buy_sell)
        if tx_type is None:
            return None

        quantity = self._parse_decimal(row.get("Quantity", "0"))
        price = self._parse_decimal(row.get("TradePrice", row.get("Price", "0")))
        fee = abs(self._parse_decimal(row.get("IBCommission", row.get("Commission", "0"))))

        date_str = row.get("TradeDate", row.get("Date", ""))
        tx_date = self._parse_date(date_str)
        if tx_date is None:
            return None

        currency = row.get("CurrencyPrimary", row.get("Currency", "USD")).strip()
        product_name = row.get("Description", row.get("Symbol", "")).strip()

        trade_id = row.get("TradeID", row.get("TransactionID", ""))
        broker_ref = self._make_reference(isin, tx_date, quantity, price, trade_id)

        return TransactionData(
            isin=isin,
            product_name=sanitize_csv_value(product_name),
            type=tx_type,
            quantity=abs(quantity),
            price=abs(price),
            fee=fee,
            date=tx_date,
            currency=currency,
            broker_reference=broker_ref,
            broker_source="interactive_brokers",
        )

    def _map_type(self, buy_sell: str) -> TransactionType | None:
        if buy_sell in ("BUY", "BOT"):
            return TransactionType.BUY
        if buy_sell in ("SELL", "SLD"):
            return TransactionType.SELL
        return None

    def _parse_decimal(self, value: str) -> Decimal:
        if not value:
            return Decimal("0")
        cleaned = value.strip().replace(",", "")
        try:
            return Decimal(cleaned)
        except Exception:
            return Decimal("0")

    def _parse_date(self, date_str: str):
        for fmt in ("%Y%m%d", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _make_reference(self, isin, date, quantity, price, trade_id):
        raw = f"ibkr:{isin}:{date}:{quantity}:{price}:{trade_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
