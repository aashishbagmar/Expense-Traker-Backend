from django.urls import path
from .views import SignupView, LoginView, get_user_data, update_avatar, ProfileSetupView, FinancialInputView
from rest_framework_simplejwt.views import TokenRefreshView
from .views import FinancialDataView
from .views import user_profile, user_notifications, user_preferences, user_profile_api

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileSetupView.as_view(), name='profile'),
    path('financial-input/', FinancialInputView.as_view(), name='financial_input'),
    path('user-data/', get_user_data, name='get_user_data'),
    path('update-avatar/', update_avatar, name='update_avatar'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('financial-data/<uuid:user_id>/', FinancialDataView.as_view(), name='financial-data'),
    path('user-profile/', user_profile, name='user-profile'),
    path('user-profile-complete/', user_profile_api, name='user-profile-complete'),
    path('user-notifications/', user_notifications, name='user-notifications'),
    path('preferences/', user_preferences, name='user_preferences'),
]

