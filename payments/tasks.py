from celery import shared_task
from django.core.mail import send_mail
from .models import Subscription
from datetime import datetime, timedelta

@shared_task
def send_payment_reminders():
    upcoming_subscriptions = Subscription.objects.filter(
        end_date__lte=datetime.now() + timedelta(days=3),
        status='active'
    )
    for sub in upcoming_subscriptions:
        send_mail(
            'Payment Reminder',
            'Your subscription is about to expire. Please renew to continue premium services.',
            'admin@finance-tracker.com',
            [sub.user.email]
        )
    return 'Reminders Sent'
