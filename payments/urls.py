from django.urls import path
from .views import RecurringPaymentListCreateView, RecurringPaymentUpdateDeleteView

urlpatterns = [
    # Payment gateway endpoints removed - add custom payment URLs here if needed
    path('recurring-payments/', RecurringPaymentListCreateView.as_view(), name='recurring_payments'),
    path('recurring-payments/<int:pk>/', RecurringPaymentUpdateDeleteView.as_view(), name='recurring_payment_detail'),
]
