from django.urls import path

from .views import PriceView

urlpatterns = [
    path("prices/<str:ticker>/", PriceView.as_view(), name="price"),
]
