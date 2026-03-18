from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    HoldingListView,
    PortfolioAdviceView,
    PortfolioAllocationView,
    PortfolioPerformanceView,
    PortfolioSummaryView,
    PortfolioViewSet,
    TransactionViewSet,
)

router = DefaultRouter()
router.register(r"portfolios", PortfolioViewSet, basename="portfolio")

urlpatterns = [
    path("", include(router.urls)),
    path("portfolios/<int:portfolio_id>/holdings/", HoldingListView.as_view(), name="portfolio-holdings"),
    path(
        "portfolios/<int:portfolio_id>/transactions/",
        TransactionViewSet.as_view({"get": "list", "post": "create"}),
        name="portfolio-transactions",
    ),
    path(
        "transactions/<int:pk>/",
        TransactionViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="transaction-detail",
    ),
    path("portfolios/<int:portfolio_id>/summary/", PortfolioSummaryView.as_view(), name="portfolio-summary"),
    path(
        "portfolios/<int:portfolio_id>/performance/", PortfolioPerformanceView.as_view(), name="portfolio-performance"
    ),
    path("portfolios/<int:portfolio_id>/allocation/", PortfolioAllocationView.as_view(), name="portfolio-allocation"),
    path("portfolios/<int:portfolio_id>/advice/", PortfolioAdviceView.as_view(), name="portfolio-advice"),
]
