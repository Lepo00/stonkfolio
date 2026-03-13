from decimal import Decimal
from pathlib import Path

from apps.brokers.importers.base import TransactionType
from apps.brokers.importers.degiro_csv import DegiroCsvImporter

FIXTURES = Path(__file__).parent / "fixtures"


class TestDegiroCsvImporter:
    def test_parse_transactions(self):
        importer = DegiroCsvImporter()
        with open(FIXTURES / "degiro_transactions.csv") as f:
            transactions = importer.import_transactions(f)

        assert len(transactions) == 3
        assert transactions[0].isin == "IE00B4L5Y983"
        assert transactions[0].type == TransactionType.BUY
        assert transactions[0].quantity == Decimal("10")
        assert transactions[0].price == Decimal("75.50")

    def test_generates_broker_reference(self):
        importer = DegiroCsvImporter()
        with open(FIXTURES / "degiro_transactions.csv") as f:
            transactions = importer.import_transactions(f)

        refs = [t.broker_reference for t in transactions]
        assert len(set(refs)) == 3  # all unique
