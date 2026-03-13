import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.portfolios.models import Portfolio
from apps.users.models import User


@pytest.mark.django_db
class TestPortfolioAPI:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_portfolio(self):
        resp = self.client.post("/api/portfolios/", {"name": "Main"})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "Main"

    def test_list_portfolios(self):
        Portfolio.objects.create(user=self.user, name="Main")
        Portfolio.objects.create(user=self.user, name="Speculative")
        resp = self.client.get("/api/portfolios/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 2

    def test_list_portfolios_only_own(self):
        other = User.objects.create_user(username="other", password="pass12345")
        Portfolio.objects.create(user=self.user, name="Mine")
        Portfolio.objects.create(user=other, name="Theirs")
        resp = self.client.get("/api/portfolios/")
        assert len(resp.data["results"]) == 1

    def test_delete_portfolio(self):
        p = Portfolio.objects.create(user=self.user, name="Main")
        resp = self.client.delete(f"/api/portfolios/{p.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_update_other_users_portfolio(self):
        other = User.objects.create_user(username="other2", password="pass12345")
        p = Portfolio.objects.create(user=other, name="Their Portfolio")
        resp = self.client.put(
            f"/api/portfolios/{p.id}/",
            {"name": "Hacked"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_other_users_portfolio(self):
        other = User.objects.create_user(username="other3", password="pass12345")
        p = Portfolio.objects.create(user=other, name="Their Portfolio")
        resp = self.client.delete(f"/api/portfolios/{p.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
