from django.urls import path
from .views import CreateSubscriptionAPIView, VerifyPaymentAPIView
from .views import RecurringPaymentListCreateView, RecurringPaymentUpdateDeleteView

urlpatterns = [
    path('subscription/create/', CreateSubscriptionAPIView.as_view(), name='create_subscription'),
    path('subscription/verify/', VerifyPaymentAPIView.as_view(), name='verify_payment'),
    path('recurring-payments/', RecurringPaymentListCreateView.as_view(), name='recurring_payments'),
    path('recurring-payments/<int:pk>/', RecurringPaymentUpdateDeleteView.as_view(), name='recurring_payment_detail'),
]
