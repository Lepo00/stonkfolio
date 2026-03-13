from io import StringIO

from apps.brokers.importers.degiro_csv import DegiroCsvImporter


class TestCsvEdgeCases:
    def test_empty_csv(self):
        """Header-only CSV should return an empty list."""
        csv = StringIO("Date,Time,Product,ISIN,Description,FX,Change,,Balance,,Order ID\n")
        importer = DegiroCsvImporter()
        transactions = importer.import_transactions(csv)
        assert transactions == []

    def test_csv_with_missing_fields(self):
        """CSV missing required columns should handle gracefully (no ISIN -> skip row)."""
        csv = StringIO("Date,Time,Product,Description\n13-01-2025,09:15,MSCI World,Buy 10 @ 75.50 EUR\n")
        importer = DegiroCsvImporter()
        transactions = importer.import_transactions(csv)
        assert transactions == []

    def test_degiro_malformed_date(self):
        """Row with invalid date format should be skipped."""
        csv = StringIO(
            "Date,Time,Product,ISIN,Description,FX,Change,,Balance,,Order ID\n"
            "2025/01/13,09:15,MSCI World,IE00B4L5Y983,Buy 10 @ 75.50 EUR,,EUR,-755.00,EUR,1245.00,12345678\n"
        )
        importer = DegiroCsvImporter()
        transactions = importer.import_transactions(csv)
        assert transactions == []
