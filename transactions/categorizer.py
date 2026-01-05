"""
DEPRECATED: ML functionality has been moved to a separate microservice.

This file is kept for backward compatibility but all functions return None/False.
For ML predictions, use the ml_client module to call the ML inference service.

Architecture Change (2024):
- Backend: Lightweight Django service (no ML dependencies)
- ML Service: Independent FastAPI service handling all ML operations
- Communication: HTTP REST API with circuit breaker pattern

Usage:
    from .ml_client import get_ml_client
    
    client = get_ml_client()
    result = client.predict_category(description="Coffee at Starbucks")
    
    if result.success:
        category = result.predicted_category
        confidence = result.confidence
"""

def categorize_transaction(description):
    """
    DEPRECATED: Use ml_client.get_ml_client().predict_category() instead.
    
    This function no longer performs ML inference. Returns None to indicate
    the caller should use the new ML service client.
    """
    return None


def update_category(description, correct_category):
    """
    DEPRECATED: Model retraining is handled by the ML service.
    
    For learning from corrections, use the ML service's feedback endpoint:
    POST /api/v1/feedback with the correction data.
    """
    return False
