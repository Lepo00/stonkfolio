from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BrokerConnectionViewSet, CsvConfirmView, CsvPreviewView, ImportSyncView

router = DefaultRouter()
router.register(r"broker-connections", BrokerConnectionViewSet, basename="broker-connection")

urlpatterns = [
    path("", include(router.urls)),
    path("portfolios/<int:portfolio_id>/import/csv/", CsvPreviewView.as_view(), name="import-csv-preview"),
    path("portfolios/<int:portfolio_id>/import/csv/confirm/", CsvConfirmView.as_view(), name="import-csv-confirm"),
    path("portfolios/<int:portfolio_id>/import/sync/", ImportSyncView.as_view(), name="import-sync"),
]
