from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    base_currency = models.CharField(max_length=3, default="EUR")
