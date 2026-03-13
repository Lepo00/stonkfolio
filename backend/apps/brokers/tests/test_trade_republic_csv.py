from decimal import Decimal
from pathlib import Path

from apps.brokers.importers.base import TransactionType
from apps.brokers.importers.trade_republic_csv import TradeRepublicCsvImporter

FIXTURES = Path(__file__).parent / "fixtures"


class TestTradeRepublicCsvImporter:
    def test_parse_transactions(self):
        importer = TradeRepublicCsvImporter()
        with open(FIXTURES / "trade_republic_transactions.csv") as f:
            transactions = importer.import_transactions(f)
        assert len(transactions) == 3
        assert transactions[0].isin == "IE00B4L5Y983"
        assert transactions[0].type == TransactionType.BUY
        assert transactions[0].quantity == Decimal("10")
        assert transactions[0].price == Decimal("75.50")
        assert transactions[0].fee == Decimal("1.00")

    def test_sell_transaction(self):
        importer = TradeRepublicCsvImporter()
        with open(FIXTURES / "trade_republic_transactions.csv") as f:
            transactions = importer.import_transactions(f)
        assert transactions[2].type == TransactionType.SELL
        assert transactions[2].quantity == Decimal("5")

    def test_unique_references(self):
        importer = TradeRepublicCsvImporter()
        with open(FIXTURES / "trade_republic_transactions.csv") as f:
            transactions = importer.import_transactions(f)
        refs = [t.broker_reference for t in transactions]
        assert len(set(refs)) == 3
