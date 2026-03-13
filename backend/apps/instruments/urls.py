from django.urls import path

from .views import InstrumentAnalysisView, InstrumentChartView, InstrumentDetailView

urlpatterns = [
    path("instruments/<int:pk>/", InstrumentDetailView.as_view(), name="instrument-detail"),
    path("instruments/<int:pk>/analysis/", InstrumentAnalysisView.as_view(), name="instrument-analysis"),
    path("instruments/<int:pk>/chart/", InstrumentChartView.as_view(), name="instrument-chart"),
]
