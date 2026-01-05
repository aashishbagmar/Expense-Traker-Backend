"""
ML Service Client for Backend
==============================

This module provides a client to communicate with the ML inference service.
It handles all HTTP communication, error handling, timeouts, and fallbacks.

Key Principles:
- Backend decides WHEN to call ML service
- ML service decides HOW to predict
- Backend MUST NOT crash if ML service is down
- Backend MUST provide graceful fallbacks
"""

import requests
import logging
from typing import Optional, Dict, Any
from django.conf import settings
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class MLServiceError(Exception):
    """Base exception for ML service errors."""
    pass


class MLServiceUnavailableError(MLServiceError):
    """Raised when ML service is not available."""
    pass


class MLServiceTimeoutError(MLServiceError):
    """Raised when ML service times out."""
    pass


class MLServiceClient:
    """
    Client for communicating with ML inference service.
    
    Handles:
    - HTTP requests to ML service
    - Timeout management
    - Error handling and logging
    - Circuit breaker pattern
    - Graceful fallbacks
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 10,
        enabled: bool = True,
        fallback_enabled: bool = True
    ):
        """
        Initialize ML service client.
        
        Args:
            base_url: ML service base URL (from settings if None)
            timeout: Request timeout in seconds
            enabled: Whether ML service is enabled
            fallback_enabled: Whether to use fallback on failure
        """
        self.base_url = base_url or getattr(
            settings, 'ML_SERVICE_URL', 'http://localhost:8000'
        )
        self.timeout = timeout
        self.enabled = enabled
        self.fallback_enabled = fallback_enabled
        
        # Circuit breaker state
        self._failure_count = 0
        self._failure_threshold = 3
        self._recovery_timeout = 60  # seconds
        self._circuit_open_time = None
        self._is_circuit_open = False
    
    def _is_circuit_breaker_open(self) -> bool:
        """
        Check if circuit breaker is open (too many failures).
        
        Returns:
            True if circuit is open (should not try requests)
        """
        if not self._is_circuit_open:
            return False
        
        # Check if recovery timeout has passed
        if self._circuit_open_time:
            elapsed = (datetime.now() - self._circuit_open_time).total_seconds()
            if elapsed >= self._recovery_timeout:
                logger.info("Circuit breaker recovery timeout reached, attempting to close")
                self._is_circuit_open = False
                self._failure_count = 0
                self._circuit_open_time = None
                return False
        
        return True
    
    def _record_failure(self):
        """Record a failed request and potentially open circuit breaker."""
        self._failure_count += 1
        
        if self._failure_count >= self._failure_threshold:
            self._is_circuit_open = True
            self._circuit_open_time = datetime.now()
            logger.warning(
                f"Circuit breaker opened after {self._failure_count} failures. "
                f"Will retry after {self._recovery_timeout}s"
            )
    
    def _record_success(self):
        """Record a successful request and close circuit breaker if open."""
        if self._is_circuit_open:
            logger.info("Circuit breaker closed after successful request")
        
        self._failure_count = 0
        self._is_circuit_open = False
        self._circuit_open_time = None
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check ML service health.
        
        Returns:
            Health status dictionary
        
        Raises:
            MLServiceUnavailableError: If service is not reachable
        """
        if not self.enabled:
            return {
                'status': 'disabled',
                'message': 'ML service is disabled in settings'
            }
        
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5  # Short timeout for health check
            )
            return response.json()
        
        except requests.RequestException as e:
            logger.error(f"ML service health check failed: {str(e)}")
            raise MLServiceUnavailableError(f"ML service unavailable: {str(e)}")
    
    def predict_category(
        self,
        description: str,
        fallback: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Predict expense category from description.
        
        Args:
            description: Transaction description
            fallback: Fallback category if prediction fails
        
        Returns:
            Prediction result dict with 'category', 'confidence', etc.
            Returns None if service unavailable and fallback enabled.
        
        Examples:
            >>> client = MLServiceClient()
            >>> result = client.predict_category("Zomato food order")
            >>> print(result['category'])  # "Food"
            >>> print(result['confidence'])  # 0.8523
        """
        # Check if service is enabled
        if not self.enabled:
            logger.debug("ML service disabled, skipping prediction")
            return self._fallback_response(description, fallback, "Service disabled")
        
        # Check circuit breaker
        if self._is_circuit_breaker_open():
            logger.warning("Circuit breaker open, skipping ML service call")
            return self._fallback_response(
                description,
                fallback,
                "Circuit breaker open"
            )
        
        # Validate input
        if not description or not description.strip():
            logger.warning("Empty description provided")
            return None
        
        try:
            # Make prediction request
            response = requests.post(
                f"{self.base_url}/api/v1/predict/category",
                json={"description": description},
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            # Handle response
            if response.status_code == 200:
                data = response.json()
                self._record_success()
                
                # Extract relevant fields
                prediction = data.get('prediction', {})
                metadata = data.get('metadata', {})
                
                result = {
                    'category': prediction.get('category'),
                    'confidence': prediction.get('confidence'),
                    'alternatives': prediction.get('alternatives', []),
                    'preprocessed_text': metadata.get('preprocessed_text'),
                    'inference_time_ms': metadata.get('inference_time_ms'),
                    'model_version': metadata.get('model_version'),
                    'success': True
                }
                
                logger.info(
                    f"ML prediction: '{description}' -> {result['category']} "
                    f"(confidence: {result['confidence']:.4f})"
                )
                
                return result
            
            elif response.status_code == 503:
                # Service unavailable (models not loaded)
                logger.error("ML service unavailable (503)")
                self._record_failure()
                return self._fallback_response(
                    description,
                    fallback,
                    "Service unavailable"
                )
            
            else:
                # Other error
                logger.error(f"ML service error: {response.status_code} - {response.text}")
                self._record_failure()
                return self._fallback_response(
                    description,
                    fallback,
                    f"HTTP {response.status_code}"
                )
        
        except requests.Timeout:
            logger.error(f"ML service timeout after {self.timeout}s")
            self._record_failure()
            return self._fallback_response(description, fallback, "Timeout")
        
        except requests.ConnectionError as e:
            logger.error(f"ML service connection error: {str(e)}")
            self._record_failure()
            return self._fallback_response(description, fallback, "Connection error")
        
        except Exception as e:
            logger.exception(f"Unexpected error calling ML service: {str(e)}")
            self._record_failure()
            return self._fallback_response(description, fallback, "Unexpected error")
    
    def _fallback_response(
        self,
        description: str,
        fallback_category: Optional[str],
        reason: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create fallback response when ML service fails.
        
        Args:
            description: Original description
            fallback_category: Fallback category (if any)
            reason: Reason for fallback
        
        Returns:
            Fallback response dict or None
        """
        if not self.fallback_enabled:
            return None
        
        logger.info(f"Using fallback for '{description}': {reason}")
        
        return {
            'category': fallback_category,
            'confidence': 0.0,
            'alternatives': [],
            'success': False,
            'fallback': True,
            'fallback_reason': reason
        }
    
    def predict_batch(
        self,
        descriptions: list[str]
    ) -> list[Dict[str, Any]]:
        """
        Predict categories for multiple descriptions.
        
        Args:
            descriptions: List of transaction descriptions
        
        Returns:
            List of prediction results
        """
        if not self.enabled or self._is_circuit_breaker_open():
            return [self._fallback_response(desc, None, "Service disabled or circuit open") 
                    for desc in descriptions]
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/predict/batch",
                json={"descriptions": descriptions},
                timeout=self.timeout * 2,  # Longer timeout for batch
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self._record_success()
                return data.get('predictions', [])
            else:
                logger.error(f"Batch prediction failed: {response.status_code}")
                self._record_failure()
                return [self._fallback_response(desc, None, "Batch failed") 
                        for desc in descriptions]
        
        except Exception as e:
            logger.error(f"Batch prediction error: {str(e)}")
            self._record_failure()
            return [self._fallback_response(desc, None, str(e)) 
                    for desc in descriptions]


# Global client instance
_ml_client = None


def get_ml_client() -> MLServiceClient:
    """
    Get global ML service client instance.
    
    Returns:
        MLServiceClient instance
    """
    global _ml_client
    
    if _ml_client is None:
        _ml_client = MLServiceClient(
            base_url=getattr(settings, 'ML_SERVICE_URL', 'http://localhost:8000'),
            timeout=getattr(settings, 'ML_SERVICE_TIMEOUT', 10),
            enabled=getattr(settings, 'ML_SERVICE_ENABLED', True),
            fallback_enabled=getattr(settings, 'ML_SERVICE_FALLBACK', True)
        )
    
    return _ml_client
