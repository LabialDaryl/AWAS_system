from django.db import models
from django.conf import settings
from billing.models import Bill
import uuid


class Payment(models.Model):
    """Model for payment transactions"""
    
    PAYMENT_METHOD_CHOICES = [
        ('gcash', 'GCash'),
        ('paypal', 'PayPal'),
        ('paymaya', 'PayMaya'),
        ('walk_in', 'Walk-in'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('success', 'Success'),  # Alias for completed for GCash compatibility
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    # Payment identification
    payment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    reference_number = models.CharField(max_length=100, unique=True, blank=True)
    
    # Payment details
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    
    # Payment gateway details
    gateway_transaction_id = models.CharField(max_length=200, blank=True, db_index=True)
    transaction_id = models.CharField(max_length=200, blank=True, unique=True, null=True, help_text="GCash transaction ID")
    gateway_response = models.TextField(blank=True)
    webhook_id = models.CharField(max_length=200, blank=True, help_text="Webhook ID for idempotency")
    
    # Refund and dispute fields
    is_disputed = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)
    flagged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flagged_payments'
    )
    flagged_at = models.DateTimeField(null=True, blank=True)
    flag_reason = models.TextField(blank=True)
    
    # Refund fields
    refund_requested = models.BooleanField(default=False)
    refund_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refund_requests'
    )
    refund_requested_at = models.DateTimeField(null=True, blank=True)
    refund_approved = models.BooleanField(default=False)
    refund_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_refunds'
    )
    refund_approved_at = models.DateTimeField(null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    refund_transaction_id = models.CharField(max_length=200, blank=True)
    
    # Metadata
    payment_date = models.DateTimeField(auto_now_add=True)
    processed_date = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payments'
    )
    
    notes = models.TextField(blank=True)
    receipt_image = models.ImageField(upload_to='payment_receipts/', blank=True, null=True)
    receipt_sent = models.BooleanField(default=False)
    receipt_sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment {self.reference_number} - {self.customer.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # Generate reference number if not exists
        if not self.reference_number:
            self.reference_number = f"PAY-{self.payment_id.hex[:12].upper()}"
        
        # Normalize 'success' to 'completed' for consistency
        if self.payment_status == 'success':
            self.payment_status = 'completed'
        
        # Update bill amount_paid if payment is completed
        if self.payment_status == 'completed' and self.pk:
            old_payment = Payment.objects.filter(pk=self.pk).first()
            if old_payment and old_payment.payment_status not in ['completed', 'success']:
                self.bill.amount_paid += self.amount
                self.bill.save()
        
        super().save(*args, **kwargs)
    
    @property
    def is_online_payment(self):
        return self.payment_method in ['gcash', 'paypal', 'paymaya']


class PaymentHistory(models.Model):
    """Model for tracking payment history and changes"""
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Payment histories'
    
    def __str__(self):
        return f"{self.payment.reference_number} - {self.status} at {self.timestamp}"


class PaymentAuditLog(models.Model):
    """Model for auditing all payment-related actions for compliance"""
    
    ACTION_CHOICES = [
        ('payment_created', 'Payment Created'),
        ('payment_initiated', 'Payment Initiated'),
        ('payment_completed', 'Payment Completed'),
        ('payment_failed', 'Payment Failed'),
        ('payment_cancelled', 'Payment Cancelled'),
        ('payment_refunded', 'Payment Refunded'),
        ('payment_verified', 'Payment Verified'),
        ('payment_flagged', 'Payment Flagged'),
        ('payment_disputed', 'Payment Disputed'),
        ('refund_requested', 'Refund Requested'),
        ('refund_approved', 'Refund Approved'),
        ('refund_rejected', 'Refund Rejected'),
        ('webhook_received', 'Webhook Received'),
        ('receipt_generated', 'Receipt Generated'),
        ('receipt_sent', 'Receipt Sent'),
    ]
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='audit_logs', null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_audit_actions'
    )
    user_role = models.CharField(max_length=20, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Payment Audit Log'
        verbose_name_plural = 'Payment Audit Logs'
        indexes = [
            models.Index(fields=['-timestamp', 'action']),
            models.Index(fields=['payment', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.payment.reference_number if self.payment else 'N/A'} - {self.timestamp}"
