from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('users/', views.user_management, name='user_management'),
    path('users/export/', views.export_users, name='export_users'),
    path('transactions/', views.transaction_management, name='transaction_management'),
    path('payments/export/', views.export_payments, name='export_payments'),

    path('payments/', views.payment_management, name='payment_management'),
    path('notifications/', views.notification_management, name='notification_management'),
    path('settings/', views.settings_view, name='settings'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('login/', views.user_login, name='user_login'),
    path('signup/', views.user_signup, name='user_signup'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
]