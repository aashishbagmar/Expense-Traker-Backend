# transactions/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transaction, CategoryCorrection
from .utils import check_budget_alert
import subprocess
import os
import sys


@receiver(post_save, sender=Transaction)
def transaction_alert(sender, instance, created, **kwargs):
    if created and instance.category_type == 'expense':
        check_budget_alert(instance.user)


@receiver(post_save, sender=CategoryCorrection)
def trigger_adaptive_learning(sender, instance, created, **kwargs):
    """
    Automatically retrain AI model after corrections are logged.
    Implements incremental adaptive learning - retrains every 5 corrections.
    """
    if not created:
        return  # Only trigger on new corrections
    
    # Count total corrections
    total_corrections = CategoryCorrection.objects.count()
    
    # Retrain every 5 corrections for rapid adaptation
    if total_corrections % 5 == 0:
        print(f"\n🧠 Adaptive Learning Triggered: {total_corrections} total corrections")
        print(f"📚 Auto-retraining AI model...")
        
        try:
            # Import here to avoid circular imports
            from django.core.management import call_command
            
            # Call retrain command synchronously for immediate model update
            call_command('retrain_from_corrections', '--min-corrections', str(total_corrections - 1))
            
            print(f"✅ AI Model retrained! Improvements active immediately.")
        except Exception as e:
            print(f"⚠️ Retraining encountered an issue: {e}")

