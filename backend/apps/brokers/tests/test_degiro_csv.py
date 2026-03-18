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


class TestDegiroCsvImporterItalian:
    def test_parse_italian_transactions(self):
        importer = DegiroCsvImporter()
        with open(FIXTURES / "degiro_transactions_it.csv") as f:
            transactions = importer.import_transactions(f)

        # 2 buy transactions (deposit row is skipped)
        assert len(transactions) == 2

    def test_italian_buy_quantity_and_price(self):
        importer = DegiroCsvImporter()
        with open(FIXTURES / "degiro_transactions_it.csv") as f:
            transactions = importer.import_transactions(f)

        # First transaction: Acquisto 26 @43,55
        em_tx = next(t for t in transactions if t.isin == "IE00BKM4GZ66")
        assert em_tx.type == TransactionType.BUY
        assert em_tx.quantity == Decimal("26")
        assert em_tx.price == Decimal("43.55")
        assert em_tx.product_name == "ISHARES CORE MSCI EM IMI UCITS ETF USD"

    def test_italian_fee_aggregation(self):
        importer = DegiroCsvImporter()
        with open(FIXTURES / "degiro_transactions_it.csv") as f:
            transactions = importer.import_transactions(f)

        # IE00BKM4GZ66: tax 1.36 + degiro fee 1.00 = 2.36
        em_tx = next(t for t in transactions if t.isin == "IE00BKM4GZ66")
        assert em_tx.fee == Decimal("2.36")

        # IE000M7V94E1: tax 0.53 + degiro fee 1.00 = 1.53
        uranium_tx = next(t for t in transactions if t.isin == "IE000M7V94E1")
        assert uranium_tx.fee == Decimal("1.53")

    def test_italian_deposits_skipped(self):
        importer = DegiroCsvImporter()
        with open(FIXTURES / "degiro_transactions_it.csv") as f:
            transactions = importer.import_transactions(f)

        # No transaction should have empty ISIN (deposit rows)
        for tx in transactions:
            assert tx.isin != ""

    def test_italian_unique_references(self):
        importer = DegiroCsvImporter()
        with open(FIXTURES / "degiro_transactions_it.csv") as f:
            transactions = importer.import_transactions(f)

        refs = [t.broker_reference for t in transactions]
        assert len(set(refs)) == len(refs)
