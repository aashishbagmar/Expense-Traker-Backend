from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model, authenticate
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, SignupSerializer, ProfileSerializer, FinancialDataSerializer, UserPreferenceSerializer
from .models import Profile, FinancialData, UserPreference
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.timezone import now
from notifications.models import Notification
from django.db.models import Sum, Count, Q
from transactions.models import Transaction

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_data(request):
    user = request.user  # Get the logged-in user
    serializer = UserSerializer(user)  # Convert user object to JSON
    return Response(serializer.data)  # Return JSON response

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_avatar(request):
    user = request.user
    if 'avatar' in request.FILES:
        user.avatar = request.FILES['avatar']
        user.save()
        return Response({"message": "Avatar updated successfully!", "avatar": user.avatar.url})
    return Response({"error": "No file uploaded"}, status=400)



class SignupView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class LoginView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "message": "Login successful"
            }, status=status.HTTP_200_OK)
        
        return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)




class ProfileSetupView(generics.RetrieveUpdateAPIView):
    """Handles Profile Setup"""
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return Profile.objects.get_or_create(user=self.request.user)[0]

class FinancialInputView(generics.RetrieveUpdateAPIView):
    """Handles Financial Inputs"""
    queryset = FinancialData.objects.all()
    serializer_class = FinancialDataSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return FinancialData.objects.get_or_create(user=self.request.user)[0]

class FinancialDataView(generics.RetrieveAPIView):
    serializer_class = FinancialDataSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        data = get_object_or_404(UsersFinancialData, user_id=user_id)
        return Response(self.get_serializer(data).data)



### 🚀 User Profile API ###
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Fetch user profile details including avatar and username.
    """
    user = request.user  # Get logged-in user
    profile_data = {
        "id": user.id,
        "username": user.username,
        "avatar": user.avatar if user.avatar else "https://via.placeholder.com/100"  # Default avatar if none
    }
    return JsonResponse(profile_data)

### 🚀 User Notifications API ###
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_notifications(request):
    """
    Fetch notifications for the authenticated user.
    - If recipient is 'all', fetch for all users.
    - If recipient is 'premium' or 'free', fetch based on user's subscription.
    - If recipient is a specific user, fetch only for that user.
    """
    user = request.user
    subscription_type = "premium" if user.is_premium else "free"  # Determine subscription type based on `is_premium` field

    notifications = Notification.objects.filter(
        recipient__in=["all", subscription_type, str(user.id)]
    ).order_by('-timestamp')

    notifications_list = [
        {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "status": notification.status,
            "timestamp": notification.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        } for notification in notifications
    ]

    return JsonResponse(notifications_list, safe=False)


### 🎯 Optimized Profile API ###
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile_api(request):
    """
    GET: Fetch complete user profile with calculated stats in single query
    PUT: Update profile personal information
    """
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)
    
    if request.method == 'GET':
        # Calculate stats with single optimized query
        stats = Transaction.objects.filter(user=user).aggregate(
            total_transactions=Count('id'),
            total_income=Sum('amount', filter=Q(category_type='income')),
            total_expenses=Sum('amount', filter=Q(category_type='expense')),
            savings_amount=Sum('amount', filter=Q(category__name__icontains='savings'))
        )
        
        # Build response with all data
        response_data = {
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'is_premium': user.is_premium,
            },
            'profile': {
                'full_name': profile.full_name or '',
                'phone_number': profile.phone_number or '',
                'address': profile.address or '',
                'city': profile.city or '',
                'state': profile.state or '',
                'zip_code': profile.zip_code or '',
                'country': profile.country or '',
                'bio': profile.bio or '',
                'avatar': request.build_absolute_uri(profile.avatar.url) if profile.avatar else None,
                'preferred_currency': profile.preferred_currency,
                'date_of_birth': profile.date_of_birth,
                'occupation': profile.occupation,
                'annual_income': profile.annual_income,
                'financial_goal': profile.financial_goal,
                'investment_risk': profile.investment_risk,
                'subscription_plan': profile.subscription_plan,
            },
            'stats': {
                'total_transactions': stats['total_transactions'] or 0,
                'total_income': float(stats['total_income'] or 0),
                'total_expenses': float(stats['total_expenses'] or 0),
                'savings_amount': float(stats['savings_amount'] or 0),
                'net_balance': float((stats['total_income'] or 0) - (stats['total_expenses'] or 0)),
            }
        }
        return Response(response_data, status=status.HTTP_200_OK)
    
    elif request.method == 'PUT':
        # Update profile fields
        allowed_fields = [
            'full_name', 'phone_number', 'address', 'city', 'state',
            'zip_code', 'country', 'bio', 'preferred_currency',
            'date_of_birth', 'occupation', 'annual_income',
            'financial_goal', 'investment_risk', 'subscription_plan'
        ]
        
        for field in allowed_fields:
            if field in request.data:
                setattr(profile, field, request.data[field])
        
        profile.save()
        
        return Response({
            'message': 'Profile updated successfully',
            'profile': ProfileSerializer(profile).data
        }, status=status.HTTP_200_OK)


### 🎨 User Preferences API ###
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_preferences(request):
    """
    GET: Fetch user preferences (currency, theme, language, etc)
    PUT: Update user preferences
    """
    user = request.user
    
    # Get or create preferences
    preferences, created = UserPreference.objects.get_or_create(user=user)
    
    if request.method == 'GET':
        serializer = UserPreferenceSerializer(preferences)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserPreferenceSerializer(preferences, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

