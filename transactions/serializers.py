from rest_framework import serializers
from .models import Transaction
from .models import Budget,BudgetHistory
from .models import Category


class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ['id', 'user', 'category', 'monthly_limit', 'created_at']
        read_only_fields = ['user']


class CategorySerializer(serializers.ModelSerializer):
    
    class Meta:
        unique_together = ('user', 'name')  




class TransactionSerializer(serializers.ModelSerializer):
    currency = serializers.CharField(required=False, default='USD', allow_blank=True)
    category_name = serializers.SerializerMethodField(read_only=True)
    category = serializers.CharField(required=False, allow_null=True, allow_blank=True)  # Accept category name as string
    type = serializers.CharField(write_only=True, required=False, allow_blank=True)  # Accept 'type' from frontend
    paymentMethod = serializers.CharField(write_only=True, required=False, allow_blank=True)  # Accept but ignore
    ai_predicted_category = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)  # Track AI prediction
    ai_confidence = serializers.FloatField(write_only=True, required=False, allow_null=True)  # Track confidence

    class Meta:
        model = Transaction
        fields = ['id', 'date', 'category', 'category_name', 'currency', 'amount', 'description', 'category_type', 'created_at', 'updated_at', 'type', 'paymentMethod', 'ai_predicted_category', 'ai_confidence']
        read_only_fields = ['user', 'created_at', 'updated_at', 'id']
    
    def get_category_name(self, obj):
        """Return category name or 'Uncategorized' if null"""
        try:
            return obj.category.name if obj.category else 'Uncategorized'
        except Exception:
            return 'Uncategorized'
    
    def create(self, validated_data):
        # Map 'type' to 'category_type' if provided
        if 'type' in validated_data:
            validated_data['category_type'] = validated_data.pop('type')
        
        # Remove paymentMethod as it's not in the model
        validated_data.pop('paymentMethod', None)
        
        # Extract AI prediction metadata for correction tracking
        ai_predicted = validated_data.pop('ai_predicted_category', None) or ''
        ai_conf = validated_data.pop('ai_confidence', None)
        
        # Handle category name - get or create Category object
        category_name = validated_data.pop('category', None)
        request = self.context.get('request')
        description = validated_data.get('description', '').strip()
        
        # Track if this is a correction for logging
        is_correction = False
        
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
            
            # Get or create category if name provided
            if category_name and category_name.strip():
                category_obj, created = Category.objects.get_or_create(
                    name=category_name,
                    user=request.user,  # Include user in lookup
                    defaults={'user': request.user}
                )
                validated_data['category'] = category_obj
                
                # Check if AI prediction was overridden
                if ai_predicted and ai_predicted.strip():
                    ai_pred_clean = ai_predicted.strip()
                    cat_name_clean = category_name.strip()
                    
                    # Log correction if different (case-insensitive)
                    if ai_pred_clean.lower() != cat_name_clean.lower():
                        from .models import CategoryCorrection
                        CategoryCorrection.objects.create(
                            user=request.user,
                            description=description or ai_pred_clean,
                            ai_predicted_category=ai_pred_clean,
                            user_corrected_category=cat_name_clean,
                            confidence=float(ai_conf) if ai_conf else None
                        )
                        is_correction = True
                        print(f"✅ Logged correction: {ai_pred_clean} → {cat_name_clean}")
            else:
                validated_data['category'] = None
        
        transaction = super().create(validated_data)
        
        if is_correction:
            print(f"Transaction ID {transaction.id}: Correction logged and saved")
        
        return transaction
    
    def update(self, instance, validated_data):
        # Map 'type' to 'category_type' if provided
        if 'type' in validated_data:
            validated_data['category_type'] = validated_data.pop('type')
        
        # Remove paymentMethod as it's not in the model
        validated_data.pop('paymentMethod', None)
        
        # Handle category name - get or create Category object
        category_name = validated_data.pop('category', None)
        request = self.context.get('request')
        
        if request and hasattr(request, 'user'):
            # Get or create category if name provided
            if category_name and category_name.strip():
                category_obj, created = Category.objects.get_or_create(
                    name=category_name,
                    user=request.user,  # Include user in lookup
                    defaults={'user': request.user}
                )
                validated_data['category'] = category_obj
            else:
                validated_data['category'] = None
        
        return super().update(instance, validated_data)

class BudgetHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetHistory
        fields = '__all__'


