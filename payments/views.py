import razorpay
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Payment, Subscription
from .permissions import IsPremiumUser
from django.contrib.auth.models import User
from rest_framework.decorators import api_view
from .utils import razorpay_client
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from .models import RecurringPayment
from .serializers import RecurringPaymentSerializer
from celery import shared_task
from django.utils.timezone import now
from notifications.models import Notification
# Initialize Razorpay Client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


class VerifyPaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_id = request.data.get('razorpay_payment_id')
        order_id = request.data.get('razorpay_order_id')
        signature = request.data.get('razorpay_signature')

        # Verify Payment Signature
        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            return Response({"message": "Payment verified successfully"}, status=200)
        except razorpay.errors.SignatureVerificationError:
            return Response({"error": "Payment verification failed"}, status=400)


class CreateSubscriptionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_type = request.data.get('plan_type', 'monthly')
        amount = 10000 if plan_type == 'monthly' else 100000  # Example: ₹100/month, ₹1000/year
        interval = 'monthly' if plan_type == 'monthly' else 'yearly'

        # Create Razorpay Subscription
        razorpay_subscription = razorpay_client.subscription.create({
            "plan_id": "plan_ABC123",  # Replace with your Razorpay Plan ID
            "customer_notify": 1,
            "total_count": 12 if interval == 'monthly' else 1,
        })

        # Save Subscription in Database
        subscription = Subscription.objects.create(
            user=request.user,
            razorpay_subscription_id=razorpay_subscription['id'],
            plan_type=plan_type,
            status='active'
        )

        return Response({
            "message": "Subscription created successfully!",
            "subscription_id": razorpay_subscription['id']
        }, status=201)



# ✅ List all recurring payments for the logged-in user & create a new payment
class RecurringPaymentListCreateView(generics.ListCreateAPIView):
    serializer_class = RecurringPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RecurringPayment.objects.filter(user=self.request.user)  # Only return user's payments

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)  # Assign logged-in user to new payment


# ✅ Retrieve, Update, or Delete a payment (only for the owner)
class RecurringPaymentUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RecurringPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RecurringPayment.objects.filter(user=self.request.user)



@shared_task
def send_payment_reminders():
    today = now().date()
    upcoming_payments = RecurringPayment.objects.filter(next_payment_date=today)

    for payment in upcoming_payments:
        Notification.objects.create(
            user=payment.user,
            message=f"Reminder: {payment.name} payment of ${payment.amount} is due today!"
        )
