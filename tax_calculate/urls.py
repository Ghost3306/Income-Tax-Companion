from django.urls import path
from .views import tax_calculator_view,tax_history_api,process_pdf,chat_api,faq_api,random_faqs,insert_faq_query,fetch_faq_by_email

urlpatterns = [
    path("calculate/", tax_calculator_view, name="tax_calculator"),
    path('tax-history/', tax_history_api, name='tax_history_api'),
    path('upload/', process_pdf, name='process_pdf'),
    path("chat/", chat_api, name="chat_api"),
    path("faq/", faq_api, name="faq_api"),
    path('random/', random_faqs, name='random_faqs'),
    path('faq/insert/', insert_faq_query, name='insert_faq_query'),
    path('faq/by-email/',fetch_faq_by_email, name='faq_by_email'),
]
