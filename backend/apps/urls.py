from django.urls import path, include

urlpatterns = [
    path("auth/", include("apps.users.urls")),
    path("user/", include("apps.users.profile_urls")),
    path("", include("apps.portfolios.urls")),
    path("", include("apps.brokers.urls")),
    path("", include("apps.market_data.urls")),
]
