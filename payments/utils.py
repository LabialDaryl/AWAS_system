"""
Utility functions for payment processing
"""
from django.utils import timezone
from .models import PaymentAuditLog
import logging

logger = logging.getLogger(__name__)


def log_payment_action(payment, action, user, request=None, details=None, status=''):
    """
    Log payment action to audit log for compliance
    
    Args:
        payment: Payment instance (can be None for system actions)
        action: Action type from PaymentAuditLog.ACTION_CHOICES
        user: User instance (can be None for system actions)
        request: Django request object (optional, for IP and user agent)
        details: Additional details dict
        status: Status string
    """
    try:
        user_role = ''
        if user:
            if user.is_superuser or user.user_type == 'admin':
                user_role = 'admin'
            elif user.is_staff_member:
                user_role = 'staff'
            else:
                user_role = 'customer'
        
        ip_address = None
        user_agent = ''
        if request:
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        PaymentAuditLog.objects.create(
            payment=payment,
            action=action,
            user=user,
            user_role=user_role,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            status=status
        )
    except Exception as e:
        logger.error(f"Failed to log payment action: {str(e)}")


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

