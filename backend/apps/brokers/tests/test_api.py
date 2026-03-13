from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.portfolios.models import Portfolio
from apps.users.models import User


@pytest.mark.django_db
class TestImportAPI:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.portfolio = Portfolio.objects.create(user=self.user, name="Main")

    def test_csv_preview(self):
        csv_content = b"Date,Time,Product,ISIN,Description,FX,Change,,Balance,,Order ID\n"
        csv_content += (
            b"13-01-2025,09:15,MSCI World,IE00B4L5Y983,Buy 10 @ 75.50 EUR,,EUR,-755.00,EUR,1245.00,12345678\n"
        )
        f = BytesIO(csv_content)
        f.name = "transactions.csv"

        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/",
            {"file": f, "broker": "degiro"},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "transactions" in resp.data
        assert len(resp.data["transactions"]) == 1
        assert "preview_id" in resp.data

    @patch("apps.brokers.views.ImportService")
    def test_csv_confirm(self, MockService):
        MockService.return_value.import_transactions.return_value = MagicMock(
            imported=1,
            skipped=0,
            warnings=[],
        )
        from datetime import date
        from decimal import Decimal

        from django.core.cache import cache

        from apps.brokers.importers.base import TransactionData, TransactionType

        preview_data = [
            TransactionData(
                isin="IE00B4L5Y983",
                product_name="Test",
                type=TransactionType.BUY,
                quantity=Decimal("10"),
                price=Decimal("75.50"),
                fee=Decimal("0"),
                date=date(2025, 1, 15),
                currency="EUR",
                broker_reference="ref1",
            )
        ]
        preview_id = f"{self.user.id}_abc12345"
        cache.set(f"import_preview_{preview_id}", preview_data, timeout=600)

        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/confirm/",
            {"preview_id": preview_id},
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_upload_no_file(self):
        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/",
            {"broker": "degiro"},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_invalid_broker(self):
        csv_content = b"Date,Time,Product,ISIN,Description\n"
        f = BytesIO(csv_content)
        f.name = "transactions.csv"

        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/",
            {"file": f, "broker": "unknown_broker"},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_confirm_expired_preview(self):
        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/confirm/",
            {"preview_id": f"{self.user.id}_nonexistent"},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_to_other_users_portfolio(self):
        other = User.objects.create_user(username="other", password="pass12345")
        other_portfolio = Portfolio.objects.create(user=other, name="Other")

        csv_content = b"Date,Time,Product,ISIN,Description\n"
        f = BytesIO(csv_content)
        f.name = "transactions.csv"

        resp = self.client.post(
            f"/api/portfolios/{other_portfolio.id}/import/csv/",
            {"file": f, "broker": "degiro"},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
