from django.db import models


class AssetType(models.TextChoices):
    STOCK = "STOCK"
    ETF = "ETF"
    BOND = "BOND"
    FUND = "FUND"
    OTHER = "OTHER"


class Instrument(models.Model):
    isin = models.CharField(max_length=12, unique=True)
    ticker = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=255)
    currency = models.CharField(max_length=3)
    sector = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    asset_type = models.CharField(max_length=10, choices=AssetType.choices, default=AssetType.STOCK)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ticker or self.isin} - {self.name}"
