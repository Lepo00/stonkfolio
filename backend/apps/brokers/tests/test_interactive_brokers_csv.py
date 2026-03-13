from decimal import Decimal
from pathlib import Path

from apps.brokers.importers.base import TransactionType
from apps.brokers.importers.interactive_brokers_csv import InteractiveBrokersCsvImporter

FIXTURES = Path(__file__).parent / "fixtures"


class TestInteractiveBrokersCsvImporter:
    def test_parse_transactions(self):
        importer = InteractiveBrokersCsvImporter()
        with open(FIXTURES / "interactive_brokers_transactions.csv") as f:
            transactions = importer.import_transactions(f)
        assert len(transactions) == 3
        assert transactions[0].isin == "IE00B4L5Y983"
        assert transactions[0].type == TransactionType.BUY
        assert transactions[0].quantity == Decimal("10")
        assert transactions[0].price == Decimal("75.50")
        assert transactions[0].fee == Decimal("1.25")

    def test_sld_is_sell(self):
        importer = InteractiveBrokersCsvImporter()
        with open(FIXTURES / "interactive_brokers_transactions.csv") as f:
            transactions = importer.import_transactions(f)
        assert transactions[2].type == TransactionType.SELL

    def test_unique_references(self):
        importer = InteractiveBrokersCsvImporter()
        with open(FIXTURES / "interactive_brokers_transactions.csv") as f:
            transactions = importer.import_transactions(f)
        refs = [t.broker_reference for t in transactions]
        assert len(set(refs)) == 3
