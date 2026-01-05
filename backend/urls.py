"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

from django.shortcuts import render



urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT Authentication Routes
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Login
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Refresh token

    # API Routes
    path('api/users/', include('users.urls')),
    path('api/', include('transactions.urls')),
    # path('api/', include('payments.urls')),  # Payments module removed
    path('api/', include('group_expenses.urls')),
    path('api/analytics/', include('analytics.urls')),
    
    #path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Login
    #path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Refresh token
    #path('api/transactions/', include('transactions.urls')),  # Ensure this is correctly included
    #path('api/payments/', include('payments.urls')),
    
    #path('api/notifications/', include('notifications.urls')),
    #path('transactions/', include('transactions.urls')),  
    #path('insights/', include('insights.urls')),
    #path('admin_dashboard/', include('admin_dashboard.urls')),
  
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

