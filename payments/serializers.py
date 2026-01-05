from rest_framework import serializers
from .models import RecurringPayment

class RecurringPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringPayment
        fields = '__all__'  # Returns all model fields as JSON
