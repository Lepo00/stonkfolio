import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestAuth:
    def setup_method(self):
        self.client = APIClient()

    def test_register_creates_user(self):
        resp = self.client.post(
            reverse("register"),
            {
                "username": "testuser",
                "password": "securepass123",
                "email": "test@example.com",
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert "id" in resp.data

    def test_login_returns_tokens(self):
        from apps.users.models import User

        User.objects.create_user(username="testuser", password="securepass123")
        resp = self.client.post(
            reverse("token_obtain_pair"),
            {
                "username": "testuser",
                "password": "securepass123",
            },
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "access" in resp.data
        assert "refresh" in resp.data

    def test_me_returns_profile(self):
        from apps.users.models import User

        user = User.objects.create_user(username="testuser", password="securepass123")
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse("user_me"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["base_currency"] == "EUR"

    def test_me_update_currency(self):
        from apps.users.models import User

        user = User.objects.create_user(username="testuser", password="securepass123")
        self.client.force_authenticate(user=user)
        resp = self.client.patch(reverse("user_me"), {"base_currency": "USD"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["base_currency"] == "USD"

    def test_register_duplicate_username(self):
        from apps.users.models import User

        User.objects.create_user(username="testuser", password="securepass123")
        resp = self.client.post(
            reverse("register"),
            {
                "username": "testuser",
                "password": "securepass123",
                "email": "test2@example.com",
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_short_password(self):
        resp = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "password": "short",
                "email": "new@example.com",
            },
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_wrong_password(self):
        from apps.users.models import User

        User.objects.create_user(username="testuser", password="securepass123")
        resp = self.client.post(
            reverse("token_obtain_pair"),
            {
                "username": "testuser",
                "password": "wrongpassword",
            },
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self):
        resp = self.client.post(
            reverse("token_obtain_pair"),
            {
                "username": "nonexistent",
                "password": "somepassword",
            },
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_unauthenticated(self):
        resp = self.client.get(reverse("user_me"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
