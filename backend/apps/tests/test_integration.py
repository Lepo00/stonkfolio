from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.portfolios.models import Portfolio
from apps.users.models import User


@pytest.mark.django_db
class TestImportToDashboardFlow:
    """Integration: upload CSV -> confirm import -> view holdings -> view summary"""

    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.portfolio = Portfolio.objects.create(user=self.user, name="Main")

    @patch("apps.instruments.services.yf")
    def test_full_csv_import_and_dashboard(self, mock_yf):
        mock_search = MagicMock()
        mock_search.quotes = [{"symbol": "IWDA.AS", "shortname": "iShares MSCI World"}]
        mock_yf.Search.return_value = mock_search
        mock_ticker = MagicMock()
        mock_ticker.info = {"sector": "Diversified", "country": "Ireland", "quoteType": "ETF"}
        mock_yf.Ticker.return_value = mock_ticker

        csv_content = (
            "Date,Time,Product,ISIN,Description,FX,Change,,Balance,,Order ID\n"
            "13-01-2025,09:15,MSCI World,IE00B4L5Y983,Buy 10 @ 75.50 EUR,,EUR,-755.00,EUR,1245.00,12345678\n"
        )
        f = BytesIO(csv_content.encode())
        f.name = "transactions.csv"

        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/",
            {"file": f, "broker": "degiro"},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_200_OK
        preview_id = resp.data["preview_id"]
        assert len(resp.data["transactions"]) == 1

        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/confirm/",
            {"preview_id": preview_id},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["imported"] == 1

        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/holdings/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 1
        assert resp.data["results"][0]["quantity"] == "10.000000"

    @patch("apps.instruments.services.yf")
    def test_duplicate_import_skips(self, mock_yf):
        mock_search = MagicMock()
        mock_search.quotes = [{"symbol": "IWDA.AS", "shortname": "Test"}]
        mock_yf.Search.return_value = mock_search
        mock_ticker = MagicMock()
        mock_ticker.info = {"quoteType": "ETF"}
        mock_yf.Ticker.return_value = mock_ticker

        csv_content = (
            "Date,Time,Product,ISIN,Description,FX,Change,,Balance,,Order ID\n"
            "13-01-2025,09:15,MSCI World,IE00B4L5Y983,Buy 10 @ 75.50 EUR,,EUR,-755.00,EUR,1245.00,12345678\n"
        )

        f = BytesIO(csv_content.encode())
        f.name = "transactions.csv"
        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/",
            {"file": f, "broker": "degiro"},
            format="multipart",
        )
        preview_id = resp.data["preview_id"]
        self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/confirm/",
            {"preview_id": preview_id},
        )

        f2 = BytesIO(csv_content.encode())
        f2.name = "transactions.csv"
        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/",
            {"file": f2, "broker": "degiro"},
            format="multipart",
        )
        preview_id2 = resp.data["preview_id"]
        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/confirm/",
            {"preview_id": preview_id2},
        )
        assert resp.data["imported"] == 0
        assert resp.data["skipped"] == 1


@pytest.mark.django_db
class TestAuthFlow:
    """Integration: register -> login -> access protected endpoint"""

    def test_register_login_access(self):
        client = APIClient()

        resp = client.post(
            "/api/auth/register/",
            {
                "username": "newuser",
                "password": "securepass123",
                "email": "new@example.com",
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED

        resp = client.post(
            "/api/auth/login/",
            {
                "username": "newuser",
                "password": "securepass123",
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        token = resp.data["access"]

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = client.get("/api/user/me/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["username"] == "newuser"

    def test_unauthenticated_access_denied(self):
        client = APIClient()
        resp = client.get("/api/portfolios/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPortfolioIsolation:
    """Integration: users cannot see each other's data"""

    def test_user_cannot_see_other_portfolios(self):
        user1 = User.objects.create_user(username="user1", password="pass12345")
        user2 = User.objects.create_user(username="user2", password="pass12345")
        Portfolio.objects.create(user=user1, name="User1 Portfolio")
        Portfolio.objects.create(user=user2, name="User2 Portfolio")

        client = APIClient()
        client.force_authenticate(user=user1)
        resp = client.get("/api/portfolios/")
        names = [p["name"] for p in resp.data["results"]]
        assert "User1 Portfolio" in names
        assert "User2 Portfolio" not in names
