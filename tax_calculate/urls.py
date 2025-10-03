from django.urls import path
from .views import tax_calculator_view,tax_history_api,process_pdf

urlpatterns = [
    path("calculate/", tax_calculator_view, name="tax_calculator"),
    path('tax-history/', tax_history_api, name='tax_history_api'),
    path('upload/', process_pdf, name='process_pdf'),
]
