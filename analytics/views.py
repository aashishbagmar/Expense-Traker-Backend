from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.utils.timezone import now
from django.db.models import Sum, Count, Q
from datetime import timedelta, datetime
from transactions.models import Transaction
from django.contrib.auth import get_user_model
from .serializers import UserCountSerializer, RevenueSerializer
# from payments.models import Subscription  # Payments app removed
from django.http import FileResponse
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import matplotlib.pyplot as plt
import base64
from matplotlib.pyplot import figure



User = get_user_model()


def generate_pie_chart_base64(category_breakdown, expense_total):
    """Generate pie chart as Base64-encoded PNG for HTML embedding"""
    try:
        if not category_breakdown or expense_total == 0:
            return None
        
        # Prepare data for pie chart
        categories = [item['category'] for item in category_breakdown[:6]]
        amounts = [float(item['amount']) for item in category_breakdown[:6]]
        
        # Handle "Other" category if more than 6
        if len(category_breakdown) > 6:
            other_amount = sum(float(item['amount']) for item in category_breakdown[6:])
            if other_amount > 0:
                categories.append('Other')
                amounts.append(other_amount)
        
        # Create pie chart
        fig, ax = plt.subplots(figsize=(8, 6))
        colors_list = ['#e74c3c', '#e67e22', '#f39c12', '#d35400', '#c0392b', '#a93226', '#7f8c8d']
        ax.pie(amounts, labels=categories, autopct='%1.1f%%', colors=colors_list[:len(amounts)], startangle=90)
        ax.set_title('Expense Distribution by Category', fontsize=14, fontweight='bold', pad=20)
        
        # Save to BytesIO
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        # Convert to Base64
        chart_base64 = base64.b64encode(buf.read()).decode('utf-8')
        return f'data:image/png;base64,{chart_base64}'
    except Exception as e:
        print(f"Error generating pie chart: {e}")
        return None


def render_financial_report_html(report_data):
    """Render financial report HTML from template with data"""
    try:
        from datetime import datetime as dt
        from django.utils.safestring import mark_safe
        
        # Extract data from report_data
        month = report_data.get('month', 1)
        year = report_data.get('year', 2025)
        summary = report_data.get('summary', {})
        category_breakdown = report_data.get('category_breakdown', [])
        transactions = report_data.get('transactions', [])
        user_name = report_data.get('user_name', 'User')
        
        # Format numbers with Rs. prefix
        total_income = f"Rs. {summary.get('income', 0):,.2f}"
        total_expense = f"Rs. {summary.get('expense', 0):,.2f}"
        net_savings = f"Rs. {summary.get('net_savings', 0):,.2f}"
        savings_rate = f"{summary.get('savings_rate', 0):.1f}%"
        
        # Format report period and generated date
        report_period = dt(year, month, 1).strftime('%B %Y')
        generated_date = now().strftime('%d %B %Y at %H:%M:%S')
        
        # Generate pie chart
        pie_chart = generate_pie_chart_base64(category_breakdown, summary.get('expense', 0))
        
        # Build expense breakdown rows HTML
        expense_breakdown_rows = ""
        for item in category_breakdown:
            expense_breakdown_rows += f"""
            <tr>
                <td>{item.get('category', 'Uncategorized')}</td>
                <td>Rs. {item.get('amount', 0):,.2f}</td>
                <td>{item.get('percentage', 0):.1f}%</td>
            </tr>
            """
        
        # Build transaction rows HTML
        transaction_rows = ""
        for trans in transactions:
            transaction_rows += f"""
            <tr>
                <td>{trans.get('date', '')}</td>
                <td>{trans.get('description', '')}</td>
                <td>{trans.get('category', 'Uncategorized')}</td>
                <td>{trans.get('type', '').upper()}</td>
                <td>Rs. {trans.get('amount', 0):,.2f}</td>
            </tr>
            """
        
        # Calculate AI insights
        ai_insights = ""
        if category_breakdown:
            top_item = category_breakdown[0]
            top_category = top_item.get('category', 'Uncategorized')
            top_percentage = top_item.get('percentage', 0)
            ai_insights += f"<p><strong>Top Spending Category:</strong> {top_category} accounts for {top_percentage:.1f}% of your total expenses.</p>"
        
        income_val = summary.get('income', 0)
        if income_val > 0:
            savings_rate_val = summary.get('savings_rate', 0)
            if savings_rate_val >= 50:
                ai_insights += "<p>Excellent savings rate! You are saving more than half of your income. Keep up this financial discipline!</p>"
            elif savings_rate_val >= 30:
                ai_insights += "<p>Good savings rate. You are maintaining a healthy financial discipline.</p>"
            elif savings_rate_val >= 10:
                ai_insights += "<p>You are saving a portion of your income. Consider analyzing your expenses to increase your savings rate.</p>"
            else:
                ai_insights += "<p>Your current savings rate is low. Review your expenses to improve your financial health.</p>"
        else:
            ai_insights += "<p>No income recorded for this period.</p>"
        
        # Context data for template - mark HTML strings as safe
        context = {
            'user_name': user_name,
            'report_period': report_period,
            'generated_date': generated_date,
            'total_income': total_income,
            'total_expense': total_expense,
            'net_savings': net_savings,
            'savings_rate': savings_rate,
            'expense_breakdown_rows': mark_safe(expense_breakdown_rows),
            'transaction_rows': mark_safe(transaction_rows),
            'ai_insights': mark_safe(ai_insights),
            'pie_chart_path': pie_chart
        }
        
        # Render template
        html_string = render_to_string('report_template.html', context)
        return html_string
    except Exception as e:
        print(f"Error rendering HTML template: {e}")
        import traceback
        traceback.print_exc()
        return None


User = get_user_model()

@api_view(['GET'])
def user_statistics(request):
    total_users = User.objects.count()
    premium_users = User.objects.filter(is_premium=True).count()

    data = {
        "total_users": total_users,
        "premium_users": premium_users,
    }
    serializer = UserCountSerializer(data)
    return Response(serializer.data)

@api_view(['GET'])
def revenue_statistics(request):
    total_revenue = Transaction.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    current_month = now().month
    monthly_revenue = Transaction.objects.filter(
        created_at__month=current_month
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    data = {
        "total_revenue": total_revenue,
        "monthly_revenue": monthly_revenue,
    }
    serializer = RevenueSerializer(data)
    return Response(serializer.data)

@api_view(['GET'])
def activity_logs(request):
    # TODO: Implement activity logs if needed
    return Response({'message': 'Activity logs not yet implemented'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_financial_report_data(request):
    """
    Get aggregated financial report data with flexible filtering.
    Filters: month, year, category, transaction_type (income/expense/all)
    Returns: income, expense, net savings, category breakdown, all transactions
    """
    try:
        # Get filter parameters
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        category_filter = request.query_params.get('category')  # Category name or 'all'
        transaction_type = request.query_params.get('transaction_type', 'all')  # 'income', 'expense', 'all'
        
        # Set defaults
        if month and year:
            month = int(month)
            year = int(year)
        else:
            current_date = now()
            month = current_date.month
            year = current_date.year
        
        user = request.user
        
        # Base query: all transactions for the user, filtered by month/year
        base_query = Transaction.objects.filter(
            user=user,
            date__month=month,
            date__year=year
        )
        
        print(f"\n=== FINANCIAL REPORT DATA ===")
        print(f"Filters: Month={month}, Year={year}, Category={category_filter}, Type={transaction_type}")
        print(f"Total transactions in period: {base_query.count()}")
        
        # Apply category filter if specified
        if category_filter and category_filter.lower() != 'all':
            base_query = base_query.filter(category__name__iexact=category_filter)
            print(f"After category filter: {base_query.count()}")
        
        # Apply transaction type filter
        if transaction_type.lower() != 'all':
            base_query = base_query.filter(category_type=transaction_type.lower())
            print(f"After type filter: {base_query.count()}")
        
        # Calculate totals
        income_total = base_query.filter(category_type='income').aggregate(Sum('amount'))['amount__sum'] or 0
        expense_total = base_query.filter(category_type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
        net_savings = float(income_total) - float(expense_total)
        savings_rate = (net_savings / float(income_total) * 100) if float(income_total) > 0 else 0
        
        print(f"Income: {income_total}, Expense: {expense_total}, Net: {net_savings}")
        
        # Get expense breakdown by category
        expense_breakdown = base_query.filter(
            category_type='expense'
        ).values('category__name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Format breakdown for response
        breakdown_data = []
        for item in expense_breakdown:
            category_name = item['category__name'] or 'Uncategorized'
            amount = float(item['total'])
            count = item['count']
            percentage = (amount / float(expense_total) * 100) if float(expense_total) > 0 else 0
            breakdown_data.append({
                'category': category_name,
                'amount': amount,
                'count': count,
                'percentage': round(percentage, 1)
            })
        
        # Get all transactions for the report
        transactions = base_query.select_related('category').order_by('-date')
        transactions_data = []
        for trans in transactions:
            transactions_data.append({
                'id': trans.id,
                'date': trans.date.strftime('%Y-%m-%d'),
                'description': trans.description or '',
                'category': trans.category.name if trans.category else 'Uncategorized',
                'type': trans.category_type,
                'amount': float(trans.amount)
            })
        
        print(f"=== END REPORT ===\n")
        
        return Response({
            'success': True,
            'month': month,
            'year': year,
            'filters': {
                'category': category_filter or 'all',
                'transaction_type': transaction_type
            },
            'summary': {
                'income': float(income_total),
                'expense': float(expense_total),
                'net_savings': net_savings,
                'savings_rate': round(savings_rate, 1),
                'transaction_count': base_query.count(),
                'income_count': base_query.filter(category_type='income').count(),
                'expense_count': base_query.filter(category_type='expense').count()
            },
            'category_breakdown': breakdown_data,
            'transactions': transactions_data
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({'success': False, 'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_financial_report_pdf(request):
    """Generate professional PDF using HTML template and WeasyPrint"""
    try:
        # Get filter parameters
        month = request.query_params.get('month') if hasattr(request, 'query_params') else request.GET.get('month')
        year = request.query_params.get('year') if hasattr(request, 'query_params') else request.GET.get('year')
        category_filter = request.query_params.get('category') if hasattr(request, 'query_params') else request.GET.get('category')
        transaction_type = request.query_params.get('transaction_type', 'all') if hasattr(request, 'query_params') else request.GET.get('transaction_type', 'all')
        
        # Set defaults
        if month and year:
            month = int(month)
            year = int(year)
        else:
            current_date = now()
            month = current_date.month
            year = current_date.year
        
        user = request.user
        
        # Build base query with filtering (same as financial_report endpoint)
        base_query = Transaction.objects.filter(
            user=user,
            date__month=month,
            date__year=year
        )
        
        # Apply category filter if specified
        if category_filter and category_filter.lower() != 'all':
            base_query = base_query.filter(category__name__iexact=category_filter)
        
        # Apply transaction type filter
        if transaction_type.lower() != 'all':
            base_query = base_query.filter(category_type=transaction_type.lower())
        
        # Calculate totals
        income_total = base_query.filter(category_type='income').aggregate(Sum('amount'))['amount__sum'] or 0
        expense_total = base_query.filter(category_type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
        net_savings = float(income_total) - float(expense_total)
        savings_rate = (net_savings / float(income_total) * 100) if float(income_total) > 0 else 0
        
        # Get expense breakdown by category
        expense_breakdown = base_query.filter(
            category_type='expense'
        ).values('category__name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Format breakdown for response
        breakdown_data = []
        for item in expense_breakdown:
            category_name = item['category__name'] or 'Uncategorized'
            amount = float(item['total'])
            count = item['count']
            percentage = (amount / float(expense_total) * 100) if float(expense_total) > 0 else 0
            breakdown_data.append({
                'category': category_name,
                'amount': amount,
                'count': count,
                'percentage': round(percentage, 1)
            })
        
        # Get all transactions for the report
        transactions = base_query.select_related('category').order_by('-date')
        transactions_data = []
        for trans in transactions:
            transactions_data.append({
                'id': trans.id,
                'date': trans.date.strftime('%Y-%m-%d'),
                'description': trans.description or '',
                'category': trans.category.name if trans.category else 'Uncategorized',
                'type': trans.category_type,
                'amount': float(trans.amount)
            })
        
        # Build report data
        report_data = {
            'month': month,
            'year': year,
            'user_name': user.get_full_name() or user.username,
            'summary': {
                'income': float(income_total),
                'expense': float(expense_total),
                'net_savings': net_savings,
                'savings_rate': round(savings_rate, 1),
                'transaction_count': base_query.count(),
                'income_count': base_query.filter(category_type='income').count(),
                'expense_count': base_query.filter(category_type='expense').count()
            },
            'category_breakdown': breakdown_data,
            'transactions': transactions_data
        }
        
        # Render HTML from template
        html_string = render_financial_report_html(report_data)
        if not html_string:
            raise Exception('Failed to render HTML template')
        
        # Convert HTML to PDF using xhtml2pdf
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_string, pdf_buffer)
        
        if pisa_status.err:
            raise Exception(f'PDF generation failed: {pisa_status.err}')
        
        pdf_buffer.seek(0)
        
        # Get month name for filename
        month_name = datetime(year, month, 1).strftime('%B')
        
        # Return PDF as file download
        return FileResponse(
            pdf_buffer,
            as_attachment=True,
            filename=f'Financial_Report_{month_name}_{year}.pdf',
            content_type='application/pdf'
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=400)
