from django.urls import path

from .views import InstrumentAnalysisView, InstrumentDetailView

urlpatterns = [
    path("instruments/<int:pk>/", InstrumentDetailView.as_view(), name="instrument-detail"),
    path("instruments/<int:pk>/analysis/", InstrumentAnalysisView.as_view(), name="instrument-analysis"),
]
