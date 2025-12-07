"""
GCash Payment Gateway Integration Service
Handles checkout creation, webhook validation, and refund processing
"""
import requests
import hmac
import hashlib
import json
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class GCashService:
    """Service class for GCash payment integration"""
    
    # GCash API endpoints (update these with actual GCash API endpoints)
    SANDBOX_BASE_URL = "https://api.gcash.com/sandbox"
    PRODUCTION_BASE_URL = "https://api.gcash.com"
    
    def __init__(self):
        self.api_key = getattr(settings, 'GCASH_API_KEY', '')
        self.api_secret = getattr(settings, 'GCASH_API_SECRET', '')
        self.merchant_id = getattr(settings, 'GCASH_MERCHANT_ID', '')
        self.is_sandbox = getattr(settings, 'GCASH_SANDBOX', True)
        self.base_url = self.SANDBOX_BASE_URL if self.is_sandbox else self.PRODUCTION_BASE_URL
        
        if not all([self.api_key, self.api_secret, self.merchant_id]):
            logger.warning("GCash API credentials not fully configured")
    
    def _get_headers(self):
        """Get authentication headers for GCash API"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-Merchant-ID': self.merchant_id,
        }
    
    def _generate_signature(self, payload, timestamp=None):
        """Generate HMAC signature for webhook validation"""
        if not timestamp:
            timestamp = str(int(timezone.now().timestamp()))
        
        message = f"{timestamp}{json.dumps(payload, sort_keys=True)}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature, timestamp
    
    def create_checkout(self, payment, request):
        """
        Create a GCash checkout session and return checkout URL
        
        Args:
            payment: Payment model instance
            request: Django request object
            
        Returns:
            dict: {'checkout_url': str, 'transaction_id': str} or {'error': str}
        """
        logger.info(f"Creating GCash checkout for payment {payment.payment_id}")
        try:
            # Build callback URLs
            success_url = request.build_absolute_uri(
                reverse('payments:payment_success', args=[payment.payment_id])
            )
            cancel_url = request.build_absolute_uri(
                reverse('payments:payment_failed', args=[payment.payment_id])
            )
            webhook_url = request.build_absolute_uri(
                reverse('payments:gcash_webhook')
            )
            
            logger.debug(f"Success URL: {success_url}")
            logger.debug(f"Cancel URL: {cancel_url}")
            logger.debug(f"Webhook URL: {webhook_url}")
            
            # Prepare checkout payload
            payload = {
                'amount': float(payment.amount),
                'currency': 'PHP',
                'description': f'Water Bill Payment - {payment.bill.billing_month.strftime("%B %Y")}',
                'reference_number': payment.reference_number,
                'customer': {
                    'name': payment.customer.get_full_name(),
                    'email': payment.customer.email,
                    'phone': payment.customer.phone_number or '',
                },
                'success_url': success_url,
                'cancel_url': cancel_url,
                'webhook_url': webhook_url,
                'metadata': {
                    'payment_id': str(payment.payment_id),
                    'bill_id': payment.bill.id,
                    'customer_id': payment.customer.id,
                }
            }
            
            # Generate signature
            signature, timestamp = self._generate_signature(payload)
            headers = self._get_headers()
            headers['X-Signature'] = signature
            headers['X-Timestamp'] = timestamp
            
            logger.debug(f"Making API request to {self.base_url}/v1/checkout")
            logger.debug(f"Headers: {headers}")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            
            # Make API request to GCash
            try:
                response = requests.post(
                    f"{self.base_url}/v1/checkout",
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                logger.debug(f"GCash API response: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                logger.error(f"GCash API request failed: {str(e)}")
                raise
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'checkout_url': data.get('checkout_url'),
                    'transaction_id': data.get('transaction_id'),
                    'status': 'success'
                }
            else:
                logger.error(f"GCash checkout failed: {response.status_code} - {response.text}")
                return {
                    'error': f"Failed to create checkout: {response.text}",
                    'status': 'error'
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"GCash API request error: {str(e)}")
            return {
                'error': f"Network error: {str(e)}",
                'status': 'error'
            }
        except Exception as e:
            logger.error(f"GCash checkout error: {str(e)}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'status': 'error'
            }
    
    def verify_webhook_signature(self, payload, signature, timestamp):
        """
        Verify webhook signature to ensure authenticity
        
        Args:
            payload: Webhook payload (dict)
            signature: Signature from webhook headers
            timestamp: Timestamp from webhook headers
            
        Returns:
            bool: True if signature is valid
        """
        try:
            expected_signature, _ = self._generate_signature(payload, timestamp)
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Webhook signature verification error: {str(e)}")
            return False
    
    def process_refund(self, payment, refund_amount=None):
        """
        Process refund for a completed payment
        
        Args:
            payment: Payment model instance
            refund_amount: Amount to refund (defaults to full payment amount)
            
        Returns:
            dict: {'status': str, 'refund_transaction_id': str} or {'error': str}
        """
        if payment.payment_status != 'completed':
            return {
                'error': 'Only completed payments can be refunded',
                'status': 'error'
            }
        
        if not payment.transaction_id:
            return {
                'error': 'No transaction ID found for this payment',
                'status': 'error'
            }
        
        try:
            refund_amount = float(refund_amount or payment.amount)
            
            payload = {
                'transaction_id': payment.transaction_id,
                'amount': refund_amount,
                'reason': 'Customer request',
                'reference_number': f"REF-{payment.reference_number}",
            }
            
            signature, timestamp = self._generate_signature(payload)
            headers = self._get_headers()
            headers['X-Signature'] = signature
            headers['X-Timestamp'] = timestamp
            
            response = requests.post(
                f"{self.base_url}/v1/refunds",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': 'success',
                    'refund_transaction_id': data.get('refund_transaction_id'),
                    'refund_amount': refund_amount
                }
            else:
                logger.error(f"GCash refund failed: {response.status_code} - {response.text}")
                return {
                    'error': f"Refund failed: {response.text}",
                    'status': 'error'
                }
                
        except Exception as e:
            logger.error(f"GCash refund error: {str(e)}")
            return {
                'error': f"Unexpected error: {str(e)}",
                'status': 'error'
            }
    
    def get_transaction_status(self, transaction_id):
        """
        Query GCash for transaction status
        
        Args:
            transaction_id: GCash transaction ID
            
        Returns:
            dict: Transaction status information
        """
        logger.info(f"Getting transaction status for: {transaction_id}")
        try:
            headers = self._get_headers()
            url = f"{self.base_url}/v1/transactions/{transaction_id}"
            
            logger.debug(f"Making API request to: {url}")
            logger.debug(f"Headers: {headers}")
            
            response = requests.get(
                url,
                headers=headers,
                timeout=30
            )
            
            logger.debug(f"GCash status check response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'data': response.json()
                }
            else:
                return {
                    'status': 'error',
                    'error': response.text
                }
                
        except Exception as e:
            logger.error(f"GCash status check error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

