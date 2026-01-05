# transactions/admin.py
from django.contrib import admin
from .models import Transaction, Category, Budget, CategoryCorrection

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'category', 'date', 'category_type')
    search_fields = ('user__username', 'category')
    list_filter = ('category_type', 'date')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user')
    search_fields = ('name', 'user__username')

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'monthly_limit', 'created_at')
    search_fields = ('user__username', 'category__name')

@admin.register(CategoryCorrection)
class CategoryCorrectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'description', 'ai_predicted_category', 'user_corrected_category', 'confidence', 'created_at')
    search_fields = ('user__username', 'description', 'ai_predicted_category', 'user_corrected_category')
    list_filter = ('user', 'created_at')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
