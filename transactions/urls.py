from django.urls import path
from .views import (
    predict_expense_category, process_voice_entry, confirm_voice_transaction, get_transactions, upcoming_bills,
    export_transactions_csv, TransactionListCreateView, TransactionDetailView, CategoryListView,
    get_correction_stats, get_ai_learning_progress, monthly_totals, all_time_totals
)
from .views import CurrencyConverter
from .views import BudgetView, BudgetHistoryView

urlpatterns = [
    path('all-time-totals/', all_time_totals, name='all_time_totals'),
    path('monthly-totals/', monthly_totals, name='monthly_totals'),
    path('predict-category/', predict_expense_category, name='predict_category'),
    path('process-voice-entry/', process_voice_entry, name='process_voice_entry'),
    path('confirm-voice-transaction/', confirm_voice_transaction, name='confirm_voice_transaction'),
    path('get-transactions/', get_transactions, name='get_transactions'),
    path('api/upcoming-bills/', upcoming_bills, name='upcoming-bills'),

    path('export-transactions-csv/', export_transactions_csv, name='export_transactions_csv'),
    path('transactions/', TransactionListCreateView.as_view(), name='transaction_list_create'),
    path('transactions/<int:pk>/', TransactionDetailView.as_view(), name='transaction_detail'),
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('api/currency-convert/', CurrencyConverter.as_view(), name='currency-converter'),
    path('budget/<uuid:user_id>/', BudgetView.as_view(), name='budget'),
    path('budget-history/<uuid:user_id>/', BudgetHistoryView.as_view(), name='budget-history'),
    path('correction-stats/', get_correction_stats, name='correction_stats'),
    path('ai-learning-progress/', get_ai_learning_progress, name='ai_learning_progress'),
    path('monthly-totals/', monthly_totals, name='monthly_totals'),

]
