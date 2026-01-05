# transactions/utils.py
"""
Backend utilities for transaction management.

NOTE: This file no longer contains ML model loading code.
All ML functionality has been moved to the independent ML inference service.
Use ml_client.py to call the ML service for predictions.
"""

from .models import alerts, Budget, Transaction
from django.db.models import Sum


def check_budget_alert(user):
    """
    Check if user has exceeded 80% of any budget and create alerts.
    
    This is pure business logic with no ML dependencies.
    """
    budgets = Budget.objects.filter(user=user)
    for budget in budgets:
        spent = Transaction.objects.filter(
            user=user, category=budget.category, category_type='expense'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        usage_percentage = (spent / budget.monthly_limit) * 100 if budget.monthly_limit > 0 else 0
        
        if usage_percentage >= 80:
            alerts.objects.create(
                user=user,
                message=f"You have used {usage_percentage:.2f}% of your budget for {budget.category.name}. Consider reviewing your spending."
            )


def categorize_transaction(description):
    """
    Predict category for a transaction description.
    
    This function now delegates to the ML service via HTTP.
    Use ml_client.get_ml_client().predict_category() instead.
    
    DEPRECATED: Use ml_client directly for new code.
    Kept for backward compatibility but returns None.
    """
    # Legacy function - ML moved to separate service
    # For new code, use: from .ml_client import get_ml_client
    return None
