from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q
from datetime import timedelta, datetime
from decimal import Decimal, InvalidOperation
from .models import Transaction, Budget, BudgetHistory, Category
from .nlp_processing import process_voice_transaction
from rest_framework import generics, filters, serializers
from rest_framework.pagination import PageNumberPagination
import csv
from .serializers import TransactionSerializer
import requests
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import Profile
from .serializers import BudgetSerializer, BudgetHistorySerializer
from payments.models import RecurringPayment

# ML Service Client (replaces direct model loading)
from .ml_client import get_ml_client

# No longer importing ML libraries (joblib, sklearn, numpy, etc.)
# All ML functionality is now handled by the independent ML service


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_time_totals(request):
    """
    Get aggregated totals for ALL user transactions (no date filtering).
    Used by Dashboard to show cumulative all-time totals.
    OPTIMIZED: Uses database aggregation instead of Python loops.
    """
    try:
        user = request.user
        
        # Optimized: Single database query with aggregation
        result = Transaction.objects.filter(user=user).aggregate(
            income=Sum('amount', filter=Q(category_type='income')),
            expense=Sum('amount', filter=Q(category_type='expense')),
            total_count=Count('id'),
            income_count=Count('id', filter=Q(category_type='income')),
            expense_count=Count('id', filter=Q(category_type='expense'))
        )
        
        income_total = float(result['income'] or 0)
        expense_total = float(result['expense'] or 0)
        net_balance = income_total - expense_total
        
        transaction_count = result['total_count']
        income_count = result['income_count']
        expense_count = result['expense_count']
        
        print(f"\n=== ALL-TIME TOTALS (OPTIMIZED) ===")
        print(f"User: {user.username}")
        print(f"Income: {income_total}, Expense: {expense_total}")
        print(f"Net Balance: {net_balance}")
        print(f"=== END DEBUG ===\n")
        
        return Response({
            'success': True,
            'totals': {
                'income': income_total,
                'expense': expense_total,
                'net_balance': net_balance,
                'transaction_count': transaction_count,
                'income_count': income_count,
                'expense_count': expense_count
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_totals(request):
    """
    Get aggregated totals for ALL transactions in the specified month.
    This ensures summary cards show correct totals regardless of pagination.
    """
    try:
        # Get month and year from query params, default to current month
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        if month and year:
            month = int(month)
            year = int(year)
        else:
            current_date = datetime.now()
            month = current_date.month
            year = current_date.year
        
        user = request.user
        
        # Query ALL transactions for the specified month/year
        all_transactions = Transaction.objects.filter(
            user=user,
            date__month=month,
            date__year=year
        )
        
        print(f"\n=== MONTHLY TOTALS DEBUG ===")
        print(f"Month: {month}, Year: {year}")
        print(f"Total transactions: {all_transactions.count()}")
        
        # Calculate income total by manually iterating through ALL transactions
        income_total = 0
        expense_total = 0
        
        for trans in all_transactions:
            print(f"Transaction: {trans.date} | {trans.description} | {trans.category_type} | {trans.amount}")
            if trans.category_type == 'income':
                income_total += float(trans.amount)
            elif trans.category_type == 'expense':
                expense_total += float(trans.amount)
        
        print(f"Income total: {income_total}")
        print(f"Expense total: {expense_total}")
        print(f"=== END DEBUG ===\n")
        
        transaction_count = all_transactions.count()
        income_count = all_transactions.filter(category_type='income').count()
        expense_count = all_transactions.filter(category_type='expense').count()
        
        net_income = income_total - expense_total
        
        return Response({
            'success': True,
            'month': month,
            'year': year,
            'totals': {
                'income': income_total,
                'expense': expense_total,
                'net_income': net_income,
                'transaction_count': transaction_count,
                'income_count': income_count,
                'expense_count': expense_count
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            'success': False,
            'error': str(e)
        }, status=400)


def predict_category(description, force_reload=False):
    """
    Predict category for an expense description using ML Service.
    
    This function now calls the independent ML inference service instead of
    loading models locally. The backend decides WHEN to predict, the ML
    service decides HOW to predict.
    
    Args:
        description: The expense description
        force_reload: Ignored (kept for backward compatibility)
    
    Returns:
        dict: {
            'predicted_category': str,
            'confidence': float (0-1),
            'success': bool
        }
    """
    try:
        # Get ML service client
        ml_client = get_ml_client()
        
        # Call ML service for prediction
        result = ml_client.predict_category(description, fallback=None)
        
        if result is None:
            # ML service unavailable and no fallback
            return {
                'success': False,
                'error': 'AI service temporarily unavailable'
            }
        
        if not result.get('success', False):
            # ML service returned an error or fallback
            return {
                'success': False,
                'error': result.get('fallback_reason', 'Prediction failed'),
                'fallback': result.get('fallback', False)
            }
        
        # Success - return prediction
        return {
            'success': True,
            'predicted_category': result['category'],
            'confidence': result['confidence']
        }
    
    except Exception as e:
        # Unexpected error - log and return failure
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Unexpected error in predict_category: {str(e)}")
        
        return {
            'success': False,
            'error': 'An unexpected error occurred'
        }

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def predict_expense_category(request):
    """
    AI endpoint to predict expense category from description.
    
    Request body:
    {
        "description": "Zomato food order"
    }
    
    Response:
    {
        "predicted_category": "Food",
        "confidence": 0.85,
        "success": true
    }
    """
    description = request.data.get('description', '').strip()
    
    if not description:
        return Response({
            'success': False,
            'error': 'Description is required'
        }, status=400)
    
    result = predict_category(description)
    
    if result.get('success'):
        return Response({
            'predicted_category': result['predicted_category'],
            'confidence': round(result['confidence'], 4),
            'success': True
        }, status=200)
    else:
        return Response({
            'success': False,
            'error': result.get('error', 'Prediction failed')
        }, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_voice_entry(request):
    """
    Processes voice input and returns structured transaction details for user confirmation.
    """
    voice_text = (request.data.get("voice_text") or request.data.get("raw_text") or "").strip()

    if not voice_text:
        return Response({"error": "No voice input received"}, status=400)

    parsed = process_voice_transaction(voice_text)
    description = parsed.get("cleaned_description") or voice_text
    prediction = predict_category(description) if description else {"success": False}

    category = parsed.get("category_hint") or "Uncategorized"
    confidence = None

    if prediction.get("success"):
        category = prediction.get("predicted_category", category)
        confidence = round(float(prediction.get("confidence", 0.0)), 4)

    response_payload = {
        "raw_text": voice_text,
        "description": description,
        "amount": parsed.get("amount") or 0,
        "transaction_type": parsed.get("transaction_type", "expense"),
        "category": category,
        "category_confidence": confidence,
        "date": parsed.get("date") or now().date().isoformat(),
        "category_source": "ai" if prediction.get("success") else "rule",
    }

    return Response(response_payload)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_voice_transaction(request):
    """
    Saves user-confirmed transaction to the database.
    """
    description = (request.data.get("description") or "").strip()
    raw_amount = request.data.get("amount")
    transaction_type = (request.data.get("transaction_type") or request.data.get("type") or "expense").strip().lower()
    category = (request.data.get("category") or "").strip()
    date_value = (request.data.get("date") or now().date().isoformat())
    currency = (request.data.get("currency") or "INR").strip().upper()

    if not raw_amount:
        return Response({"error": "Amount is required"}, status=400)

    try:
        normalized_amount = str(Decimal(str(raw_amount)))
    except (InvalidOperation, ValueError):
        return Response({"error": "Invalid amount"}, status=400)

    payload = {
        "description": description or request.data.get("raw_text", ""),
        "amount": normalized_amount,
        "category": category or "Uncategorized",
        "date": date_value,
        "type": "income" if transaction_type == "income" else "expense",
        "currency": currency,
    }

    serializer = TransactionSerializer(data=payload, context={"request": request})
    serializer.is_valid(raise_exception=True)
    transaction = serializer.save()

    return Response(
        {
            "message": "Transaction saved successfully!",
            "transaction": TransactionSerializer(transaction, context={"request": request}).data,
        },
        status=201,
    )


@api_view(['GET'])
def get_transactions(request):
    transactions = Transaction.objects.select_related('category').all().order_by('-date')[:10]  # Fetch latest 10 transactions

    data = [
        {
            "id": t.id,
            "category_name": t.category.name,  # Fetch category name
            "category_type": t.category_type,  # Income or Expense
            "description": t.description,
            "amount": float(t.amount),
            "date": t.date.isoformat(),  # Convert date to JSON format
        }
        for t in transactions
    ]
    
    return JsonResponse(data, safe=False)






@api_view(['GET'])
@permission_classes([IsAuthenticated])
def upcoming_bills(request):
    """
    Fetch upcoming recurring payments for the user.
    """
    user = request.user
    today = now().date()
    upcoming_payments = RecurringPayment.objects.filter(
        user=user, 
        next_payment_date__gte=today,  # Payments due today or later
        status="active"
    ).order_by('next_payment_date')

    bills_list = [
        {
            "id": payment.id,
            "name": payment.name,
            "amount": float(payment.amount),
            "category": payment.category,
            "frequency": payment.frequency,
            "days_remaining": (payment.next_payment_date - today).days,
            "next_payment_date": payment.next_payment_date.strftime("%Y-%m-%d")
        } for payment in upcoming_payments
    ]

    return Response(bills_list)


def track_budget_history(user):
    """
    Stores historical budget data and calculates suggested budget.
    """
    current_month = now().month
    current_year = now().year

    budgets = Budget.objects.filter(user=user)

    for budget in budgets:
        category = budget.category
        prev_limit = budget.monthly_limit

        # Get total spending for this category in the last month
        last_month = (now() - timedelta(days=30)).month
        total_spent = Transaction.objects.filter(
            user=user, category_id=category, date__month=last_month
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        # AI Logic to Suggest Budget Adjustment
        suggested_limit = prev_limit
        if total_spent > prev_limit:
            suggested_limit = prev_limit * 1.1  # Increase budget by 10% if overspending
        elif total_spent < (prev_limit * 0.7):
            suggested_limit = prev_limit * 0.9  # Decrease budget by 10% if underused

        # Save to BudgetHistory Table
        BudgetHistory.objects.update_or_create(
            user=user,
            category=category,
            month=current_month,
            year=current_year,
            defaults={
                "previous_limit": prev_limit,
                "actual_spent": total_spent,
                "suggested_limit": suggested_limit,
            }
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def export_transactions_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Date', 'Category', 'Amount', 'Description'])

    transactions = Transaction.objects.all().values_list('id', 'date', 'category__name', 'amount', 'description')
    for transaction in transactions:
        writer.writerow(transaction)

    return response


# Pagination class for handling multiple transactions
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10  # Show 10 transactions per page
    page_size_query_param = 'page_size'
    max_page_size = 100


# View for listing and creating transactions
class TransactionListCreateView(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['description']
    ordering_fields = ['date', 'amount']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Transaction.objects.filter(user_id=user.id).select_related('category').order_by('-date')
        category = self.request.query_params.get('category', None)
        min_amount = self.request.query_params.get('min_amount', None)
        date = self.request.query_params.get('date', None)

        if category:
            queryset = queryset.filter(category__id=category)
        if min_amount:
            queryset = queryset.filter(amount__gte=min_amount)
        if date:
            queryset = queryset.filter(date=date)

        return queryset
    
    def get_serializer_context(self):
        """Ensure request is available in serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context




class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Transaction.objects.filter(user_id=user.id)
    
    def get_serializer_context(self):
        """Ensure request is available in serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.ModelSerializer
    serializer_class.Meta = type("Meta", (object,), {"model": Category, "fields": "__all__"})



class CurrencyConverter(APIView):
    def get(self, request):
        base_currency = request.query_params.get('base', 'USD')
        target_currency = request.query_params.get('target', 'INR')

        api_url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
        response = requests.get(api_url)

        if response.status_code != 200:
            return Response({"error": "Failed to fetch exchange rates"}, status=500)

        data = response.json()
        conversion_rate = data["rates"].get(target_currency, None)

        if conversion_rate:
            return Response({"rate": conversion_rate}, status=200)
        else:
            return Response({"error": "Invalid currency"}, status=400)


class BudgetView(generics.ListCreateAPIView):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TransactionsBudget.objects.filter(user_id=self.kwargs['user_id'])

# Fetch budget history
class BudgetHistoryView(generics.ListAPIView):
    serializer_class = BudgetHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TransactionsBudgetHistory.objects.filter(
            user_id=self.kwargs['user_id'], 
            month=self.request.query_params.get('month'), 
            year=self.request.query_params.get('year')
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_correction_stats(request):
    """Get correction statistics for the current user."""
    from .models import CategoryCorrection
    from django.db.models import Count, Avg
    
    user = request.user
    corrections = CategoryCorrection.objects.filter(user=user)
    total = corrections.count()
    
    if total == 0:
        return Response({
            'success': True,
            'total_corrections': 0,
            'message': 'No corrections yet. Start correcting AI predictions to improve the model!'
        })
    
    # Most wrong AI predictions
    wrong_predictions = corrections.values('ai_predicted_category').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Most corrected to categories
    corrected_to = corrections.values('user_corrected_category').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Average confidence of wrong predictions
    avg_conf = corrections.filter(
        confidence__isnull=False
    ).aggregate(Avg('confidence'))['confidence__avg']
    
    return Response({
        'success': True,
        'total_corrections': total,
        'average_confidence_of_wrong_predictions': round(avg_conf * 100, 1) if avg_conf else None,
        'most_frequently_wrong': list(wrong_predictions),
        'most_frequently_corrected_to': list(corrected_to),
        'ready_to_retrain': total >= 50
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ai_learning_progress(request):
    """Get AI learning progress for the current user."""
    from .models import CategoryCorrection
    
    user = request.user
    total_corrections = CategoryCorrection.objects.filter(user=user).count()
    min_required = 50
    progress_percent = min(int((total_corrections / min_required) * 100), 100)
    
    return Response({
        'success': True,
        'total_corrections': total_corrections,
        'min_required_for_retraining': min_required,
        'progress_percent': progress_percent,
        'corrections_remaining': max(0, min_required - total_corrections),
        'ready_to_retrain': total_corrections >= min_required,
        'message': f'{total_corrections}/{min_required} corrections logged. ' + 
                   ('Ready to improve AI model!' if total_corrections >= min_required else 'Keep correcting predictions!')
    })