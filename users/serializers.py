from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Profile, FinancialData, UserPreference

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields =  '__all__'

class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = [
            'currency', 'theme',
            'notifications_enabled', 'email_alerts', 'push_alerts',
            'auto_backup', 'budget_notification', 'weekly_reports', 'monthly_analysis'
        ]

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    username = serializers.CharField(required=False, allow_blank=True)
    phone_no = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'phone_no']

    def create(self, validated_data):
        username = validated_data.get('username') or (validated_data.get('email') or '').split('@')[0]
        email = validated_data.get('email')
        password = validated_data.pop('password')
        phone_no = validated_data.get('phone_no')

        user = User(
            username=username,
            email=email,
            phone_no=phone_no
        )
        user.set_password(password)
        user.save()
        return user





class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'

class FinancialDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialData
        fields = '__all__'
